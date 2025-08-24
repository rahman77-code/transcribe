#!/usr/bin/env python3
"""
Dev Tier Optimized Daily Call Processor
Designed to process 1000+ recordings in under 6 hours using Groq Dev Tier API keys
"""

import os
import json
import csv
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import requests
from ringcentral import SDK
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_call_processor_dev_tier.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DevTierCallProcessor:
    """Optimized processor for Groq Dev Tier API keys"""
    
    def __init__(self):
        """Initialize with dev tier specific configurations"""
        # RingCentral config
        self.config = {
            "clientId": os.getenv("RC_CLIENT_ID"),
            "clientSecret": os.getenv("RC_CLIENT_SECRET"),
            "server": os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com").rstrip('/')
        }
        self.jwt_token = os.getenv("RC_JWT")
        
        # Load only dev tier API keys
        self.dev_tier_keys = self._load_dev_tier_keys()
        self.current_key_index = 0
        
        # Dev tier specific limits (confirmed via testing)
        self.AUDIO_LIMIT_PER_KEY_PER_HOUR = 7200  # seconds
        self.REQUEST_LIMIT_PER_MINUTE = 300  # confirmed dev tier limit works!
        self.SAFETY_BUFFER = 0.9  # Use 90% of limits to be safe
        
        # Track usage per key
        self.key_usage = {
            key: {
                'audio_seconds': 0,
                'request_count': 0,
                'last_reset': datetime.now(),
                'last_minute_reset': datetime.now(),
                'minute_requests': 0,
                'errors': 0,
                'rate_limited': False
            } for key in self.dev_tier_keys
        }
        
        # Optimized delays for dev tier
        # With 300 req/min, we can make 5 requests per second
        self.download_delay = 5  # 5 seconds between downloads (safe for RingCentral)
        self.transcription_delay = 2  # 2 seconds between transcriptions
        self.rate_limit_wait = 60  # Wait 1 minute if rate limited
        
        # Performance tracking
        self.start_time = datetime.now()
        self.stats = {
            "total_calls": 0,
            "recordings_found": 0,
            "recordings_processed": 0,
            "transcriptions_completed": 0,
            "errors": 0,
            "rate_limits_hit": 0,
            "total_audio_seconds": 0
        }
        
        self.output_base_dir = "daily_recordings_dev"
        self.max_retries = 3
        
        logger.info(f"🚀 Dev Tier Processor initialized with {len(self.dev_tier_keys)} API keys")
        logger.info(f"⚡ Limits: {self.AUDIO_LIMIT_PER_KEY_PER_HOUR}s audio/hour, {self.REQUEST_LIMIT_PER_MINUTE} req/min")
        self._estimate_capacity()
        
    def _load_dev_tier_keys(self) -> List[str]:
        """Load only dev tier API keys from environment"""
        dev_keys = []
        
        # Check for dev tier keys specifically marked
        # Option 1: DEV_TIER_KEYS environment variable with comma-separated key numbers
        dev_tier_numbers = os.getenv("DEV_TIER_KEYS", "")
        if dev_tier_numbers:
            key_numbers = [n.strip() for n in dev_tier_numbers.split(",") if n.strip()]
            for num in key_numbers:
                key = os.getenv(f"GROQ_API_KEY_{num}")
                if key:
                    dev_keys.append(key)
                    logger.info(f"✅ Loaded dev tier key #{num}")
        else:
            # Option 2: Look for keys with DEV_TIER prefix
            for i in range(1, 30):  # Check up to 30 keys to support adding new ones
                key = os.getenv(f"GROQ_API_KEY_{i}")
                is_dev = os.getenv(f"GROQ_API_KEY_{i}_IS_DEV", "false").lower() == "true"
                if key and is_dev:
                    dev_keys.append(key)
                    logger.info(f"✅ Loaded dev tier key #{i}")
        
        if not dev_keys:
            # Fallback: Use first 6 keys as dev tier
            logger.warning("⚠️ No dev tier keys specified. Using first 6 keys as dev tier.")
            for i in range(1, 7):
                key = os.getenv(f"GROQ_API_KEY_{i}")
                if key:
                    dev_keys.append(key)
        
        if not dev_keys:
            raise ValueError("❌ No API keys found! Please set up your API keys.")
        
        logger.info(f"📊 Total dev tier keys loaded: {len(dev_keys)}")
        return dev_keys
    
    def _estimate_capacity(self):
        """Estimate processing capacity with current configuration"""
        num_keys = len(self.dev_tier_keys)
        
        # Audio capacity
        audio_capacity_per_hour = num_keys * self.AUDIO_LIMIT_PER_KEY_PER_HOUR * self.SAFETY_BUFFER
        audio_capacity_total = audio_capacity_per_hour * 6  # 6 hours
        
        # Request capacity (limiting factor)
        requests_per_hour = (self.REQUEST_LIMIT_PER_MINUTE * 60 * self.SAFETY_BUFFER)
        total_requests = requests_per_hour * 6
        
        # Time per recording
        time_per_recording = self.download_delay + self.transcription_delay  # 7 seconds
        max_recordings_by_time = (6 * 3600) / time_per_recording  # 6 hours in seconds
        
        # Assuming 2 minute average recordings
        avg_recording_seconds = 120
        max_recordings_by_audio = audio_capacity_total / avg_recording_seconds
        
        logger.info("\n📊 CAPACITY ANALYSIS")
        logger.info("=" * 50)
        logger.info(f"API Keys: {num_keys} dev tier keys")
        logger.info(f"Audio capacity: {audio_capacity_total/3600:.1f} hours total")
        logger.info(f"Max recordings by audio: {max_recordings_by_audio:.0f}")
        logger.info(f"Max recordings by time: {max_recordings_by_time:.0f}")
        logger.info(f"Max recordings by requests: {total_requests:.0f}")
        logger.info(f"🎯 Limiting factor: Time (7s per recording)")
        logger.info(f"✅ Can process ~{min(max_recordings_by_time, max_recordings_by_audio):.0f} recordings in 6 hours")
        logger.info("=" * 50)
    
    def _reset_usage_if_needed(self, key: str):
        """Reset usage counters if hour/minute has passed"""
        usage = self.key_usage[key]
        now = datetime.now()
        
        # Reset hourly audio limit
        if (now - usage['last_reset']).total_seconds() >= 3600:
            usage['audio_seconds'] = 0
            usage['request_count'] = 0
            usage['last_reset'] = now
            usage['errors'] = 0
            usage['rate_limited'] = False
            logger.debug(f"Reset hourly limits for key")
        
        # Reset minute request limit
        if (now - usage['last_minute_reset']).total_seconds() >= 60:
            usage['minute_requests'] = 0
            usage['last_minute_reset'] = now
    
    def _get_best_available_key(self, audio_duration: int) -> Optional[str]:
        """Get the best available key for transcription"""
        best_key = None
        best_score = -1
        
        for key in self.dev_tier_keys:
            self._reset_usage_if_needed(key)
            usage = self.key_usage[key]
            
            # Skip if rate limited
            if usage['rate_limited']:
                continue
            
            # Skip if would exceed audio limit
            if usage['audio_seconds'] + audio_duration > self.AUDIO_LIMIT_PER_KEY_PER_HOUR * self.SAFETY_BUFFER:
                continue
            
            # Skip if at minute request limit
            if usage['minute_requests'] >= self.REQUEST_LIMIT_PER_MINUTE * self.SAFETY_BUFFER:
                continue
            
            # Calculate score (prefer keys with less usage)
            audio_remaining = self.AUDIO_LIMIT_PER_KEY_PER_HOUR - usage['audio_seconds']
            requests_remaining = self.REQUEST_LIMIT_PER_MINUTE - usage['minute_requests']
            
            score = (audio_remaining / self.AUDIO_LIMIT_PER_KEY_PER_HOUR) * \
                   (requests_remaining / self.REQUEST_LIMIT_PER_MINUTE) * \
                   (1 - usage['errors'] / 10)  # Penalize keys with errors
            
            if score > best_score:
                best_score = score
                best_key = key
        
        return best_key
    
    def should_continue_processing(self) -> bool:
        """Check if we should continue processing (time limit)"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        # Stop at 5.5 hours to leave buffer
        return elapsed < 5.5 * 3600
    
    def authenticate(self) -> bool:
        """Authenticate with RingCentral using JWT"""
        try:
            self.sdk = SDK(
                self.config["clientId"],
                self.config["clientSecret"],
                self.config["server"]
            )
            self.platform = self.sdk.platform()
            self.platform.login(jwt=self.jwt_token)
            logger.info("✅ Successfully authenticated with RingCentral")
            return True
        except Exception as e:
            logger.error(f"❌ Authentication failed: {str(e)}")
            return False
    
    def fetch_call_recordings(self, date: Optional[datetime] = None) -> List[Dict]:
        """Fetch all call recordings for a specific date"""
        if date is None:
            date = datetime.now().date() - timedelta(days=1)
        
        date_str = date.strftime('%Y-%m-%d')
        logger.info(f"📅 Fetching recordings for: {date_str}")
        
        all_recordings = []
        page = 1
        per_page = 100
        
        while True:
            try:
                response = self.platform.get(
                    f'/account/~/call-log',
                    {
                        'dateFrom': f'{date_str}T00:00:00.000Z',
                        'dateTo': f'{date_str}T23:59:59.999Z',
                        'page': page,
                        'perPage': per_page,
                        'view': 'Detailed',
                        'withRecording': True
                    }
                )
                
                data = response.json()
                records = data.get('records', [])
                
                for record in records:
                    if record.get('recording'):
                        all_recordings.append({
                            'call_log': record,
                            'recording': record['recording']
                        })
                
                self.stats["total_calls"] += len(records)
                
                navigation = data.get('navigation', {})
                if not navigation.get('nextPage'):
                    break
                
                page += 1
                time.sleep(self.download_delay)
                
            except Exception as e:
                logger.error(f"❌ Error fetching page {page}: {str(e)}")
                break
        
        self.stats["recordings_found"] = len(all_recordings)
        logger.info(f"📊 Found {len(all_recordings)} recordings out of {self.stats['total_calls']} calls")
        return all_recordings
    
    def download_recording(self, recording_info: Dict, output_dir: Path) -> Optional[str]:
        """Download a single recording"""
        try:
            recording_id = recording_info.get('id')
            content_uri = recording_info.get('contentUri')
            
            if not content_uri:
                return None
            
            # Create filename
            filename = f"recording_{recording_id}.mp3"
            filepath = output_dir / filename
            
            # Skip if already exists
            if filepath.exists() and filepath.stat().st_size > 0:
                logger.debug(f"⏭️ Skipping existing: {filename}")
                return str(filepath)
            
            # Download with retries
            for attempt in range(self.max_retries):
                try:
                    response = self.platform.get(content_uri)
                    if response.status_code == 200:
                        filepath.write_bytes(response.content)
                        logger.info(f"✅ Downloaded: {filename} ({len(response.content)/1024/1024:.1f} MB)")
                        return str(filepath)
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"⚠️ Download attempt {attempt + 1} failed, retrying...")
                        time.sleep(5)
                    else:
                        raise
                        
        except Exception as e:
            logger.error(f"❌ Download failed: {str(e)}")
            self.stats["errors"] += 1
            
        return None
    
    def transcribe_audio_with_dev_tier(self, audio_file_path: str) -> Optional[str]:
        """Transcribe audio using dev tier key with smart rotation"""
        if not os.path.exists(audio_file_path):
            logger.error(f"❌ Audio file not found: {audio_file_path}")
            return None
        
        # Estimate audio duration (rough estimate based on file size)
        file_size_mb = os.path.getsize(audio_file_path) / 1024 / 1024
        estimated_duration = int(file_size_mb * 60)  # ~1 minute per MB
        
        # Try each key until successful
        for attempt in range(len(self.dev_tier_keys) * 2):  # Allow 2 rounds
            api_key = self._get_best_available_key(estimated_duration)
            
            if not api_key:
                logger.warning("⏳ No keys available, waiting 60 seconds...")
                time.sleep(60)
                continue
            
            key_index = self.dev_tier_keys.index(api_key) + 1
            usage = self.key_usage[api_key]
            
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
                    
                    logger.info(f"🎤 Transcribing with dev key #{key_index} "
                              f"({usage['audio_seconds']}/{self.AUDIO_LIMIT_PER_KEY_PER_HOUR}s, "
                              f"{usage['minute_requests']}/{self.REQUEST_LIMIT_PER_MINUTE} req/min)")
                    
                    response = requests.post(url, headers=headers, files=files, data=data, timeout=120)
                    
                    # Update usage
                    usage['minute_requests'] += 1
                    usage['request_count'] += 1
                    usage['audio_seconds'] += estimated_duration
                    self.stats['total_audio_seconds'] += estimated_duration
                    
                    if response.status_code == 200:
                        result = response.json()
                        transcription = result.get('text', '')
                        logger.info(f"✅ Transcription successful with key #{key_index}")
                        return transcription
                    elif response.status_code == 429:
                        logger.warning(f"⚠️ Rate limit hit on key #{key_index}")
                        usage['rate_limited'] = True
                        usage['errors'] += 1
                        self.stats['rate_limits_hit'] += 1
                        time.sleep(self.rate_limit_wait)
                    else:
                        logger.error(f"❌ Transcription failed: {response.status_code} - {response.text}")
                        usage['errors'] += 1
                        
            except Exception as e:
                logger.error(f"❌ Transcription error with key #{key_index}: {str(e)}")
                usage['errors'] += 1
        
        logger.error("❌ All transcription attempts failed")
        self.stats["errors"] += 1
        return None
    
    def process_recordings(self, recordings: List[Dict], output_dir: Path) -> List[Dict]:
        """Process all recordings efficiently"""
        results = []
        total = len(recordings)
        
        for i, recording in enumerate(recordings):
            if not self.should_continue_processing():
                logger.warning("⏰ Time limit reached, stopping processing")
                break
            
            recording_num = i + 1
            progress = (recording_num / total) * 100
            elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
            eta = (elapsed / recording_num * total) if recording_num > 0 else 0
            
            logger.info(f"\n[{recording_num}/{total}] Processing recording | {progress:.1f}% | "
                       f"ETA: {eta:.1f}h | Elapsed: {elapsed:.1f}h")
            
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
            audio_path = self.download_recording(recording_data, output_dir)
            
            if audio_path:
                self.stats["recordings_processed"] += 1
                time.sleep(self.download_delay)
                
                # Transcribe
                transcription = self.transcribe_audio_with_dev_tier(audio_path)
                
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
            
            # Log progress stats every 50 recordings
            if recording_num % 50 == 0:
                self._log_progress_stats()
        
        return results
    
    def _log_progress_stats(self):
        """Log detailed progress statistics"""
        elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
        rate = self.stats['recordings_processed'] / elapsed if elapsed > 0 else 0
        
        logger.info("\n📊 PROGRESS STATS")
        logger.info("=" * 50)
        logger.info(f"Recordings processed: {self.stats['recordings_processed']}")
        logger.info(f"Transcriptions completed: {self.stats['transcriptions_completed']}")
        logger.info(f"Processing rate: {rate:.1f} recordings/hour")
        logger.info(f"Audio processed: {self.stats['total_audio_seconds']/3600:.1f} hours")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Rate limits hit: {self.stats['rate_limits_hit']}")
        
        # Key usage stats
        logger.info("\n🔑 KEY USAGE:")
        for i, key in enumerate(self.dev_tier_keys):
            usage = self.key_usage[key]
            audio_pct = (usage['audio_seconds'] / self.AUDIO_LIMIT_PER_KEY_PER_HOUR) * 100
            logger.info(f"Key #{i+1}: {audio_pct:.1f}% audio used, "
                       f"{usage['request_count']} requests, {usage['errors']} errors")
        logger.info("=" * 50)
    
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
        summary = {
            **self.stats,
            "date_processed": date_str,
            "duration_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
            "success_rate": f"{(self.stats['transcriptions_completed'] / max(self.stats['recordings_found'], 1) * 100):.1f}%",
            "dev_tier_keys_used": len(self.dev_tier_keys),
            "processing_speed": f"{self.stats['recordings_processed'] / ((datetime.now() - self.start_time).total_seconds() / 3600):.1f} recordings/hour"
        }
        
        summary_path = output_dir / "summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"📊 Saved summary: {summary_path}")
    
    def run(self, target_date: Optional[datetime] = None):
        """Main execution method"""
        logger.info("\n🚀 STARTING DEV TIER CALL PROCESSOR")
        logger.info("=" * 60)
        
        # Authenticate
        if not self.authenticate():
            logger.error("❌ Failed to authenticate. Exiting.")
            return
        
        # Create output directory
        if target_date is None:
            target_date = datetime.now().date() - timedelta(days=1)
        
        date_str = target_date.strftime('%Y-%m-%d')
        output_dir = Path(self.output_base_dir) / date_str
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Fetch recordings
        recordings = self.fetch_call_recordings(target_date)
        
        if not recordings:
            logger.warning("⚠️ No recordings found for the specified date")
            return
        
        # Process recordings
        logger.info(f"\n🎯 Processing {len(recordings)} recordings...")
        results = self.process_recordings(recordings, output_dir)
        
        # Save results
        self.save_results(results, date_str, output_dir)
        
        # Final summary
        duration = (datetime.now() - self.start_time).total_seconds() / 3600
        logger.info("\n✅ PROCESSING COMPLETE!")
        logger.info("=" * 60)
        logger.info(f"Total time: {duration:.2f} hours")
        logger.info(f"Recordings processed: {self.stats['recordings_processed']}/{self.stats['recordings_found']}")
        logger.info(f"Success rate: {(self.stats['transcriptions_completed'] / max(self.stats['recordings_found'], 1) * 100):.1f}%")
        logger.info(f"Average speed: {self.stats['recordings_processed'] / duration:.1f} recordings/hour")
        
        # Final key usage report
        self._log_progress_stats()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process daily call recordings with dev tier optimization')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD), defaults to yesterday')
    
    args = parser.parse_args()
    
    # Parse date if provided
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        except ValueError:
            logger.error(f"❌ Invalid date format: {args.date}. Use YYYY-MM-DD")
            return
    
    # Run processor
    processor = DevTierCallProcessor()
    processor.run(target_date)


if __name__ == "__main__":
    main()
