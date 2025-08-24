"""
Safe Daily RingCentral Call Recording Processor
Designed to run slowly over 10-12 hours to avoid ALL rate limits
Perfect for GitHub Actions or any cloud platform
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
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_call_processor_safe.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

class SafeDailyCallProcessor:
    def __init__(self):
        # RingCentral credentials
        self.config = {
            "clientId": os.getenv("RC_CLIENT_ID"),
            "clientSecret": os.getenv("RC_CLIENT_SECRET"),
            "server": os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com").rstrip('/')
        }
        self.jwt_token = os.getenv("RC_JWT")
        
        # Multiple Groq API keys
        self.groq_api_keys = self._load_groq_keys()
        self.current_key_index = 0
        
        # SAFE Rate limiting settings
        self.download_delay = 30  # 30 seconds between downloads (120 per hour)
        self.transcription_delay = 45  # 45 seconds between transcriptions (80 per hour)
        self.api_call_delay = 2  # 2 seconds between any API calls
        
        # Track usage per key
        self.key_usage = {
            key: {
                'seconds_used': 0,
                'last_reset': datetime.now(),
                'calls_made': 0
            } for key in self.groq_api_keys
        }
        
        # Safety limits
        self.max_seconds_per_key_per_hour = 6000  # Leave 1200 second buffer (7200 limit)
        self.max_calls_per_key_per_hour = 40  # Conservative limit
        
    def _load_groq_keys(self):
        """Load multiple Groq API keys from environment"""
        keys = []
        
        # Load numbered keys
        for i in range(1, 20):  # Check up to 20 keys
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                keys.append(key)
        
        # Also check single key
        single_key = os.getenv("GROQ_API_KEY")
        if single_key and single_key not in keys:
            keys.append(single_key)
        
        logging.info(f"Loaded {len(keys)} Groq API key(s)")
        return keys
    
    def get_available_groq_key(self, audio_duration_seconds):
        """Get an available Groq API key that has capacity"""
        current_time = datetime.now()
        
        # Try each key to find one with capacity
        for _ in range(len(self.groq_api_keys)):
            key = self.groq_api_keys[self.current_key_index]
            usage = self.key_usage[key]
            
            # Check if hour has passed to reset usage
            time_since_reset = (current_time - usage['last_reset']).total_seconds()
            if time_since_reset >= 3600:  # 1 hour
                # Reset usage
                usage['seconds_used'] = 0
                usage['calls_made'] = 0
                usage['last_reset'] = current_time
                logging.info(f"Reset usage for key #{self.current_key_index + 1}")
            
            # Check if key has capacity
            if (usage['seconds_used'] + audio_duration_seconds <= self.max_seconds_per_key_per_hour and
                usage['calls_made'] < self.max_calls_per_key_per_hour):
                # Use this key
                usage['seconds_used'] += audio_duration_seconds
                usage['calls_made'] += 1
                self.current_key_index = (self.current_key_index + 1) % len(self.groq_api_keys)
                
                logging.info(f"Using key #{self.groq_api_keys.index(key) + 1}: "
                           f"{usage['seconds_used']}/{self.max_seconds_per_key_per_hour} seconds, "
                           f"{usage['calls_made']}/{self.max_calls_per_key_per_hour} calls")
                return key
            
            # Try next key
            self.current_key_index = (self.current_key_index + 1) % len(self.groq_api_keys)
        
        # No keys available - need to wait
        logging.warning("All keys at capacity. Will wait for reset...")
        return None
    
    def safe_wait(self, seconds, message="Waiting"):
        """Wait with progress logging"""
        logging.info(f"{message} for {seconds} seconds...")
        for i in range(0, seconds, 10):
            time.sleep(min(10, seconds - i))
            if i > 0 and i % 60 == 0:
                logging.info(f"  ... {i}/{seconds} seconds elapsed")
    
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
    
    def process_recording_safely(self, platform, record, output_dir):
        """Process a single recording with maximum safety"""
        if record.get('recording', {}).get('id'):
            recording_id = record['recording']['id']
            duration_seconds = record.get('duration', 0)
            
            # Estimate audio file duration (usually less than call duration)
            estimated_audio_seconds = duration_seconds * 0.8
            
            try:
                # Wait before download
                self.safe_wait(self.download_delay, "⏳ Rate limit delay before download")
                
                # Download recording
                logging.info(f"📥 Downloading recording {recording_id}")
                content_uri = f"/restapi/v1.0/account/~/recording/{recording_id}/content"
                response = platform.get(content_uri)
                
                if hasattr(response, '_response'):
                    content = response._response.content
                else:
                    content = response.content() if hasattr(response, 'content') else None
                
                if content:
                    # Save audio file
                    filename = f"recording_{recording_id}.mp3"
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    
                    file_size_mb = len(content) / (1024 * 1024)
                    logging.info(f"✅ Downloaded: {filename} ({file_size_mb:.2f} MB)")
                    
                    # Transcribe if under 25MB
                    transcription = ""
                    if file_size_mb < 25:
                        # Wait before transcription
                        self.safe_wait(self.transcription_delay, "⏳ Rate limit delay before transcription")
                        
                        # Get available key
                        groq_key = self.get_available_groq_key(estimated_audio_seconds)
                        
                        if groq_key:
                            try:
                                logging.info(f"🎤 Transcribing {filename}")
                                result = transcribe_audio(filepath, groq_key)
                                transcription = result.get('text', '')
                                
                                if transcription:
                                    trans_file = save_transcription(transcription, filepath)
                                    logging.info(f"✅ Transcribed: {trans_file}")
                                
                            except Exception as e:
                                logging.error(f"❌ Transcription error: {e}")
                        else:
                            # Need to wait for key availability
                            wait_time = 3600  # Wait 1 hour for reset
                            self.safe_wait(wait_time, "⏳ Waiting for API key reset")
                            
                            # Try again after wait
                            groq_key = self.get_available_groq_key(estimated_audio_seconds)
                            if groq_key:
                                try:
                                    result = transcribe_audio(filepath, groq_key)
                                    transcription = result.get('text', '')
                                    if transcription:
                                        trans_file = save_transcription(transcription, filepath)
                                        logging.info(f"✅ Transcribed after wait: {trans_file}")
                                except Exception as e:
                                    logging.error(f"❌ Transcription error after wait: {e}")
                    
                    return {
                        'file': filename,
                        'transcription': transcription,
                        'size_mb': file_size_mb
                    }
                    
            except Exception as e:
                logging.error(f"❌ Error processing recording {recording_id}: {e}")
                if "429" in str(e):
                    # Extra wait for rate limits
                    self.safe_wait(300, "⏳ Hit rate limit, extra wait")
        
        return None
    
    def process_daily_calls(self, date=None):
        """Main process to run daily - SAFE VERSION"""
        start_time = datetime.now()
        
        if date is None:
            date = datetime.now().date() - timedelta(days=1)
        
        logging.info(f"\n{'='*60}")
        logging.info(f"🚀 Starting SAFE daily call processing for {date}")
        logging.info(f"⏰ This will take 10-12 hours to complete safely")
        logging.info(f"🔑 Using {len(self.groq_api_keys)} Groq API key(s)")
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
        
        # Extract and save call details
        detailed_records = []
        for record in records:
            detail = {
                'Call_ID': record.get('id', ''),
                'From': record.get('from', {}).get('phoneNumber', ''),
                'To': record.get('to', {}).get('phoneNumber', ''),
                'Duration': record.get('duration', 0),
                'Start_Time': record.get('startTime', ''),
                'Direction': record.get('direction', ''),
                'Type': record.get('type', ''),
                'Has_Recording': 'Yes' if record.get('recording') else 'No'
            }
            detailed_records.append(detail)
        
        # Save call log
        csv_filename = f"{output_dir}/call_log_{date.strftime('%Y%m%d')}.csv"
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            if detailed_records:
                writer = csv.DictWriter(f, fieldnames=detailed_records[0].keys())
                writer.writeheader()
                writer.writerows(detailed_records)
        
        logging.info(f"📊 Call log saved: {csv_filename}")
        
        # Filter recordings to process
        recordings_to_process = [r for r in records 
                               if r.get('recording') 
                               and r.get('duration', 0) >= 30]
        
        total_recordings = len(recordings_to_process)
        logging.info(f"🎯 Found {total_recordings} recordings >= 30 seconds")
        
        # Estimate completion time
        estimated_hours = (total_recordings * (self.download_delay + self.transcription_delay)) / 3600
        logging.info(f"⏱️ Estimated completion time: {estimated_hours:.1f} hours")
        
        # Process recordings SAFELY
        processed_recordings = []
        failed_recordings = []
        
        for i, record in enumerate(recordings_to_process, 1):
            logging.info(f"\n📍 Processing {i}/{total_recordings} "
                        f"({(i/total_recordings)*100:.1f}% complete)")
            
            # Show time elapsed and remaining
            elapsed = datetime.now() - start_time
            if i > 1:
                avg_time_per_recording = elapsed.total_seconds() / (i - 1)
                remaining_recordings = total_recordings - i + 1
                estimated_remaining = timedelta(seconds=avg_time_per_recording * remaining_recordings)
                logging.info(f"⏰ Elapsed: {elapsed} | Estimated remaining: {estimated_remaining}")
            
            result = self.process_recording_safely(platform, record, output_dir)
            
            if result:
                # Add to processed list
                processed_record = {
                    'Call_ID': record.get('id', ''),
                    'From': record.get('from', {}).get('phoneNumber', ''),
                    'To': record.get('to', {}).get('phoneNumber', ''),
                    'Duration': record.get('duration', 0),
                    'Audio_File': result['file'],
                    'Transcription': result['transcription'][:500] if result['transcription'] else '',
                    'File_Size_MB': result['size_mb']
                }
                processed_recordings.append(processed_record)
                
                # Save progress every 10 recordings
                if i % 10 == 0:
                    self._save_progress(processed_recordings, output_dir, date)
            else:
                failed_recordings.append(record.get('id', ''))
        
        # Final save
        self._save_progress(processed_recordings, output_dir, date)
        
        # Generate summary
        end_time = datetime.now()
        summary = {
            'date': date.strftime('%Y-%m-%d'),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'total_duration': str(end_time - start_time),
            'total_calls': len(records),
            'calls_with_recordings': len(recordings_to_process),
            'successfully_processed': len(processed_recordings),
            'failed': len(failed_recordings),
            'api_keys_used': len(self.groq_api_keys)
        }
        
        summary_file = f"{output_dir}/summary_{date.strftime('%Y%m%d')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logging.info(f"\n{'='*60}")
        logging.info(f"✅ SAFE processing complete!")
        logging.info(f"📊 Summary: {json.dumps(summary, indent=2)}")
        logging.info(f"{'='*60}")
        
        return summary
    
    def _save_progress(self, processed_recordings, output_dir, date):
        """Save progress to CSV"""
        if processed_recordings:
            progress_file = f"{output_dir}/processed_recordings_{date.strftime('%Y%m%d')}.csv"
            with open(progress_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=processed_recordings[0].keys())
                writer.writeheader()
                writer.writerows(processed_recordings)
            logging.info(f"💾 Progress saved: {len(processed_recordings)} recordings")

def main():
    processor = SafeDailyCallProcessor()
    
    # Process yesterday's calls by default
    processor.process_daily_calls()

if __name__ == "__main__":
    main()
