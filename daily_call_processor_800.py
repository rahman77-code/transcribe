"""
Optimized Daily RingCentral Call Recording Processor for 800+ calls
Designed to handle high volume within GitHub Actions 24-hour limit
"""

import os
import json
import csv
import time
from datetime import datetime, timedelta
from pathlib import Path
from ringcentral import SDK
from transcribe_audio import transcribe_audio, save_transcription
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_call_processor_800.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

class OptimizedCallProcessor800:
    def __init__(self):
        # RingCentral credentials
        self.config = {
            "clientId": os.getenv("RC_CLIENT_ID"),
            "clientSecret": os.getenv("RC_CLIENT_SECRET"),
            "server": os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com").rstrip('/')
        }
        self.jwt_token = os.getenv("RC_JWT")
        
        # Load ALL Groq API keys (up to 10)
        self.groq_api_keys = self._load_groq_keys()
        self.current_key_index = 0
        
        # OPTIMIZED delays for 800 recordings in 22 hours
        # 800 recordings * 100s = 80,000s = 22.2 hours
        self.download_delay = 40  # 40 seconds between downloads
        self.transcription_delay = 60  # 60 seconds between transcriptions
        self.api_call_delay = 2  # 2 seconds between API calls
        
        # Track usage per key
        self.key_usage = {
            key: {
                'seconds_used': 0,
                'last_reset': datetime.now(),
                'calls_made': 0
            } for key in self.groq_api_keys
        }
        
        # Adjusted limits for safety
        self.max_seconds_per_key_per_hour = 6500  # Still safe buffer from 7200
        self.max_calls_per_key_per_hour = 50
        
        logging.info(f"🚀 Optimized for 800+ calls with {len(self.groq_api_keys)} API keys")
        
    def _load_groq_keys(self):
        """Load ALL available Groq API keys"""
        keys = []
        
        # Try to load up to 10 numbered keys
        for i in range(1, 11):
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                keys.append(key)
                logging.info(f"✅ Loaded GROQ_API_KEY_{i}")
        
        # Also check single key format
        single_key = os.getenv("GROQ_API_KEY")
        if single_key and single_key not in keys:
            keys.append(single_key)
        
        # Check comma-separated format
        csv_keys = os.getenv("GROQ_API_KEYS", "")
        if csv_keys:
            for key in csv_keys.split(','):
                key = key.strip()
                if key and key not in keys:
                    keys.append(key)
        
        if len(keys) < 5:
            logging.warning(f"⚠️  Only {len(keys)} API keys loaded. Recommended: 5-6 keys for 800 calls")
        else:
            logging.info(f"✅ Loaded {len(keys)} API keys - sufficient for high volume!")
        
        return keys
    
    def estimate_completion(self, num_recordings):
        """Estimate completion time and show progress"""
        total_seconds = num_recordings * (self.download_delay + self.transcription_delay)
        hours = total_seconds / 3600
        
        # Calculate capacity
        processing_hours = hours
        capacity_per_key = 6500 * processing_hours / 3600  # seconds per key
        total_capacity = capacity_per_key * len(self.groq_api_keys)
        
        # Assume 2 min average per recording
        required_capacity = num_recordings * 120  # seconds
        
        logging.info(f"\n📊 PROCESSING ESTIMATE:")
        logging.info(f"- Recordings to process: {num_recordings}")
        logging.info(f"- Time per recording: {self.download_delay + self.transcription_delay}s")
        logging.info(f"- Total processing time: {hours:.1f} hours")
        logging.info(f"- Available API keys: {len(self.groq_api_keys)}")
        logging.info(f"- Total transcription capacity: {total_capacity/3600:.1f} hours of audio")
        logging.info(f"- Required capacity: {required_capacity/3600:.1f} hours of audio")
        
        if required_capacity > total_capacity:
            logging.warning(f"⚠️  May need more API keys! Add {int((required_capacity - total_capacity) / capacity_per_key) + 1} more keys")
        else:
            logging.info(f"✅ Sufficient API keys for this volume!")
        
        return hours
    
    def get_available_groq_key(self, audio_duration_seconds):
        """Get an available Groq API key with smart rotation"""
        current_time = datetime.now()
        
        # First, reset any keys that have been idle for an hour
        for key in self.groq_api_keys:
            usage = self.key_usage[key]
            time_since_reset = (current_time - usage['last_reset']).total_seconds()
            if time_since_reset >= 3600:
                usage['seconds_used'] = 0
                usage['calls_made'] = 0
                usage['last_reset'] = current_time
        
        # Find the key with most remaining capacity
        best_key = None
        best_remaining = 0
        
        for key in self.groq_api_keys:
            usage = self.key_usage[key]
            remaining = self.max_seconds_per_key_per_hour - usage['seconds_used']
            
            if remaining >= audio_duration_seconds and usage['calls_made'] < self.max_calls_per_key_per_hour:
                if remaining > best_remaining:
                    best_key = key
                    best_remaining = remaining
        
        if best_key:
            usage = self.key_usage[best_key]
            usage['seconds_used'] += audio_duration_seconds
            usage['calls_made'] += 1
            key_index = self.groq_api_keys.index(best_key) + 1
            logging.info(f"🔑 Using API key #{key_index} ({usage['seconds_used']}/{self.max_seconds_per_key_per_hour}s used)")
            return best_key
        
        # No key available - need to wait
        logging.warning("⏳ All keys at capacity. Waiting for reset...")
        return None
    
    def authenticate(self):
        """Authenticate with RingCentral"""
        try:
            sdk = SDK(self.config["clientId"], self.config["clientSecret"], self.config["server"])
            platform = sdk.platform()
            platform.login(jwt=self.jwt_token)
            logging.info("✅ Successfully authenticated with RingCentral")
            return platform
        except Exception as e:
            logging.error(f"❌ Authentication failed: {e}")
            return None
    
    def fetch_daily_calls(self, platform, date=None):
        """Fetch all calls for a specific date"""
        if date is None:
            date = datetime.now().date() - timedelta(days=1)
        
        date_str = date.strftime('%Y-%m-%d')
        date_from = f"{date_str}T00:00:00.000Z"
        date_to = f"{(date + timedelta(days=1)).strftime('%Y-%m-%d')}T00:00:00.000Z"
        
        logging.info(f"📅 Fetching calls for: {date_str}")
        
        all_records = []
        page = 1
        per_page = 1000
        
        while True:
            try:
                url = (f"/restapi/v1.0/account/~/call-log?"
                       f"dateFrom={date_from}&dateTo={date_to}"
                       f"&page={page}&perPage={per_page}"
                       f"&view=Detailed")
                
                response = platform.get(url)
                data = response.json_dict()
                
                records = data.get('records', [])
                all_records.extend(records)
                
                paging = data.get('paging', {})
                total_pages = paging.get('totalPages', 1)
                
                if page >= total_pages:
                    break
                
                page += 1
                time.sleep(self.api_call_delay)
                
            except Exception as e:
                logging.error(f"Error fetching page {page}: {e}")
                break
        
        logging.info(f"📞 Total calls found: {len(all_records)}")
        return all_records
    
    def process_recording_optimized(self, platform, record, output_dir, index, total):
        """Process a single recording with optimized delays"""
        if not record.get('recording', {}).get('id'):
            return None
            
        recording_id = record['recording']['id']
        duration_seconds = record.get('duration', 0)
        
        # Progress indicator
        progress = (index / total) * 100
        logging.info(f"\n[{index}/{total}] 📍 Processing recording {recording_id} ({progress:.1f}% complete)")
        
        try:
            # Download with optimized delay
            logging.info(f"⏳ Waiting {self.download_delay}s (download rate limit)...")
            time.sleep(self.download_delay)
            
            content_uri = f"/restapi/v1.0/account/~/recording/{recording_id}/content"
            response = platform.get(content_uri)
            
            if hasattr(response, '_response'):
                content = response._response.content
            else:
                content = response.content() if hasattr(response, 'content') else None
            
            if content:
                # Save audio
                from_phone = record.get('from', {}).get('phoneNumber', 'unknown')
                to_phone = record.get('to', {}).get('phoneNumber', 'unknown')
                filename = f"rec_{recording_id}_{from_phone}_{to_phone}.mp3".replace('+', '')
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                file_size_mb = len(content) / (1024 * 1024)
                logging.info(f"✅ Downloaded: {filename} ({file_size_mb:.2f} MB)")
                
                # Transcribe with optimized delay
                transcription = ""
                if file_size_mb < 25:
                    logging.info(f"⏳ Waiting {self.transcription_delay}s (transcription rate limit)...")
                    time.sleep(self.transcription_delay)
                    
                    # Estimate audio duration
                    estimated_seconds = min(duration_seconds * 0.8, 300)  # Cap at 5 minutes
                    
                    groq_key = self.get_available_groq_key(estimated_seconds)
                    
                    if groq_key:
                        try:
                            result = transcribe_audio(filepath, groq_key)
                            transcription = result.get('text', '')
                            
                            if transcription:
                                trans_file = save_transcription(transcription, filepath)
                                logging.info(f"✅ Transcribed: {trans_file}")
                        except Exception as e:
                            logging.error(f"Transcription error: {e}")
                    else:
                        # Wait for key availability
                        wait_time = 3600  # 1 hour
                        logging.warning(f"⏳ No keys available. Waiting {wait_time/60} minutes...")
                        time.sleep(wait_time)
                        
                        # Try again
                        groq_key = self.get_available_groq_key(estimated_seconds)
                        if groq_key:
                            try:
                                result = transcribe_audio(filepath, groq_key)
                                transcription = result.get('text', '')
                                if transcription:
                                    trans_file = save_transcription(transcription, filepath)
                                    logging.info(f"✅ Transcribed after wait")
                            except Exception as e:
                                logging.error(f"Transcription error after wait: {e}")
                
                return {
                    'file': filename,
                    'transcription': transcription,
                    'size_mb': file_size_mb,
                    'from': from_phone,
                    'to': to_phone
                }
                
        except Exception as e:
            logging.error(f"Error processing recording {recording_id}: {e}")
            if "429" in str(e):
                time.sleep(300)  # Extra 5-minute wait for rate limits
        
        return None
    
    def process_daily_calls(self, date=None):
        """Main process optimized for 800 calls"""
        start_time = datetime.now()
        
        if date is None:
            date = datetime.now().date() - timedelta(days=1)
        
        logging.info(f"\n{'='*60}")
        logging.info(f"🚀 High-Volume Call Processor for {date}")
        logging.info(f"⚡ Optimized for 800+ calls/day")
        logging.info(f"🔑 Using {len(self.groq_api_keys)} Groq API keys")
        logging.info(f"{'='*60}")
        
        # Authenticate
        platform = self.authenticate()
        if not platform:
            return
        
        # Create output directory
        output_dir = f"daily_recordings/{date.strftime('%Y-%m-%d')}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Fetch all calls
        records = self.fetch_daily_calls(platform, date)
        
        # Filter recordings >= 30 seconds
        recordings_to_process = [r for r in records 
                               if r.get('recording') 
                               and r.get('duration', 0) >= 30]
        
        total_recordings = len(recordings_to_process)
        logging.info(f"🎯 Found {total_recordings} recordings >= 30 seconds")
        
        # Estimate completion
        estimated_hours = self.estimate_completion(total_recordings)
        
        if estimated_hours > 23:
            logging.warning(f"⚠️  Processing may exceed 24 hours! Consider adding more API keys.")
        
        # Process recordings
        processed = []
        
        for i, record in enumerate(recordings_to_process, 1):
            result = self.process_recording_optimized(platform, record, output_dir, i, total_recordings)
            
            if result:
                processed_record = {
                    'Index': i,
                    'Call_ID': record.get('id', ''),
                    'From': result['from'],
                    'To': result['to'],
                    'Duration': record.get('duration', 0),
                    'Start_Time': record.get('startTime', ''),
                    'Audio_File': result['file'],
                    'Transcription': result['transcription'][:200] + '...' if result['transcription'] else '',
                    'File_Size_MB': result['size_mb']
                }
                processed.append(processed_record)
                
                # Save progress every 20 recordings
                if i % 20 == 0:
                    self._save_progress(processed, output_dir, date)
                    
                    # Show time estimate
                    elapsed = (datetime.now() - start_time).total_seconds()
                    avg_time = elapsed / i
                    remaining = (total_recordings - i) * avg_time
                    eta = datetime.now() + timedelta(seconds=remaining)
                    logging.info(f"⏰ ETA: {eta.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Final save
        self._save_progress(processed, output_dir, date)
        
        # Summary
        end_time = datetime.now()
        summary = {
            'date': date.strftime('%Y-%m-%d'),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration': str(end_time - start_time),
            'total_calls': len(records),
            'recordings_found': total_recordings,
            'recordings_processed': len(processed),
            'api_keys_used': len(self.groq_api_keys),
            'settings': {
                'download_delay': self.download_delay,
                'transcription_delay': self.transcription_delay
            }
        }
        
        with open(f"{output_dir}/summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        logging.info(f"\n{'='*60}")
        logging.info(f"✅ Processing complete!")
        logging.info(f"📊 Processed {len(processed)}/{total_recordings} recordings")
        logging.info(f"⏱️  Total time: {end_time - start_time}")
        logging.info(f"{'='*60}")
        
        return summary
    
    def _save_progress(self, processed, output_dir, date):
        """Save progress to CSV"""
        if processed:
            csv_file = f"{output_dir}/processed_{date.strftime('%Y%m%d')}.csv"
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=processed[0].keys())
                writer.writeheader()
                writer.writerows(processed)
            logging.info(f"💾 Saved {len(processed)} processed recordings")

def main():
    processor = OptimizedCallProcessor800()
    processor.process_daily_calls()

if __name__ == "__main__":
    main()
