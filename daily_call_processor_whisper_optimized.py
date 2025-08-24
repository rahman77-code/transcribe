import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor
import threading
from ringcentral import SDK
from groq import Groq

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_call_processor_whisper_optimized.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WhisperOptimizedProcessor:
    def __init__(self):
        # Whisper API tier configuration
        self.whisper_tier = os.getenv("WHISPER_API_TIER", "free").lower()
        
        if self.whisper_tier == "developer":
            self.whisper_rpm = 300  # Developer tier: 300 requests per minute
            self.whisper_delay = 0.2  # Can do one request every 0.2 seconds
            logger.info("💎 Using Whisper DEVELOPER tier (300 RPM)")
        else:
            self.whisper_rpm = 20  # Free tier: 20 requests per minute
            self.whisper_delay = 3  # Must wait 3 seconds between requests
            logger.info("🆓 Using Whisper FREE tier (20 RPM)")
        
        # RingCentral configuration
        self.rc_client_id = os.getenv("RC_CLIENT_ID")
        self.rc_client_secret = os.getenv("RC_CLIENT_SECRET")
        self.rc_jwt = os.getenv("RC_JWT")
        self.rc_server_url = os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com")
        
        # Initialize Groq API keys
        self.groq_api_keys = []
        for i in range(1, 51):  # Support up to 50 keys
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                self.groq_api_keys.append(key)
        
        if not self.groq_api_keys:
            logger.error("❌ No Groq API keys found!")
            sys.exit(1)
        
        # Initialize key rotation mechanism
        self.current_groq_key_index = 0
        self.groq_key_usage = {key: 0 for key in self.groq_api_keys}
        self.groq_key_last_used = {key: datetime.min for key in self.groq_api_keys}
        self.groq_key_errors = {key: 0 for key in self.groq_api_keys}
        self.groq_key_last_rate_limit = {key: None for key in self.groq_api_keys}
        
        # Download delay optimization
        # RingCentral has generous rate limits, so we can download quickly
        self.download_delay = 0.5  # Half second between downloads
        
        # Transcription delay based on Whisper tier
        self.transcription_delay = self.whisper_delay
        
        # Calculate maximum throughput
        seconds_per_call = self.download_delay + self.transcription_delay
        max_calls_hour = int(3600 / seconds_per_call)
        max_calls_6h = max_calls_hour * 6
        
        logger.info(f"🚀 Initialized with {len(self.groq_api_keys)} Groq API keys")
        logger.info(f"⚡ Optimized for Whisper {self.whisper_tier.upper()} tier")
        logger.info(f"📊 Theoretical maximum: {max_calls_hour} calls/hour, {max_calls_6h} calls in 6 hours")
        logger.info(f"⏱️ Delays: {self.download_delay}s download, {self.transcription_delay}s transcription")
        
        # Initialize RingCentral
        self.sdk = None
        self.last_token_refresh = None
        self.token_refresh_interval = 3300  # 55 minutes
        self.hubspot_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        
        # Performance tracking
        self.stats = {
            "total_calls": 0,
            "recordings_found": 0,
            "recordings_processed": 0,
            "recordings_skipped_short": 0,
            "errors": 0,
            "total_audio_hours": 0.0,
            "total_call_duration": 0,
            "start_time": datetime.now(),
            "transcription_errors_by_key": {}
        }
        
        # Rate limit tracking for Whisper
        self.whisper_request_times = []
        self.whisper_lock = threading.Lock()
        
        # Configuration
        self.max_retries = 3
        self.chunk_size = 8192
        
        # Auth RingCentral
        self._authenticate()
    
    def _wait_for_whisper_rate_limit(self):
        """Ensure we don't exceed Whisper rate limits"""
        with self.whisper_lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.whisper_request_times = [t for t in self.whisper_request_times if now - t < 60]
            
            # Check if we need to wait
            if len(self.whisper_request_times) >= self.whisper_rpm:
                # Calculate how long to wait
                oldest_request = self.whisper_request_times[0]
                wait_time = 60 - (now - oldest_request) + 0.1  # Add 100ms buffer
                if wait_time > 0:
                    logger.info(f"⏳ Approaching Whisper rate limit, waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    now = time.time()
            
            # Record this request
            self.whisper_request_times.append(now)
    
    def _should_refresh_token(self):
        """Check if it's time to refresh the token"""
        if not self.last_token_refresh:
            return False
        
        time_since_refresh = (datetime.now() - self.last_token_refresh).total_seconds()
        return time_since_refresh >= self.token_refresh_interval
    
    def _authenticate(self):
        """Authenticate with RingCentral using JWT"""
        try:
            if self._should_refresh_token():
                logger.info("🔄 Refreshing RingCentral token...")
            
            rcsdk = SDK(self.rc_client_id, self.rc_client_secret, self.rc_server_url)
            platform = rcsdk.platform()
            
            # JWT auth
            platform.login(jwt=self.rc_jwt)
            
            self.sdk = rcsdk
            self.last_token_refresh = datetime.now()
            
            if self._should_refresh_token():
                logger.info("✅ Token refreshed successfully")
            else:
                logger.info("✅ Authenticated with RingCentral successfully")
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            raise
    
    def _get_next_groq_key(self) -> Tuple[str, int]:
        """Get the next Groq API key using intelligent rotation"""
        now = datetime.now()
        best_key = None
        best_score = float('inf')
        
        # Find the best key based on usage and time since last use
        for i, key in enumerate(self.groq_api_keys):
            # Skip keys with high error rates
            if self.groq_key_errors[key] >= 5:
                logger.debug(f"Skipping key #{i+1} due to high error rate")
                continue
            
            # Skip keys that were rate limited in the last 5 minutes
            if self.groq_key_last_rate_limit[key]:
                time_since_rate_limit = (now - self.groq_key_last_rate_limit[key]).total_seconds()
                if time_since_rate_limit < 300:  # 5 minutes
                    logger.debug(f"Skipping key #{i+1} - rate limited {time_since_rate_limit:.0f}s ago")
                    continue
                
            # Calculate time since last use
            time_since_use = (now - self.groq_key_last_used[key]).total_seconds()
            
            # Score based on usage count, time since last use, and rate limit history
            # Lower score is better
            score = self.groq_key_usage[key] - (time_since_use / 10)
            
            # Penalize keys that have been rate limited recently
            if self.groq_key_last_rate_limit[key]:
                score += 10 / (time_since_rate_limit / 60)  # Less penalty as time passes
            
            if score < best_score:
                best_score = score
                best_key = key
                self.current_groq_key_index = i
        
        if best_key is None:
            # All keys have errors or are rate limited
            logger.warning("All keys have errors or are rate limited")
            # Find the key that was rate limited longest ago
            oldest_rate_limit_key = min(
                self.groq_api_keys,
                key=lambda k: self.groq_key_last_rate_limit[k] or datetime.min
            )
            best_key = oldest_rate_limit_key
            self.current_groq_key_index = self.groq_api_keys.index(best_key)
            
        return best_key, self.current_groq_key_index
    
    def get_call_info(self, target_date: str) -> List[Dict]:
        """Get call information including names from HubSpot"""
        logger.info(f"📞 Fetching calls for {target_date}")
        
        # First get calls from RingCentral
        calls_by_phone = {}
        
        # Refresh token if needed
        if self._should_refresh_token():
            self._authenticate()
        
        # Get extension list
        try:
            extensions_response = self.sdk.platform().get('/restapi/v1.0/account/~/extension')
            extensions = extensions_response.json()['records']
            logger.info(f"Found {len(extensions)} extensions")
        except Exception as e:
            logger.error(f"Failed to get extensions: {e}")
            extensions = []
        
        # Get call logs for each extension
        for ext in extensions:
            if ext.get('status') != 'Enabled':
                continue
                
            ext_id = ext['id']
            ext_name = f"{ext.get('contact', {}).get('firstName', '')} {ext.get('contact', {}).get('lastName', '')}".strip()
            ext_number = ext.get('extensionNumber', 'Unknown')
            
            logger.info(f"Checking extension: {ext_name or ext_number}")
            
            try:
                # Date range for the target date (in UTC)
                date_from = f"{target_date}T00:00:00.000Z"
                date_to = f"{target_date}T23:59:59.999Z"
                
                page = 1
                per_page = 250
                
                while True:
                    call_log_response = self.sdk.platform().get(
                        f'/restapi/v1.0/account/~/extension/{ext_id}/call-log',
                        {
                            'dateFrom': date_from,
                            'dateTo': date_to,
                            'type': 'Voice',
                            'view': 'Detailed',
                            'perPage': per_page,
                            'page': page,
                            'recordingType': 'All'
                        }
                    )
                    
                    data = call_log_response.json()
                    records = data.get('records', [])
                    
                    for record in records:
                        # Only include calls with recordings
                        if record.get('recording'):
                            phone = record.get('from', {}).get('phoneNumber', '') or record.get('to', {}).get('phoneNumber', '')
                            if phone and not phone.startswith('+1650'):  # Exclude RingCentral numbers
                                call_key = f"{phone}_{record['id']}"
                                calls_by_phone[call_key] = {
                                    'id': record['id'],
                                    'startTime': record['startTime'],
                                    'duration': record['duration'],
                                    'direction': record['direction'],
                                    'from': record.get('from', {}),
                                    'to': record.get('to', {}),
                                    'recording': record.get('recording'),
                                    'extension_name': ext_name,
                                    'extension_number': ext_number,
                                    'phone_number': phone,
                                    'contact_name': None  # Will be filled from HubSpot
                                }
                    
                    # Check if there are more pages
                    if 'navigation' in data and 'nextPage' in data['navigation']:
                        page += 1
                        time.sleep(2)  # Small delay between pages
                    else:
                        break
                        
            except Exception as e:
                logger.error(f"Failed to get call log for extension {ext_id}: {e}")
        
        # Now get names from HubSpot
        if self.hubspot_token and calls_by_phone:
            unique_phones = list(set(call['phone_number'] for call in calls_by_phone.values()))
            logger.info(f"Looking up {len(unique_phones)} phone numbers in HubSpot")
            
            # Create a mapping of phone numbers to names
            phone_to_name = {}
            
            for phone in unique_phones:
                try:
                    # Search for contact by phone number
                    search_response = requests.post(
                        'https://api.hubapi.com/crm/v3/objects/contacts/search',
                        headers={
                            'Authorization': f'Bearer {self.hubspot_token}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            "filterGroups": [
                                {
                                    "filters": [
                                        {
                                            "propertyName": "phone",
                                            "operator": "CONTAINS_TOKEN",
                                            "value": phone.replace('+', '')
                                        }
                                    ]
                                }
                            ],
                            "properties": ["firstname", "lastname", "phone"],
                            "limit": 1
                        }
                    )
                    
                    if search_response.status_code == 200:
                        results = search_response.json().get('results', [])
                        if results:
                            contact = results[0]['properties']
                            full_name = f"{contact.get('firstname', '')} {contact.get('lastname', '')}".strip()
                            if full_name:
                                phone_to_name[phone] = full_name
                    
                except Exception as e:
                    logger.debug(f"Could not find contact for {phone}: {e}")
            
            # Update calls with names
            for call in calls_by_phone.values():
                if call['phone_number'] in phone_to_name:
                    call['contact_name'] = phone_to_name[call['phone_number']]
        
        calls = list(calls_by_phone.values())
        logger.info(f"Found {len(calls)} calls with recordings")
        
        # Filter to only include calls longer than 20 seconds
        long_calls = [call for call in calls if call['duration'] > 20]
        short_calls = len(calls) - len(long_calls)
        
        if short_calls > 0:
            logger.info(f"⏭️ Skipped {short_calls} recordings shorter than 20 seconds")
        
        return long_calls
    
    def download_recording(self, recording_info: Dict) -> Optional[str]:
        """Download a recording from RingCentral"""
        for attempt in range(self.max_retries):
            try:
                # Refresh token if needed
                if self._should_refresh_token():
                    self._authenticate()
                
                # Get recording content
                recording_uri = recording_info['uri']
                response = self.sdk.platform().get(recording_uri)
                
                if response.status_code == 200:
                    # Save to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                        tmp_file.write(response.content)
                        return tmp_file.name
                        
                elif response.status_code == 401:
                    logger.warning("⚠️ Token expired, refreshing...")
                    self._authenticate()
                    continue
                    
                elif response.status_code == 429:
                    # Rate limit - wait longer
                    wait_time = (attempt + 1) * 30
                    logger.warning(f"⚠️ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Download failed: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Download error: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep(10)
        
        self.stats["errors"] += 1
        return None
    
    def transcribe_audio(self, audio_file: str, call_info: Dict) -> Optional[str]:
        """Transcribe audio using Groq API with intelligent key rotation"""
        max_key_attempts = min(len(self.groq_api_keys), 5)  # Try up to 5 different keys
        
        for key_attempt in range(max_key_attempts):
            api_key, key_index = self._get_next_groq_key()
            
            # Update usage tracking
            self.groq_key_usage[api_key] += 1
            self.groq_key_last_used[api_key] = datetime.now()
            
            # Initialize error tracking for this key if not exists
            if api_key not in self.stats["transcription_errors_by_key"]:
                self.stats["transcription_errors_by_key"][api_key] = 0
            
            try:
                logger.info(f"🎯 Attempting transcription with Groq key #{key_index + 1} (usage: {self.groq_key_usage[api_key]})")
                
                # Ensure we respect Whisper rate limits
                self._wait_for_whisper_rate_limit()
                
                # Configure Groq client with current key
                client = Groq(api_key=api_key)
                
                # Open audio file and transcribe
                with open(audio_file, 'rb') as audio:
                    start_time = time.time()
                    
                    # Call Groq API
                    response = client.audio.transcriptions.create(
                        model="whisper-large-v3",
                        file=(os.path.basename(audio_file), audio.read()),
                        response_format="json"
                    )
                    
                    transcription_time = time.time() - start_time
                    logger.info(f"✅ Transcription successful in {transcription_time:.1f}s with key #{key_index + 1}")
                    
                    # Return the transcription text
                    return response.text
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Transcription failed with key #{key_index + 1}: {error_msg}")
                
                # Track errors
                self.groq_key_errors[api_key] += 1
                self.stats["transcription_errors_by_key"][api_key] += 1
                
                # Check if it's a rate limit error
                if "429" in error_msg or "rate" in error_msg.lower():
                    self.groq_key_last_rate_limit[api_key] = datetime.now()
                    logger.warning(f"⚠️ Rate limit hit on key #{key_index + 1}")
                    # Don't wait long, just try the next key
                    time.sleep(2)
                elif "500" in error_msg or "server" in error_msg.lower():
                    logger.warning(f"⚠️ Server error with key #{key_index + 1}")
                    time.sleep(5)
                
                # Try next key
                continue
        
        # All keys failed
        logger.error("❌ All Groq API keys failed for this transcription")
        self.stats["errors"] += 1
        return None
    
    def process_calls(self, target_date: str):
        """Process all calls for a given date"""
        # Get call info
        calls = self.get_call_info(target_date)
        self.stats["total_calls"] = len(calls)
        self.stats["recordings_found"] = len(calls)
        
        if not calls:
            logger.warning("No calls found with recordings")
            return
        
        logger.info(f"📊 Processing {len(calls)} recordings")
        
        # Create output directory
        output_dir = Path(f"daily_recordings/{target_date}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each call
        for idx, call_info in enumerate(calls):
            call_id = call_info['id']
            logger.info(f"\n🔄 Processing call {idx + 1}/{len(calls)} - ID: {call_id}")
            
            # Download recording
            logger.info("📥 Downloading recording...")
            audio_file = self.download_recording(call_info['recording'])
            
            try:
                if audio_file:
                    # Copy to output directory
                    output_audio = output_dir / f"{call_id}.mp3"
                    shutil.copy2(audio_file, output_audio)
                    logger.info(f"✅ Downloaded to {output_audio}")
                    
                    # Update audio hours stat
                    duration_hours = call_info['duration'] / 3600
                    self.stats["total_audio_hours"] += duration_hours
                    
                    # Track successful download
                    self.stats["recordings_processed"] += 1
                    self.stats["total_call_duration"] += call_info['duration']
                    time.sleep(self.download_delay)
                    
                    # Transcribe
                    logger.info("🎤 Transcribing audio...")
                    transcription = self.transcribe_audio(audio_file, call_info)
                    
                    if transcription:
                        call_info['transcription'] = transcription
                        logger.info("✅ Transcription completed")
                        
                        # Save transcription
                        output_text = output_dir / f"{call_id}.txt"
                        with open(output_text, 'w', encoding='utf-8') as f:
                            f.write(transcription)
                    else:
                        logger.warning("⚠️ Transcription failed")
                        call_info['transcription'] = "Transcription failed"
                    
                    time.sleep(self.transcription_delay)
                else:
                    call_info['transcription'] = "Download failed"
                    
            finally:
                # Clean up temp file
                if audio_file and os.path.exists(audio_file):
                    try:
                        os.unlink(audio_file)
                    except:
                        pass
            
            # Save call info
            info_file = output_dir / f"{call_id}_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(call_info, f, indent=2, ensure_ascii=False)
            
            # Log progress
            if (idx + 1) % 10 == 0:
                elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
                rate = (idx + 1) / (elapsed / 3600) if elapsed > 0 else 0
                eta_hours = (len(calls) - idx - 1) / rate if rate > 0 else 0
                logger.info(f"📊 Progress: {idx + 1}/{len(calls)} ({(idx + 1)/len(calls)*100:.1f}%) - Rate: {rate:.1f} calls/hour - ETA: {eta_hours:.1f} hours")
    
    def save_summary(self, target_date: str):
        """Save processing summary"""
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
        duration_hours = elapsed / 3600
        
        summary = {
            "date": target_date,
            "total_calls": self.stats["total_calls"],
            "recordings_found": self.stats["recordings_found"],
            "recordings_processed": self.stats["recordings_processed"],
            "recordings_skipped_short": self.stats["recordings_skipped_short"],
            "errors": self.stats["errors"],
            "success_rate": f"{(self.stats['recordings_processed'] / self.stats['recordings_found'] * 100):.1f}%" if self.stats['recordings_found'] > 0 else "0%",
            "duration_hours": f"{duration_hours:.2f}",
            "processing_rate": f"{self.stats['recordings_processed'] / duration_hours:.1f} calls/hour" if duration_hours > 0 else "0",
            "total_audio_hours": f"{self.stats['total_audio_hours']:.2f}",
            "groq_keys_used": len(self.groq_api_keys),
            "whisper_tier": self.whisper_tier.upper(),
            "whisper_rpm": self.whisper_rpm
        }
        
        # Add API key usage stats
        key_usage_summary = {}
        for i, key in enumerate(self.groq_api_keys):
            key_name = f"key_{i+1}"
            key_usage_summary[key_name] = {
                "usage_count": self.groq_key_usage[key],
                "error_count": self.groq_key_errors[key],
                "transcription_errors": self.stats["transcription_errors_by_key"].get(key, 0),
                "was_rate_limited": self.groq_key_last_rate_limit[key] is not None
            }
        
        summary["api_key_usage"] = key_usage_summary
        
        # Save summary
        output_dir = Path(f"daily_recordings/{target_date}")
        summary_file = output_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Print summary
        logger.info("\n" + "="*50)
        logger.info("📊 PROCESSING SUMMARY")
        logger.info("="*50)
        logger.info(f"📅 Date: {target_date}")
        logger.info(f"📞 Total calls: {self.stats['total_calls']}")
        logger.info(f"🎵 Recordings found: {self.stats['recordings_found']}")
        logger.info(f"✅ Successfully processed: {self.stats['recordings_processed']}")
        logger.info(f"⏭️ Skipped (too short): {self.stats['recordings_skipped_short']}")
        logger.info(f"❌ Errors: {self.stats['errors']}")
        logger.info(f"📈 Success rate: {summary['success_rate']}")
        logger.info(f"⏱️ Total duration: {summary['duration_hours']} hours")
        logger.info(f"🚀 Processing rate: {summary['processing_rate']}")
        logger.info(f"🎤 Total audio transcribed: {summary['total_audio_hours']} hours")
        logger.info(f"🔑 Groq API keys used: {len(self.groq_api_keys)}")
        logger.info(f"💎 Whisper tier: {self.whisper_tier.upper()} ({self.whisper_rpm} RPM)")
        
        # Show API key performance
        logger.info("\n🔑 API Key Usage:")
        for i, key in enumerate(self.groq_api_keys):
            usage = self.groq_key_usage[key]
            errors = self.groq_key_errors[key]
            transcription_errors = self.stats["transcription_errors_by_key"].get(key, 0)
            rate_limited = "Yes" if self.groq_key_last_rate_limit[key] else "No"
            logger.info(f"  Key #{i+1}: {usage} uses, {errors} errors, {transcription_errors} transcription errors, Rate limited: {rate_limited}")
        
        logger.info("="*50)

def main():
    # Get target date
    target_date = os.getenv("TARGET_DATE")
    if not target_date:
        # Default to yesterday
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
    
    logger.info(f"🚀 Starting Whisper-optimized processor for {target_date}")
    logger.info(f"🔑 Whisper API tier: {os.getenv('WHISPER_API_TIER', 'free').upper()}")
    
    try:
        processor = WhisperOptimizedProcessor()
        processor.process_calls(target_date)
        processor.save_summary(target_date)
        logger.info("✅ Processing completed successfully!")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()



