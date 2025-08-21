#!/usr/bin/env python3
"""
Reliable Call Processor - Simple, bulletproof transcription
Handles 1000+ recordings without timeouts or rate limit issues
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Import existing modules
try:
    from groq import Groq
    from ringcentral import SDK
except ImportError:
    print("Installing dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "groq", "ringcentral", "python-dotenv", "requests"])
    from groq import Groq
    from ringcentral import SDK

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReliableProcessor:
    def __init__(self):
        # RingCentral setup
        self.rc_client_id = os.getenv("RC_CLIENT_ID")
        self.rc_client_secret = os.getenv("RC_CLIENT_SECRET") 
        self.rc_jwt = os.getenv("RC_JWT")
        self.rc_server_url = os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com")
        
        # Ultra-conservative rate limiting
        self.rc_rps = float(os.getenv("RC_RPS", "0.25"))  # Very slow API calls
        self.rc_media_delay = float(os.getenv("RC_MEDIA_DELAY", "12"))  # 12 seconds between downloads
        self.last_rc_request = 0
        self.last_media_request = 0
        
        # Groq API keys
        self.groq_keys = []
        for i in range(1, 20):
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                self.groq_keys.append(key)
        
        if not self.groq_keys:
            logger.error("❌ No Groq API keys found!")
            sys.exit(1)
        
        logger.info(f"🔑 Using {len(self.groq_keys)} Groq API keys")
        
        # Simple stats
        self.stats = {
            'total_calls': 0,
            'recordings_found': 0,
            'processed': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        # Initialize RingCentral
        self.sdk = SDK(self.rc_client_id, self.rc_client_secret, self.rc_server_url)
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with RingCentral"""
        try:
            self.sdk.platform().login(jwt=self.rc_jwt)
            logger.info("✅ RingCentral authentication successful")
        except Exception as e:
            logger.error(f"❌ RingCentral authentication failed: {e}")
            sys.exit(1)
    
    def _wait_for_rc_api(self):
        """Wait to avoid RingCentral API rate limits"""
        now = time.time()
        time_since_last = now - self.last_rc_request
        min_interval = 1.0 / self.rc_rps
        
        if time_since_last < min_interval:
            wait_time = min_interval - time_since_last
            time.sleep(wait_time)
        
        self.last_rc_request = time.time()
    
    def _wait_for_rc_media(self):
        """Wait to avoid RingCentral media download limits"""
        now = time.time()
        time_since_last = now - self.last_media_request
        
        if time_since_last < self.rc_media_delay:
            wait_time = self.rc_media_delay - time_since_last
            logger.info(f"⏳ Waiting {wait_time:.1f}s before next download (avoiding RC limits)")
            time.sleep(wait_time)
        
        self.last_media_request = time.time()
    
    def get_call_logs(self, target_date: str) -> List[Dict]:
        """Get call logs for specific date"""
        logger.info(f"📅 Fetching call logs for {target_date}")
        
        date_from = f"{target_date}T00:00:00.000Z"
        date_to = f"{target_date}T23:59:59.999Z"
        
        all_records = []
        page = 1
        
        while True:
            try:
                self._wait_for_rc_api()
                response = self.sdk.platform().get(
                    '/restapi/v1.0/account/~/call-log',
                    {
                        'dateFrom': date_from,
                        'dateTo': date_to,
                        'page': page,
                        'perPage': 100,
                        'view': 'Detailed',
                        'withRecording': True
                    }
                )
                
                data = response.json_dict()
                records = data.get('records', [])
                all_records.extend(records)
                
                logger.info(f"📄 Fetched page {page}, found {len(records)} records")
                
                if 'navigation' in data and 'nextPage' in data['navigation']:
                    page += 1
                else:
                    break
                    
            except Exception as e:
                logger.error(f"❌ Error fetching call logs: {e}")
                break
        
        # Filter recordings > 20 seconds
        recordings = [r for r in all_records if r.get('recording') and r.get('duration', 0) > 20]
        
        self.stats['total_calls'] = len(all_records)
        self.stats['recordings_found'] = len(recordings)
        
        logger.info(f"📊 Found {len(recordings)} recordings (from {len(all_records)} total calls)")
        return recordings
    
    def download_recording(self, call_log: Dict, output_dir: Path) -> Optional[str]:
        """Download recording file"""
        recording_id = call_log.get('recording', {}).get('id')
        content_uri = call_log.get('recording', {}).get('contentUri')
        
        if not content_uri:
            return None
        
        output_file = output_dir / f"recording_{recording_id}.mp3"
        
        if output_file.exists():
            return str(output_file)
        
        # Conservative download with retries
        for attempt in range(3):
            try:
                self._wait_for_rc_media()
                response = self.sdk.platform().get(content_uri)
                
                # Get content
                if hasattr(response, '_response'):
                    content = response._response.content
                else:
                    content = response.content() if hasattr(response, 'content') else response.body()
                
                if content:
                    output_file.write_bytes(content)
                    return str(output_file)
                
            except Exception as e:
                logger.warning(f"⚠️ Download attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    time.sleep(10 * (attempt + 1))  # Progressive backoff
        
        logger.error(f"❌ Failed to download recording {recording_id}")
        return None
    
    def transcribe_recording(self, audio_path: str, call_log: Dict) -> Optional[Dict]:
        """Transcribe audio file"""
        if not os.path.exists(audio_path):
            return None
        
        # Try each Groq key
        for key_idx, api_key in enumerate(self.groq_keys):
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
                
                return {
                    'id': call_log.get('recording', {}).get('id'),
                    'date': call_log.get('startTime', ''),
                    'duration': call_log.get('duration', 0),
                    'from': call_log.get('from', {}).get('phoneNumber', ''),
                    'to': call_log.get('to', {}).get('phoneNumber', ''),
                    'direction': call_log.get('direction', ''),
                    'transcription': transcription
                }
                
            except Exception as e:
                logger.warning(f"⚠️ Transcription failed with key {key_idx + 1}: {e}")
                if "rate" in str(e).lower():
                    time.sleep(2)  # Rate limit backoff
                continue
        
        return None
    
    def save_results(self, results: List[Dict], output_dir: Path, target_date: str):
        """Save results to files"""
        if not results:
            return
        
        # Sort by date
        results.sort(key=lambda x: x.get('date', ''))
        
        # Save JSON
        json_file = output_dir / f"transcriptions_{target_date}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Save CSV
        csv_file = output_dir / f"transcriptions_{target_date}.csv"
        with open(csv_file, 'w', encoding='utf-8') as f:
            f.write("Recording ID,Date,Duration (seconds),From,To,Direction,Transcription\n")
            for result in results:
                transcription = result["transcription"].replace('"', '""')
                f.write(f'"{result["id"]}","{result["date"]}",{result["duration"]},'
                       f'"{result["from"]}","{result["to"]}","{result["direction"]}","{transcription}"\n')
        
        logger.info(f"💾 Saved {len(results)} results to {json_file} and {csv_file}")
    
    def process_recordings(self, call_logs: List[Dict], output_dir: Path, target_date: str):
        """Process recordings one by one (simple and reliable)"""
        results = []
        total = len(call_logs)
        
        logger.info(f"🚀 Starting to process {total} recordings")
        
        for i, call_log in enumerate(call_logs, 1):
            logger.info(f"📊 Processing {i}/{total} ({i/total*100:.1f}%)")
            
            try:
                # Download recording
                audio_path = self.download_recording(call_log, output_dir)
                if not audio_path:
                    self.stats['errors'] += 1
                    continue
                
                # Transcribe recording
                result = self.transcribe_recording(audio_path, call_log)
                if result:
                    results.append(result)
                    self.stats['processed'] += 1
                    
                    # Save progress every 10 recordings
                    if len(results) % 10 == 0:
                        self.save_results(results, output_dir, target_date)
                        logger.info(f"💾 Saved progress: {len(results)} completed")
                else:
                    self.stats['errors'] += 1
                
            except Exception as e:
                logger.error(f"❌ Error processing recording {i}: {e}")
                self.stats['errors'] += 1
        
        # Final save
        self.save_results(results, output_dir, target_date)
        
        # Summary
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        logger.info("=" * 60)
        logger.info(f"✅ PROCESSING COMPLETE")
        logger.info(f"📊 Total recordings: {self.stats['recordings_found']}")
        logger.info(f"✅ Successfully processed: {self.stats['processed']}")
        logger.info(f"❌ Errors: {self.stats['errors']}")
        logger.info(f"⏱️ Total time: {elapsed/3600:.2f} hours")
        logger.info(f"⚡ Rate: {self.stats['processed']/(elapsed/60):.1f} recordings/minute")
        logger.info("=" * 60)
    
    def run(self, target_date: Optional[str] = None):
        """Main processing function"""
        if not target_date:
            # Default to yesterday
            central_tz = timezone(timedelta(hours=-6))
            yesterday = datetime.now(central_tz) - timedelta(days=1)
            target_date = yesterday.strftime("%Y-%m-%d")
            logger.info(f"🗓️ No date specified, using yesterday: {target_date}")
        
        logger.info(f"🚀 Starting reliable processing for {target_date}")
        
        # Get call logs
        call_logs = self.get_call_logs(target_date)
        if not call_logs:
            logger.warning("⚠️ No recordings found")
            return
        
        # Create output directory
        output_dir = Path(f"daily_recordings/{target_date}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process all recordings
        self.process_recordings(call_logs, output_dir, target_date)

def main():
    target_date = os.getenv("TARGET_DATE")
    processor = ReliableProcessor()
    processor.run(target_date)

if __name__ == "__main__":
    main()
