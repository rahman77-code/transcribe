#!/usr/bin/env python3
"""
Ultra-Fast Daily Call Processor - Optimized for 6-hour GitHub Actions limit
Processes 1000+ calls using 11 Groq API keys with aggressive optimization
"""

import os
import json
import csv
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from ringcentral import SDK
from dotenv import load_dotenv
import pytz

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_call_processor_6hour.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OptimizedDailyCallProcessor:
    """Optimized processor for 6-hour execution window"""
    
    def __init__(self):
        """Initialize with RingCentral and multiple Groq configurations"""
        # RingCentral config
        self.config = {
            "clientId": os.getenv("RC_CLIENT_ID"),
            "clientSecret": os.getenv("RC_CLIENT_SECRET"),
            "server": os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com").rstrip('/')
        }
        self.jwt_token = os.getenv("RC_JWT")
        
        # Load all Groq API keys
        self.groq_api_keys = self._load_groq_api_keys()
        self.current_groq_key_index = 0
        self.groq_key_usage = {key: 0 for key in self.groq_api_keys}
        self.groq_key_last_used = {key: datetime.min for key in self.groq_api_keys}
        self.groq_key_errors = {key: 0 for key in self.groq_api_keys}
        
        # Optimized delays for 6-hour window
        # With 11 keys, we can be aggressive on transcription
        self.download_delay = 8  # 8 seconds between downloads
        self.transcription_delay = 5  # 5 seconds between transcriptions
        self.batch_size = 5  # Process in batches
        
        # Calculate maximum throughput
        # 6 hours = 21,600 seconds
        # Per call: 8s download + 5s transcription = 13s
        # Max calls: 21,600 / 13 = ~1,661 calls
        self.max_processing_time = 5.5 * 3600  # 5.5 hours to be safe
        
        self.max_retries = 3
        self.output_base_dir = "daily_recordings"
        
        # RingCentral SDK
        self.sdk = None
        self.platform = None
        
        # Processing stats
        self.start_time = datetime.now()
        self.stats = {
            "total_calls": 0,
            "recordings_found": 0,
            "recordings_processed": 0,
            "transcriptions_completed": 0,
            "errors": 0,
            "total_duration": 0
        }
        
        logger.info(f"🚀 Initialized with {len(self.groq_api_keys)} Groq API keys")
        logger.info(f"⚡ Optimized for 6-hour window: {self.download_delay}s download, {self.transcription_delay}s transcription delays")
        
    def _load_groq_api_keys(self) -> List[str]:
        """Load all available Groq API keys from environment"""
        keys = []
        # Try GROQ_API_KEY first (single key)
        single_key = os.getenv("GROQ_API_KEY")
        if single_key:
            keys.append(single_key)
            
        # Then load numbered keys
        for i in range(1, 12):  # Support up to 11 keys
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                keys.append(key)
                
        if not keys:
            raise ValueError("No Groq API keys found in environment!")
            
        # Remove duplicates while preserving order
        seen = set()
        unique_keys = []
        for key in keys:
            if key not in seen:
                seen.add(key)
                unique_keys.append(key)
                
        return unique_keys
    
    def _get_next_groq_key(self) -> str:
        """Get next Groq API key using intelligent rotation"""
        # Find the key that was least recently used and has fewest errors
        now = datetime.now()
        best_key = None
        best_score = float('inf')
        
        for i, key in enumerate(self.groq_api_keys):
            # Skip keys with too many recent errors
            if self.groq_key_errors[key] > 5:
                continue
                
            # Calculate time since last use
            time_since_use = (now - self.groq_key_last_used[key]).total_seconds()
            
            # Score based on usage count and time since last use
            # Lower score is better
            score = self.groq_key_usage[key] - (time_since_use / 10)
            
            if score < best_score:
                best_score = score
                best_key = key
                self.current_groq_key_index = i
        
        if best_key is None:
            # All keys have errors, reset error counts and try again
            logger.warning("All keys have errors, resetting error counts")
            self.groq_key_errors = {key: 0 for key in self.groq_api_keys}
            best_key = self.groq_api_keys[0]
            self.current_groq_key_index = 0
        
        return best_key
    
    def authenticate(self) -> bool:
        """Authenticate with RingCentral using JWT"""
        try:
            self.sdk = SDK(
                self.config["clientId"],
                self.config["clientSecret"],
                self.config["server"]
            )
            self.platform = self.sdk.platform()
            
            # JWT authentication
            self.platform.login(jwt=self.jwt_token)
            
            logger.info("✅ Successfully authenticated with RingCentral")
            return True
            
        except Exception as e:
            logger.error(f"❌ Authentication failed: {str(e)}")
            return False
    
    def should_continue_processing(self) -> bool:
        """Check if we should continue processing based on time limit"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed > self.max_processing_time:
            logger.warning(f"⏰ Approaching 6-hour limit ({elapsed/3600:.1f} hours elapsed). Stopping processing.")
            return False
        return True
    
    def fetch_call_logs(self, date_str: str) -> List[Dict]:
        """Fetch call logs for a specific date"""
        try:
            # Parse the date
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Set timezone to match RingCentral (UTC)
            utc = pytz.UTC
            date_from = utc.localize(target_date.replace(hour=0, minute=0, second=0))
            date_to = utc.localize(target_date.replace(hour=23, minute=59, second=59))
            
            # Format for API
            date_from_str = date_from.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            date_to_str = date_to.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            logger.info(f"📅 Fetching call logs from {date_from_str} to {date_to_str}")
            
            all_records = []
            page = 1
            per_page = 1000  # Maximum allowed
            
            while self.should_continue_processing():
                try:
                    response = self.platform.get(
                        f'/restapi/v1.0/account/~/call-log?'
                        f'dateFrom={date_from_str}&dateTo={date_to_str}&'
                        f'recordingType=All&perPage={per_page}&page={page}&'
                        f'view=Detailed'
                    )
                    
                    data = response.json_dict()
                    records = data.get('records', [])
                    
                    if not records:
                        break
                        
                    all_records.extend(records)
                    logger.info(f"📞 Fetched page {page} with {len(records)} records")
                    
                    # Check if there are more pages
                    if 'navigation' in data and 'nextPage' in data['navigation']:
                        page += 1
                        time.sleep(2)  # Small delay between pages
                    else:
                        break
                        
                except Exception as e:
                    logger.error(f"❌ Error fetching page {page}: {str(e)}")
                    break
            
            self.stats["total_calls"] = len(all_records)
            logger.info(f"📊 Found {len(all_records)} total call log entries")
            return all_records
            
        except Exception as e:
            logger.error(f"❌ Error fetching call logs: {str(e)}")
            return []
    
    def filter_recordings_by_duration(self, call_logs: List[Dict], min_duration_seconds: int = 15) -> List[Dict]:
        """Filter call logs to only include recordings longer than minimum duration"""
        filtered_logs = []
        
        for log in call_logs:
            if 'recording' in log and log.get('duration', 0) > min_duration_seconds:
                filtered_logs.append(log)
        
        self.stats["recordings_found"] = len(filtered_logs)
        logger.info(f"🎯 Found {len(filtered_logs)} recordings longer than {min_duration_seconds} seconds")
        return filtered_logs
    
    def download_recording(self, recording_info: Dict, output_dir: Path) -> Optional[str]:
        """Download a single recording with retry logic"""
        recording_id = recording_info.get('id', 'unknown')
        content_uri = recording_info.get('contentUri')
        
        if not content_uri:
            logger.error(f"❌ No content URI for recording {recording_id}")
            return None
        
        # Generate filename
        filename = f"recording_{recording_id}.mp3"
        filepath = output_dir / filename
        
        # Skip if already downloaded
        if filepath.exists() and filepath.stat().st_size > 0:
            logger.info(f"✅ Recording already exists: {filename}")
            return str(filepath)
        
        for attempt in range(self.max_retries):
            try:
                headers = {
                    'Authorization': f'Bearer {self.platform.auth().access_token()}'
                }
                
                response = requests.get(content_uri, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    filepath.write_bytes(response.content)
                    logger.info(f"✅ Downloaded: {filename}")
                    return str(filepath)
                elif response.status_code == 429:
                    # Rate limit - wait longer
                    wait_time = (attempt + 1) * 30
                    logger.warning(f"⚠️ Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Download failed: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Download error attempt {attempt + 1}: {str(e)}")
                
            if attempt < self.max_retries - 1:
                time.sleep(10)
        
        self.stats["errors"] += 1
        return None
    
    def transcribe_audio_with_rotation(self, audio_file_path: str) -> Optional[str]:
        """Transcribe audio using Groq API with key rotation"""
        if not os.path.exists(audio_file_path):
            logger.error(f"❌ Audio file not found: {audio_file_path}")
            return None
        
        for attempt in range(len(self.groq_api_keys)):  # Try each key once
            api_key = self._get_next_groq_key()
            key_index = self.groq_api_keys.index(api_key) + 1
            
            try:
                url = "https://api.groq.com/openai/v1/audio/transcriptions"
                
                with open(audio_file_path, 'rb') as audio_file:
                    files = {
                        'file': (os.path.basename(audio_file_path), audio_file, 'audio/mpeg')
                    }
                    data = {
                        'model': 'whisper-large-v3-turbo',
                        'response_format': 'json',
                        'language': 'en'
                    }
                    headers = {
                        'Authorization': f'Bearer {api_key}'
                    }
                    
                    logger.info(f"🎤 Transcribing with Groq API key #{key_index}")
                    response = requests.post(url, headers=headers, files=files, data=data, timeout=120)
                    
                    # Update usage tracking
                    self.groq_key_usage[api_key] += 1
                    self.groq_key_last_used[api_key] = datetime.now()
                    
                    if response.status_code == 200:
                        result = response.json()
                        transcription = result.get('text', '')
                        logger.info(f"✅ Transcription successful with key #{key_index}")
                        self.groq_key_errors[api_key] = 0  # Reset error count on success
                        return transcription
                    elif response.status_code == 429:
                        logger.warning(f"⚠️ Rate limit hit on key #{key_index}")
                        self.groq_key_errors[api_key] += 1
                        # Try next key immediately
                        continue
                    else:
                        logger.error(f"❌ Transcription failed with key #{key_index}: {response.status_code}")
                        self.groq_key_errors[api_key] += 1
                        
            except Exception as e:
                logger.error(f"❌ Transcription error with key #{key_index}: {str(e)}")
                self.groq_key_errors[api_key] += 1
                
        logger.error("❌ All Groq keys exhausted or errored")
        self.stats["errors"] += 1
        return None
    
    def process_recordings_batch(self, recordings: List[Dict], output_dir: Path) -> Dict:
        """Process recordings in batches for efficiency"""
        results = []
        total = len(recordings)
        
        for i in range(0, total, self.batch_size):
            if not self.should_continue_processing():
                logger.warning("⏰ Time limit reached, stopping batch processing")
                break
                
            batch = recordings[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total + self.batch_size - 1) // self.batch_size
            
            logger.info(f"📦 Processing batch {batch_num}/{total_batches}")
            
            for recording in batch:
                if not self.should_continue_processing():
                    break
                    
                call_log = recording['call_log']
                recording_data = recording['recording']
                
                # Extract call information
                call_info = {
                    'date': call_log.get('startTime', ''),
                    'duration': call_log.get('duration', 0),
                    'from': call_log.get('from', {}).get('phoneNumber', 'Unknown'),
                    'to': call_log.get('to', {}).get('phoneNumber', 'Unknown'),
                    'direction': call_log.get('direction', 'Unknown'),
                    'recording_id': recording_data.get('id', 'unknown')
                }
                
                # Download recording
                logger.info(f"⬇️ Downloading recording {call_info['recording_id']}")
                audio_path = self.download_recording(recording_data, output_dir)
                
                if audio_path:
                    self.stats["recordings_processed"] += 1
                    time.sleep(self.download_delay)
                    
                    # Transcribe
                    logger.info(f"🎯 Transcribing recording {call_info['recording_id']}")
                    transcription = self.transcribe_audio_with_rotation(audio_path)
                    
                    if transcription:
                        self.stats["transcriptions_completed"] += 1
                        call_info['transcription'] = transcription
                        
                        # Save transcription
                        trans_path = Path(audio_path).with_suffix('.txt')
                        trans_path.write_text(transcription, encoding='utf-8')
                    else:
                        call_info['transcription'] = "Transcription failed"
                    
                    time.sleep(self.transcription_delay)
                else:
                    call_info['transcription'] = "Download failed"
                
                results.append(call_info)
                
                # Log progress
                progress = len(results) / total * 100
                elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
                logger.info(f"📊 Progress: {len(results)}/{total} ({progress:.1f}%) - {elapsed:.1f} hours elapsed")
        
        return results
    
    def save_results(self, results: List[Dict], date_str: str, output_dir: Path):
        """Save results to CSV and JSON files"""
        # Save to CSV
        csv_path = output_dir / f"transcriptions_{date_str}.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            if results:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
        logger.info(f"📄 Saved CSV: {csv_path}")
        
        # Save to JSON
        json_path = output_dir / f"transcriptions_{date_str}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"📄 Saved JSON: {json_path}")
        
        # Save summary
        self.stats["total_duration"] = (datetime.now() - self.start_time).total_seconds()
        summary_path = output_dir / "summary.json"
        
        summary = {
            **self.stats,
            "date_processed": date_str,
            "duration_hours": round(self.stats["total_duration"] / 3600, 2),
            "success_rate": f"{(self.stats['transcriptions_completed'] / max(self.stats['recordings_found'], 1) * 100):.1f}%",
            "groq_keys_used": len(self.groq_api_keys),
            "processing_speed": f"{self.stats['recordings_processed'] / max(self.stats['total_duration'] / 3600, 1):.1f} recordings/hour"
        }
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"📊 Saved summary: {summary_path}")
    
    def log_api_key_usage(self):
        """Log detailed API key usage statistics"""
        logger.info("\n🔑 API Key Usage Statistics:")
        logger.info("=" * 50)
        
        total_usage = sum(self.groq_key_usage.values())
        
        for i, key in enumerate(self.groq_api_keys):
            usage = self.groq_key_usage[key]
            errors = self.groq_key_errors[key]
            percentage = (usage / max(total_usage, 1)) * 100
            
            # Mask the key for security
            masked_key = f"{key[:8]}...{key[-4:]}"
            
            logger.info(f"Key #{i+1} ({masked_key}): {usage} uses ({percentage:.1f}%), {errors} errors")
        
        logger.info(f"\nTotal API calls: {total_usage}")
        logger.info("=" * 50)
    
    def process_daily_calls(self, date_to_process: Optional[str] = None):
        """Main method to process daily calls"""
        try:
            # Determine date to process
            if date_to_process:
                process_date = date_to_process
            else:
                # Default to yesterday
                yesterday = datetime.now() - timedelta(days=1)
                process_date = yesterday.strftime("%Y-%m-%d")
            
            logger.info(f"🚀 Starting optimized daily processing for {process_date}")
            logger.info(f"⏱️ Maximum processing time: {self.max_processing_time/3600:.1f} hours")
            
            # Create output directory
            output_dir = Path(self.output_base_dir) / process_date
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Authenticate
            if not self.authenticate():
                logger.error("❌ Failed to authenticate with RingCentral")
                return
            
            # Fetch call logs
            call_logs = self.fetch_call_logs(process_date)
            if not call_logs:
                logger.warning("📭 No call logs found for the specified date")
                return
            
            # Filter for recordings
            recordings_to_process = self.filter_recordings_by_duration(call_logs)
            if not recordings_to_process:
                logger.warning("📭 No qualifying recordings found")
                return
            
            # Prepare recording data
            recording_list = []
            for log in recordings_to_process:
                recording_list.append({
                    'call_log': log,
                    'recording': log['recording']
                })
            
            # Process recordings in batches
            logger.info(f"🎬 Starting batch processing of {len(recording_list)} recordings")
            results = self.process_recordings_batch(recording_list, output_dir)
            
            # Save results
            self.save_results(results, process_date, output_dir)
            
            # Log final statistics
            elapsed_hours = self.stats["total_duration"] / 3600
            logger.info(f"\n✅ Processing completed in {elapsed_hours:.2f} hours")
            logger.info(f"📊 Processed {self.stats['recordings_processed']} recordings")
            logger.info(f"📝 Completed {self.stats['transcriptions_completed']} transcriptions")
            logger.info(f"❌ Errors: {self.stats['errors']}")
            
            # Log API key usage
            self.log_api_key_usage()
            
        except Exception as e:
            logger.error(f"❌ Fatal error in daily processing: {str(e)}")
            raise

def main():
    """Main function to run the daily processor"""
    processor = OptimizedDailyCallProcessor()
    
    # Check if a specific date was provided via environment variable
    target_date = os.getenv("TARGET_DATE")
    
    try:
        processor.process_daily_calls(target_date)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Processing interrupted by user")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
