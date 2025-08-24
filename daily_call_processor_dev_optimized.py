#!/usr/bin/env python3
"""
Dev Tier Optimized Daily Call Processor
Maximizes throughput with 6 dev tier keys (300 RPM each = 1,800 RPM total)
Uses concurrent processing for downloads and transcriptions
"""

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
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue, Empty
from ringcentral import SDK
from dotenv import load_dotenv

# Auto-install groq if not available
try:
    from groq import Groq
except ImportError:
    print("Groq package not found. Please install dependencies from requirements.txt")
    print("pip install -r requirements.txt")
    sys.exit(1)

# Set up logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_call_processor_dev_optimized.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DevTierOptimizedProcessor:
    def __init__(self):
        # RingCentral configuration
        self.rc_client_id = os.getenv("RC_CLIENT_ID")
        self.rc_client_secret = os.getenv("RC_CLIENT_SECRET")
        self.rc_jwt = os.getenv("RC_JWT")
        self.rc_server_url = os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com").rstrip('/')
        
        # Initialize Groq API keys (expecting 6 dev tier keys)
        self.groq_api_keys = []
        for i in range(1, 20):  # Check up to 20 keys
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                self.groq_api_keys.append(key)
        
        if not self.groq_api_keys:
            logger.error("❌ No Groq API keys found!")
            sys.exit(1)
        
        # Dev tier configuration
        self.dev_tier_keys = os.getenv("DEV_TIER_KEYS", "")
        if self.dev_tier_keys:
            # Use only specified dev tier keys
            dev_indices = [int(x.strip())-1 for x in self.dev_tier_keys.split(",")]
            self.groq_api_keys = [self.groq_api_keys[i] for i in dev_indices if i < len(self.groq_api_keys)]
        
        # Rate limiting for 300 RPM per key
        self.groq_rpm = 300
        self.rate_limiters = {}
        for key in self.groq_api_keys:
            self.rate_limiters[key] = {
                'lock': threading.Lock(),
                'requests': [],
                'errors': 0,
                'usage': 0
            }
        
        # RingCentral throttling (prevent 429 CMN-301)
        # Default: ~0.3 request/second for large batch processing
        self.rc_rps = float(os.getenv("RC_RPS", "0.3"))  # Very conservative for 1000+ recordings
        self.rc_requests: list[float] = []
        self.rc_throttle_lock = threading.Lock()
        self.rc_media_requests: list[float] = []
        self.rc_media_throttle_lock = threading.Lock()
        self.rc_media_delay = 10.0  # Extra conservative for large batches (6 RPM)

        # Concurrent processing configuration
        # RingCentral has strict rate limits on media downloads, so it's safer to download one at a time.
        self.download_workers = int(os.getenv("RC_DOWNLOAD_WORKERS", "1"))
        self.transcription_workers = len(self.groq_api_keys) * 2  # 2 workers per key
        
        logger.info(f"🚀 DEV TIER OPTIMIZED PROCESSOR")
        logger.info(f"🔑 Using {len(self.groq_api_keys)} dev tier keys")
        logger.info(f"⚡ Total capacity: {300 * len(self.groq_api_keys)} RPM")
        logger.info(f"🔄 Concurrent workers: {self.download_workers} download, {self.transcription_workers} transcription")
        
        # Initialize RingCentral
        self.sdk = None
        self.last_token_refresh = None
        self.token_refresh_interval = 3000  # 50 minutes
        self.rc_lock = threading.Lock()
        self.download_lock = threading.Lock()  # Ensure only one download at a time
        
        # Performance tracking
        self.stats = {
            "total_calls": 0,
            "recordings_found": 0,
            "recordings_processed": 0,
            "recordings_skipped": 0,
            "download_errors": 0,
            "transcription_errors": 0,
            "total_audio_seconds": 0,
            "start_time": datetime.now()
        }
        
        # Configuration
        self.min_duration_seconds = 20
        self.max_processing_time = 5.5 * 3600  # 5.5 hours safety limit
        
        self._authenticate()
    
    def _rc_wait(self):
        """Global RingCentral rate limiter based on RC_RPS."""
        with self.rc_throttle_lock:
            now = time.time()
            target_delay = 1.0 / self.rc_rps
            if self.rc_requests:
                last_req_time = self.rc_requests[-1]
                elapsed = now - last_req_time
                if elapsed < target_delay:
                    sleep_for = target_delay - elapsed
                    time.sleep(sleep_for)
            
            self.rc_requests.append(time.time())
            self.rc_requests = self.rc_requests[-100:] # Prune to prevent memory leak

    def _rc_media_wait(self):
        """Specific rate limiter for RingCentral media downloads (Heavy usage)."""
        with self.rc_media_throttle_lock:
            now = time.time()
            if self.rc_media_requests:
                last_req_time = self.rc_media_requests[-1]
                elapsed = now - last_req_time
                if elapsed < self.rc_media_delay:
                    sleep_for = self.rc_media_delay - elapsed
                    time.sleep(sleep_for)
            
            self.rc_media_requests.append(time.time())
            self.rc_media_requests = self.rc_media_requests[-20:] # Prune
    
    def _authenticate(self):
        """Authenticate with RingCentral"""
        try:
            with self.rc_lock:
                self.sdk = SDK(self.rc_client_id, self.rc_client_secret, self.rc_server_url)
                self.sdk.platform().login(jwt=self.rc_jwt)
                self.last_token_refresh = datetime.now()
                logger.info("✅ Successfully authenticated with RingCentral")
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            raise
    
    def _should_refresh_token(self) -> bool:
        """Check if token needs refresh"""
        if not self.last_token_refresh:
            return True
        elapsed = (datetime.now() - self.last_token_refresh).total_seconds()
        return elapsed >= self.token_refresh_interval
    
    def _ensure_auth(self):
        """Ensure we're authenticated"""
        if self._should_refresh_token():
            self._authenticate()
    
    def _wait_for_rate_limit(self, api_key: str) -> bool:
        """Ensure we don't exceed 300 RPM for a specific key"""
        limiter = self.rate_limiters[api_key]
        with limiter['lock']:
            now = time.time()
            # Remove requests older than 1 minute
            limiter['requests'] = [t for t in limiter['requests'] if now - t < 60]
            
            # Check if we need to wait
            if len(limiter['requests']) >= self.groq_rpm:
                # Calculate wait time
                oldest = limiter['requests'][0]
                wait_time = 60 - (now - oldest) + 0.1
                if wait_time > 0:
                    time.sleep(wait_time)
                    # Clean again after wait
                    limiter['requests'] = [t for t in limiter['requests'] if time.time() - t < 60]
            
            # Record this request
            limiter['requests'].append(time.time())
            return True
    
    def _get_best_key(self) -> Optional[str]:
        """Get the API key with lowest current usage"""
        best_key = None
        min_usage = float('inf')
        
        for key in self.groq_api_keys:
            limiter = self.rate_limiters[key]
            with limiter['lock']:
                current_rpm = len(limiter['requests'])
                if current_rpm < min_usage and limiter['errors'] < 5:
                    min_usage = current_rpm
                    best_key = key
        
        return best_key
    
    def get_call_logs(self, target_date: str) -> List[Dict]:
        """Get call logs for a specific date"""
        logger.info(f"📅 Fetching call logs for {target_date}")
        
        self._ensure_auth()
        
        # Date range for the target date (in UTC)
        date_from = f"{target_date}T00:00:00.000Z"
        date_to = f"{target_date}T23:59:59.999Z"
        
        all_records = []
        page = 1
        per_page = 100
        
        while True:
            try:
                with self.rc_lock:
                    # Global throttle for RingCentral API
                    self._rc_wait()
                    self._ensure_auth()
                    response = self.sdk.platform().get(
                        '/restapi/v1.0/account/~/call-log',
                        {
                            'dateFrom': date_from,
                            'dateTo': date_to,
                            'page': page,
                            'perPage': per_page,
                            'view': 'Detailed',
                            'withRecording': True
                        }
                    )
                
                data = response.json_dict()
                records = data.get('records', [])
                all_records.extend(records)
                
                # Check if there are more pages
                if 'navigation' in data and 'nextPage' in data['navigation']:
                    page += 1
                    time.sleep(2.0)  # Longer delay to avoid RingCentral 429
                else:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching call logs: {e}")
                break
        
        # Filter for recordings longer than minimum duration
        recordings = []
        for record in all_records:
            if record.get('recording') and record.get('duration', 0) > self.min_duration_seconds:
                recordings.append(record)
            elif record.get('recording') and record.get('duration', 0) <= self.min_duration_seconds:
                self.stats['recordings_skipped'] += 1
        
        self.stats['total_calls'] = len(all_records)
        self.stats['recordings_found'] = len(recordings)
        
        logger.info(f"📊 Found {len(recordings)} recordings (skipped {self.stats['recordings_skipped']} short recordings)")
        return recordings
    
    def download_recording(self, call_log: Dict, output_dir: Path) -> Optional[Tuple[str, Dict]]:
        """Download a recording (returns path and metadata)"""
        with self.download_lock:  # Ensure only one download at a time
            try:
                recording_id = call_log.get('recording', {}).get('id')
                content_uri = call_log.get('recording', {}).get('contentUri')
                
                if not content_uri:
                    return None
                
                output_file = output_dir / f"recording_{recording_id}.mp3"
                
                # Skip if already exists
                if output_file.exists():
                    # Small delay even for skipped files to maintain rate limit
                    time.sleep(1.0)
                    return str(output_file), call_log
                
                # Download with retries and backoff on 429
                backoff = 30.0  # Start with 30 second delay for 429 errors
                for attempt in range(6):
                    try:
                        with self.rc_lock:
                            # Global throttle for RingCentral media content
                            self._rc_media_wait()
                            self._ensure_auth()
                            response = self.sdk.platform().get(content_uri)
                        
                        # Determine status code if available
                        status_code = None
                        if hasattr(response, '_response'):
                            status_code = getattr(response._response, 'status_code', None)
                        if status_code is None:
                            status_code = getattr(response, 'status_code', None)

                        # Get content from RingCentral response
                        if hasattr(response, '_response'):
                            content = response._response.content
                        else:
                            content = response.content() if hasattr(response, 'content') else response.body()
                        
                        if status_code == 429 or (not content):
                            # Backoff and retry on rate limit or empty body
                            logger.warning(f"Download hit RC 429 or empty body; backing off {backoff}s and retrying")
                            time.sleep(backoff)
                            backoff = min(backoff * 1.5, 60)  # Slower increase, max 60s
                            continue

                        if content:
                            output_file.write_bytes(content)
                            # Add delay after successful download to avoid hitting rate limits
                            time.sleep(3.0)
                            return str(output_file), call_log
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg or "CMN-301" in error_msg or "rate exceeded" in error_msg.lower():
                            logger.warning(f"RingCentral 429 rate limit hit, waiting {backoff}s before retry")
                            time.sleep(backoff)
                            backoff = min(backoff * 2, 90)  # Double backoff, max 90s
                            if attempt < 5:
                                continue
                        elif attempt < 5:
                            # Other errors, shorter backoff
                            time.sleep(5)
                        else:
                            raise
                
            except Exception as e:
                self.stats['download_errors'] += 1
                logger.error(f"Download failed: {e}")
            
            return None
    
    def transcribe_recording(self, audio_path: str, call_log: Dict) -> Optional[Dict]:
        """Transcribe a recording using Groq"""
        if not os.path.exists(audio_path):
            return None
        
        # Try transcription with key rotation
        for attempt in range(len(self.groq_api_keys)):
            api_key = self._get_best_key()
            if not api_key:
                time.sleep(1)
                continue
            
            # Wait for rate limit
            self._wait_for_rate_limit(api_key)
            
            try:
                client = Groq(api_key=api_key)
                
                with open(audio_path, 'rb') as audio_file:
                    response = client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo",
                        file=audio_file,
                        response_format="text",
                        language="en"
                    )
                
                transcription = response.strip() if isinstance(response, str) else str(response)
                
                # Update stats
                limiter = self.rate_limiters[api_key]
                limiter['usage'] += 1
                
                # Prepare result
                result = {
                    'id': call_log.get('recording', {}).get('id'),
                    'date': call_log.get('startTime', ''),
                    'duration': call_log.get('duration', 0),
                    'from': call_log.get('from', {}).get('phoneNumber', ''),
                    'to': call_log.get('to', {}).get('phoneNumber', ''),
                    'direction': call_log.get('direction', ''),
                    'transcription': transcription
                }
                
                self.stats['recordings_processed'] += 1
                self.stats['total_audio_seconds'] += call_log.get('duration', 0)
                
                return result
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "rate" in error_msg.lower():
                    limiter = self.rate_limiters[api_key]
                    limiter['errors'] += 1
                    time.sleep(1)
                else:
                    logger.error(f"Transcription error: {e}")
                    self.stats['transcription_errors'] += 1
        
        return None
    
    def process_recordings_concurrent(self, call_logs: List[Dict], output_dir: Path, target_date: str):
        """Process recordings using concurrent downloads and transcriptions"""
        results = []
        results_lock = threading.Lock()
        
        # Create work queues
        download_queue = Queue()
        transcription_queue = Queue()
        
        # Fill download queue
        for call_log in call_logs:
            download_queue.put(call_log)
        
        download_finished = threading.Event()

        def download_worker():
            """Worker for downloading recordings"""
            while not download_finished.is_set():
                try:
                    call_log = download_queue.get(timeout=1)
                    try:
                        result = self.download_recording(call_log, output_dir)
                        if result:
                            transcription_queue.put(result)
                    except Exception as e:
                        logger.error(f"Error downloading for call {call_log.get('id', 'N/A')}: {e}")
                        self.stats['download_errors'] += 1
                    finally:
                        download_queue.task_done()
                except Empty:
                    if download_finished.is_set():
                        break
        
        def transcription_worker():
            """Worker for transcribing recordings"""
            while not (download_finished.is_set() and transcription_queue.empty()):
                try:
                    audio_path, call_log = transcription_queue.get(timeout=5)
                    try:
                        result = self.transcribe_recording(audio_path, call_log)
                        if result:
                            with results_lock:
                                results.append(result)
                    except Exception as e:
                        logger.error(f"Error transcribing for call {call_log.get('id', 'N/A')}: {e}")
                        self.stats['transcription_errors'] += 1
                    finally:
                        transcription_queue.task_done()
                except Empty:
                    pass
        
        # Start workers
        download_threads = []
        for _ in range(self.download_workers):
            t = threading.Thread(target=download_worker, daemon=True)
            t.start()
            download_threads.append(t)
        
        transcription_threads = []
        for _ in range(self.transcription_workers):
            t = threading.Thread(target=transcription_worker, daemon=True)
            t.start()
            transcription_threads.append(t)
        
        # Monitor progress
        start_time = time.time()
        total = len(call_logs)
        
        # Main monitoring loop
        while any(t.is_alive() for t in download_threads) or any(t.is_alive() for t in transcription_threads):
            time.sleep(10)
            
            # Check if downloads are done
            if not download_finished.is_set() and not any(t.is_alive() for t in download_threads):
                download_finished.set()
                logger.info("✅ All download tasks completed.")

            with results_lock:
                processed = len(results)
            
            elapsed = time.time() - start_time
            if processed > 0:
                rate = processed / (elapsed / 60)  # per minute
                eta_minutes = (total - processed) / rate if rate > 0 else 0
                logger.info(f"📊 Progress: {processed}/{total} ({processed/total*100:.1f}%) "
                          f"| Rate: {rate:.0f}/min | ETA: {eta_minutes:.1f} min")
            else:
                logger.info(f"📊 Progress: 0/{total} (0.0%) | Rate: 0/min | ETA: inf")
            
            # Check time limit
            if elapsed > self.max_processing_time:
                logger.warning("⏰ Time limit reached, stopping processing")
                download_finished.set()  # Signal all workers to stop
                break
        
        # Final check for worker completion
        for t in download_threads:
            t.join(timeout=10)
        for t in transcription_threads:
            t.join(timeout=10)
        
        logger.info("✅ All workers have finished.")

        # Save results
        self.save_results(results, output_dir, target_date)
    
    def save_results(self, results: List[Dict], output_dir: Path, target_date: str):
        """Save results to JSON and CSV files with statistics"""
        # Sort by date
        results.sort(key=lambda x: x.get('date', ''))
        
        # Prepare statistics summary
        stats_summary = {
            'processing_date': target_date,
            'total_recordings_found': self.stats['recordings_found'],
            'total_recordings_processed': self.stats['recordings_processed'],
            'total_recordings_skipped': self.stats['recordings_skipped'],
            'success_rate': f"{(self.stats['recordings_processed'] / max(self.stats['recordings_found'], 1) * 100):.1f}%",
            'total_audio_minutes': round(self.stats['total_audio_seconds'] / 60, 1),
            'download_errors': self.stats['download_errors'],
            'transcription_errors': self.stats['transcription_errors']
        }
        
        # Save enhanced JSON with statistics
        json_file = output_dir / f"transcriptions_{target_date}.json"
        json_data = {
            'statistics': stats_summary,
            'transcriptions': results
        }
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        # Save CSV with statistics header
        csv_file = output_dir / f"transcriptions_{target_date}.csv"
        with open(csv_file, 'w', encoding='utf-8') as f:
            # Write statistics as comments
            f.write(f"# Processing Statistics for {target_date}\n")
            f.write(f"# Total Recordings Found: {stats_summary['total_recordings_found']}\n")
            f.write(f"# Total Recordings Processed: {stats_summary['total_recordings_processed']}\n")
            f.write(f"# Total Recordings Skipped (too short): {stats_summary['total_recordings_skipped']}\n")
            f.write(f"# Success Rate: {stats_summary['success_rate']}\n")
            f.write(f"# Total Audio Time: {stats_summary['total_audio_minutes']} minutes\n")
            f.write(f"#\n")
            
            # Write data headers and rows
            f.write("Recording ID,Date,Duration (seconds),From,To,Direction,Transcription\n")
            for result in results:
                transcription_escaped = result["transcription"].replace('"', '""')
                line = f'"{result["id"]}","{result["date"]}",{result["duration"]},"{result["from"]}","{result["to"]}","{result["direction"]}","{transcription_escaped}"\n'
                f.write(line)
        
        # Save summary
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        summary = {
            'date': target_date,
            'total_calls': self.stats['total_calls'],
            'recordings_found': self.stats['recordings_found'],
            'recordings_processed': self.stats['recordings_processed'],
            'recordings_skipped': self.stats['recordings_skipped'],
            'download_errors': self.stats['download_errors'],
            'transcription_errors': self.stats['transcription_errors'],
            'total_audio_hours': round(self.stats['total_audio_seconds'] / 3600, 2),
            'processing_time_hours': round(elapsed / 3600, 2),
            'success_rate': f"{(self.stats['recordings_processed'] / max(self.stats['recordings_found'], 1) * 100):.1f}%",
            'processing_rate_per_hour': round(self.stats['recordings_processed'] / (elapsed / 3600), 1),
            'api_keys_used': len(self.groq_api_keys),
            'total_rpm_capacity': len(self.groq_api_keys) * 300
        }
        
        summary_file = output_dir / "summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"📊 Saved results: {json_file}, {csv_file}, {summary_file}")
    
    def run(self, target_date: str):
        """Main processing function"""
        logger.info(f"🚀 Starting DEV TIER optimized processing for {target_date}")
        
        # Get call logs
        call_logs = self.get_call_logs(target_date)
        
        if not call_logs:
            logger.warning("⚠️ No recordings found for the specified date")
            return
        
        # Create output directory
        output_dir = Path(f"daily_recordings/{target_date}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process recordings concurrently
        self.process_recordings_concurrent(call_logs, output_dir, target_date)
        
        # Final stats
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        logger.info("\n" + "="*80)
        logger.info(f"✅ Processing completed in {elapsed/3600:.2f} hours")
        logger.info(f"📊 Processed: {self.stats['recordings_processed']}/{self.stats['recordings_found']} recordings")
        logger.info(f"⚡ Rate: {self.stats['recordings_processed'] / (elapsed / 60):.0f} recordings/minute")
        logger.info(f"🎙️ Total audio: {self.stats['total_audio_seconds'] / 3600:.1f} hours")
        
        # Log API key usage
        logger.info("\n🔑 API Key Performance:")
        for i, key in enumerate(self.groq_api_keys):
            limiter = self.rate_limiters[key]
            usage = limiter['usage']
            errors = limiter['errors']
            logger.info(f"Key #{i+1}: {usage} requests, {errors} errors")
        
        logger.info("="*80)


def main():
    # Load environment variables from .env file
    load_dotenv()

    # Get target date from environment or default to yesterday
    target_date = os.getenv("TARGET_DATE")
    if not target_date:
        # Default to yesterday in Central Time
        central_tz = timezone(timedelta(hours=-6))
        yesterday = datetime.now(central_tz) - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")
        logger.info(f"No date specified, defaulting to yesterday: {target_date}")
    
    processor = DevTierOptimizedProcessor()
    processor.run(target_date)


if __name__ == "__main__":
    main()
