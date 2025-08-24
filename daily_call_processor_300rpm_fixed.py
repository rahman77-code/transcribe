#!/usr/bin/env python3
"""
Daily Call Processor - Optimized for 300 RPM per Groq API key
Handles automatic token refresh and multi-key rotation
"""

import subprocess
import sys

# Install groq if not available
try:
    from groq import Groq
except ImportError:
    print("Installing groq package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "groq"])
    from groq import Groq

import os
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

# Set up logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_call_processor_300rpm.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OptimizedCallProcessor:
    def __init__(self):
        # RingCentral configuration
        self.rc_client_id = os.getenv("RC_CLIENT_ID")
        self.rc_client_secret = os.getenv("RC_CLIENT_SECRET")
        self.rc_jwt = os.getenv("RC_JWT")
        self.rc_server_url = os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com")
        
        # Strip any trailing slashes from server URL
        self.rc_server_url = self.rc_server_url.rstrip('/')
        
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
        
        # Groq API Rate limiting (300 RPM per key)
        self.groq_rpm = 300
        self.groq_request_times = {key: [] for key in self.groq_api_keys}
        self.groq_locks = {key: threading.Lock() for key in self.groq_api_keys}
        
        # Processing delays optimized for 300 RPM
        self.download_delay = 0.5  # RingCentral has generous limits
        self.min_transcription_interval = 0.2  # 300 RPM = 0.2s minimum between requests
        
        logger.info(f"🚀 Initialized with {len(self.groq_api_keys)} Groq API keys")
        logger.info(f"⚡ Optimized for 300 RPM per key = {300 * len(self.groq_api_keys)} total RPM")
        logger.info(f"📊 Theoretical max: {300 * len(self.groq_api_keys) * 60} transcriptions/hour")
        logger.info(f"⏱️ Will only process recordings longer than 20 seconds")
        
        # Initialize RingCentral
        self.sdk = None
        self.last_token_refresh = None
        self.token_refresh_interval = 3000  # 50 minutes
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
            "transcription_errors_by_key": {},
            "token_refreshes": 0
        }
        
        # Configuration
        self.max_retries = 3
        self.chunk_size = 8192
        self.max_file_size_mb = 25  # Groq limit
        self.min_duration_seconds = 20  # Skip recordings shorter than 20 seconds
        self.max_processing_time = 5.5 * 3600  # 5.5 hours (leave buffer)
        
        # Authenticate
        self._authenticate()
    
    def _wait_for_groq_rate_limit(self, api_key: str):
        """Ensure we don't exceed 300 RPM for a specific key"""
        with self.groq_locks[api_key]:
            now = time.time()
            # Remove requests older than 1 minute
            self.groq_request_times[api_key] = [t for t in self.groq_request_times[api_key] if now - t < 60]
            
            # Check if we need to wait
            if len(self.groq_request_times[api_key]) >= self.groq_rpm:
                # Calculate how long to wait
                oldest_request = self.groq_request_times[api_key][0]
                wait_time = 60 - (now - oldest_request) + 0.1  # Add 100ms buffer
                if wait_time > 0:
                    logger.info(f"⏳ Key #{self.groq_api_keys.index(api_key)+1} approaching rate limit, waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    now = time.time()
            
            # Record this request
            self.groq_request_times[api_key].append(now)
    
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
                self.stats["token_refreshes"] += 1
            
            rcsdk = SDK(self.rc_client_id, self.rc_client_secret, self.rc_server_url)
            platform = rcsdk.platform()
            
            # JWT auth
            platform.login(jwt=self.rc_jwt)
            
            self.sdk = rcsdk
            self.last_token_refresh = datetime.now()
            
            if self._should_refresh_token():
                logger.info("✅ Token refreshed successfully")
            else:
                logger.info("✅ Successfully authenticated with RingCentral")
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            raise
    
    def _get_best_groq_key(self) -> Tuple[str, int]:
        """Get the best Groq API key based on rate limits and usage"""
        now = datetime.now()
        best_key = None
        best_score = float('inf')
        
        for i, key in enumerate(self.groq_api_keys):
            # Skip keys with high error rates
            if self.groq_key_errors[key] >= 5:
                continue
            
            # Skip keys that were rate limited in the last 5 minutes
            if self.groq_key_last_rate_limit[key]:
                time_since_rate_limit = (now - self.groq_key_last_rate_limit[key]).total_seconds()
                if time_since_rate_limit < 300:  # 5 minutes
                    continue
            
            # Check current RPM for this key
            with self.groq_locks[key]:
                current_rpm = len([t for t in self.groq_request_times[key] if now.timestamp() - t < 60])
            
            # Score based on current RPM usage (lower is better)
            score = current_rpm
            
            if score < best_score:
                best_score = score
                best_key = key
                self.current_groq_key_index = i
        
        if best_key is None:
            # All keys are either errored or rate limited, use least recently used
            best_key = min(self.groq_api_keys, key=lambda k: self.groq_key_last_used[k])
            self.current_groq_key_index = self.groq_api_keys.index(best_key)
        
        return best_key, self.current_groq_key_index
    
    def get_fresh_recording_uri(self, recording_id: str) -> Optional[str]:
        """Re-fetch recording metadata to get a fresh content URI"""
        try:
            if self._should_refresh_token():
                self._authenticate()
            
            # Get recording info
            response = self.sdk.platform().get(f'/restapi/v1.0/account/~/recording/{recording_id}')
            if response.status_code == 200:
                data = response.json()
                return data.get('contentUri')
            else:
                logger.error(f"Failed to refresh recording URI: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error refreshing recording URI: {e}")
            return None
    
    def get_call_logs(self, target_date: str) -> List[Dict]:
        """Get call logs for a specific date"""
        logger.info(f"📅 Fetching call logs for {target_date}")
        
        # Refresh token if needed
        if self._should_refresh_token():
            self._authenticate()
        
        # Date range for the target date (in UTC)
        date_from = f"{target_date}T00:00:00.000Z"
        date_to = f"{target_date}T23:59:59.999Z"
        
        logger.info(f"📅 Fetching call logs from {date_from} to {date_to}")
        
        all_records = []
        page = 1
        per_page = 1000
        
        while True:
            try:
                response = self.sdk.platform().get(
                    '/restapi/v1.0/account/~/call-log',
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
                
                if response.status_code == 200:
                    data = response.json()
                    records = data.get('records', [])
                    all_records.extend(records)
                    
                    logger.info(f"📞 Fetched page {page} with {len(records)} records")
                    
                    # Check if there are more pages
                    if 'navigation' in data and 'nextPage' in data['navigation']:
                        page += 1
                        time.sleep(2)  # Small delay between pages
                    else:
                        break
                elif response.status_code == 401:
                    logger.warning("Token expired during call log fetch, refreshing...")
                    self._authenticate()
                    continue
                else:
                    logger.error(f"Failed to fetch call logs: HTTP {response.status_code}")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching call logs: {e}")
                break
        
        logger.info(f"📊 Found {len(all_records)} total call log entries")
        
        # Filter for recordings longer than minimum duration
        recordings = []
        skipped_count = 0
        
        for record in all_records:
            if record.get('recording') and record.get('duration', 0) > self.min_duration_seconds:
                recordings.append(record)
            elif record.get('recording') and record.get('duration', 0) <= self.min_duration_seconds:
                skipped_count += 1
        
        if skipped_count > 0:
            logger.info(f"⏭️ Skipping {skipped_count} recordings shorter than {self.min_duration_seconds} seconds")
            self.stats["recordings_skipped_short"] = skipped_count
        
        logger.info(f"🎯 Found {len(recordings)} recordings longer than {self.min_duration_seconds} seconds")
        
        return recordings
    
    def download_recording(self, recording_info: Dict, output_dir: Path) -> Optional[str]:
        """Download a recording from RingCentral"""
        recording_id = recording_info['id']
        content_uri = recording_info.get('contentUri', recording_info.get('uri'))
        
        if not content_uri:
            logger.error(f"No content URI for recording {recording_id}")
            return None
        
        # Ensure output_dir is a Path object
        output_dir = Path(output_dir)
        output_file = output_dir / f"recording_{recording_id}.mp3"
        
        for attempt in range(self.max_retries):
            try:
                # Refresh token if needed
                if self._should_refresh_token():
                    self._authenticate()
                
                # Download the recording
                headers = {
                    'Authorization': f'Bearer {self.sdk.platform().auth().data()["access_token"]}'
                }
                
                response = requests.get(content_uri, headers=headers, stream=True)
                
                if response.status_code == 200:
                    # Save to file
                    with open(output_file, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                f.write(chunk)
                    
                    logger.info(f"✅ Downloaded: {output_file.name}")
                    return str(output_file)
                    
                elif response.status_code == 401:
                    logger.warning("⚠️ Token expired, refreshing...")
                    self._authenticate()
                    
                    # Get fresh content URI
                    fresh_uri = self.get_fresh_recording_uri(recording_id)
                    if fresh_uri:
                        content_uri = fresh_uri
                        recording_info['contentUri'] = fresh_uri
                    else:
                        logger.error("Failed to get fresh recording URI")
                        
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
    
    def transcribe_audio(self, audio_file: str, recording_id: str) -> Optional[str]:
        """Transcribe audio using Groq API with 300 RPM rate limiting"""
        # Check file size
        file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            logger.warning(f"⚠️ File too large ({file_size_mb:.1f}MB > {self.max_file_size_mb}MB)")
            return "File too large for transcription"
        
        max_key_attempts = min(len(self.groq_api_keys), 5)
        
        for key_attempt in range(max_key_attempts):
            api_key, key_index = self._get_best_groq_key()
            
            # Wait for rate limit on this specific key
            self._wait_for_groq_rate_limit(api_key)
            
            # Update usage tracking
            self.groq_key_usage[api_key] += 1
            self.groq_key_last_used[api_key] = datetime.now()
            
            # Initialize error tracking for this key
            if api_key not in self.stats["transcription_errors_by_key"]:
                self.stats["transcription_errors_by_key"][api_key] = 0
            
            try:
                logger.info(f"🎤 Transcribing with Groq API key #{key_index + 1}")
                
                # Configure Groq client
                client = Groq(api_key=api_key)
                
                # Open and transcribe
                with open(audio_file, 'rb') as audio:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-large-v3",
                        file=audio,
                        response_format="json"
                    )
                    
                    logger.info(f"✅ Transcription successful with key #{key_index + 1}")
                    return transcript.text
                    
            except Exception as e:
                error_msg = str(e)
                
                # Log based on error type
                if "429" in error_msg or "rate" in error_msg.lower():
                    logger.warning(f"⚠️ Rate limit hit on key #{key_index + 1}")
                    self.groq_key_errors[api_key] += 1
                    self.groq_key_last_rate_limit[api_key] = datetime.now()
                    self.stats["transcription_errors_by_key"][api_key] += 1
                    # No long wait, just try next key
                    time.sleep(1)
                    continue
                elif "500" in error_msg or "server" in error_msg.lower():
                    logger.warning(f"⚠️ Server error with key #{key_index + 1}")
                    # Don't penalize key for server errors
                    time.sleep(5)
                    continue
                else:
                    logger.error(f"❌ Transcription failed with key #{key_index + 1}: {error_msg}")
                    self.groq_key_errors[api_key] += 1
                    self.stats["transcription_errors_by_key"][api_key] += 1
                
                # Try next key
                continue
        
        # All attempts failed
        logger.error("❌ All transcription attempts failed")
        self.stats["errors"] += 1
        return None
    
    def process_recording(self, call_log: Dict, output_dir: Path) -> Dict:
        """Process a single recording"""
        recording_id = call_log.get('recording', {}).get('id', call_log.get('id'))
        duration = call_log.get('duration', 0)
        
        # Prepare call info
        call_info = {
            'id': recording_id,
            'date': call_log.get('startTime', ''),
            'duration': duration,
            'from': call_log.get('from', {}).get('phoneNumber', ''),
            'to': call_log.get('to', {}).get('phoneNumber', ''),
            'direction': call_log.get('direction', ''),
            'transcription': None,
            'audio_file': None
        }
        
        # Download recording
        logger.info(f"⬇️ Downloading recording {recording_id}")
        audio_file = self.download_recording(call_log.get('recording', {}), output_dir)
        
        if audio_file:
            call_info['audio_file'] = os.path.basename(audio_file)
            self.stats["recordings_processed"] += 1
            self.stats["total_call_duration"] += duration
            time.sleep(self.download_delay)
            
            # Transcribe
            logger.info(f"🎯 Transcribing recording {recording_id}")
            transcription = self.transcribe_audio(audio_file, recording_id)
            
            if transcription:
                call_info['transcription'] = transcription
                
                # Save transcription to file
                transcription_file = output_dir / f"recording_{recording_id}_transcription.txt"
                with open(transcription_file, 'w', encoding='utf-8') as f:
                    f.write(transcription)
            else:
                call_info['transcription'] = "Transcription failed"
            
            # Small delay between transcriptions
            time.sleep(self.min_transcription_interval)
        else:
            call_info['transcription'] = "Download failed"
        
        return call_info
    
    def save_results(self, results: List[Dict], output_dir: Path, target_date: str):
        """Save results to CSV and JSON files"""
        # Save as JSON
        json_file = output_dir / f"transcriptions_{target_date}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"📄 Saved JSON: {json_file}")
        
        # Save as CSV
        csv_file = output_dir / f"transcriptions_{target_date}.csv"
        with open(csv_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("Recording ID,Date,Duration (seconds),From,To,Direction,Transcription\n")
            
            # Write data
            for result in results:
                # Escape quotes in transcription
                transcription = (result.get('transcription') or '').replace('"', '""')
                
                f.write(f'"{result["id"]}",')
                f.write(f'"{result["date"]}",')
                f.write(f'{result["duration"]},')
                f.write(f'"{result["from"]}",')
                f.write(f'"{result["to"]}",')
                f.write(f'"{result["direction"]}",')
                f.write(f'"{transcription}"\n')
        
        logger.info(f"📄 Saved CSV: {csv_file}")
        
        # Save summary
        summary = {
            'date': target_date,
            'total_calls': self.stats['total_calls'],
            'recordings_found': self.stats['recordings_found'],
            'recordings_processed': self.stats['recordings_processed'],
            'recordings_skipped_short': self.stats['recordings_skipped_short'],
            'errors': self.stats['errors'],
            'success_rate': f"{(self.stats['recordings_processed'] / self.stats['recordings_found'] * 100):.1f}%" if self.stats['recordings_found'] > 0 else "0%",
            'duration_hours': f"{(datetime.now() - self.stats['start_time']).total_seconds() / 3600:.2f}",
            'total_audio_hours': f"{self.stats['total_call_duration'] / 3600:.2f}",
            'api_keys_used': len(self.groq_api_keys),
            'groq_rpm_per_key': self.groq_rpm,
            'total_rpm_capacity': self.groq_rpm * len(self.groq_api_keys)
        }
        
        summary_file = output_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"📊 Saved summary: {summary_file}")
    
    def run(self, target_date: str):
        """Main processing function"""
        logger.info(f"🚀 Starting optimized daily processing for {target_date}")
        logger.info(f"⏱️ Maximum processing time: {self.max_processing_time/3600:.1f} hours")
        
        # Get call logs
        call_logs = self.get_call_logs(target_date)
        self.stats["total_calls"] = len(call_logs)
        self.stats["recordings_found"] = len(call_logs)
        
        if not call_logs:
            logger.warning("⚠️ No recordings found for the specified date")
            return
        
        # Create output directory
        output_dir = Path(f"daily_recordings/{target_date}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process recordings
        results = []
        logger.info(f"🎬 Starting batch processing of {len(call_logs)} recordings")
        
        for idx, call_log in enumerate(call_logs):
            # Check processing time
            elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
            if elapsed > self.max_processing_time:
                logger.warning(f"⏰ Approaching time limit, stopping at {idx}/{len(call_logs)}")
                break
            
            # Update tokens if needed
            if self._should_refresh_token():
                self._authenticate()
            
            # Process recording
            result = self.process_recording(call_log, output_dir)
            results.append(result)
            
            # Progress update
            if (idx + 1) % 10 == 0 or idx == len(call_logs) - 1:
                progress = (idx + 1) / len(call_logs) * 100
                elapsed_hours = elapsed / 3600
                logger.info(f"📊 Progress: {idx + 1}/{len(call_logs)} ({progress:.1f}%) - {elapsed_hours:.1f} hours elapsed")
        
        # Save results
        self.save_results(results, output_dir, target_date)
        
        # Final stats
        elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
        logger.info("\n" + "="*80)
        logger.info(f"✅ Processing completed in {elapsed/3600:.2f} hours")
        logger.info(f"📊 Processed {self.stats['recordings_processed']} recordings")
        logger.info(f"📝 Completed {len([r for r in results if r['transcription'] and r['transcription'] != 'Transcription failed'])} transcriptions")
        logger.info(f"❌ Errors: {self.stats['errors']}")
        logger.info(f"🔄 Token refreshes: {self.stats['token_refreshes']}")
        
        # API Key usage stats
        logger.info("\n🔑 API Key Usage Statistics:")
        logger.info("="*80)
        
        for i, key in enumerate(self.groq_api_keys):
            usage = self.groq_key_usage[key]
            errors = self.groq_key_errors[key]
            rate_limited = self.groq_key_last_rate_limit[key] is not None
            usage_percent = (usage / self.stats['recordings_processed'] * 100) if self.stats['recordings_processed'] > 0 else 0
            
            # Mask the key for security
            masked_key = f"{key[:8]}...{key[-4:]}"
            logger.info(f"Key #{i+1} ({masked_key}): {usage} uses ({usage_percent:.1f}%), {errors} errors{', Rate limited' if rate_limited else ''}")
        
        logger.info(f"Total API calls: {sum(self.groq_key_usage.values())}")
        logger.info(f"Token refreshes: {self.stats['token_refreshes']}")
        logger.info("="*80)

def main():
    # Get target date
    target_date = os.getenv("TARGET_DATE")
    if not target_date:
        # Default to yesterday in Central Time
        central_tz = timezone(timedelta(hours=-6))  # CST/CDT
        yesterday = datetime.now(central_tz) - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
    
    processor = OptimizedCallProcessor()
    processor.run(target_date)

if __name__ == "__main__":
    main()
