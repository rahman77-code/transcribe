"""
Daily RingCentral Call Recording Processor with Multiple API Key Support
Rotates between multiple Groq API keys to avoid rate limits
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
import schedule
import logging
import random

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_call_processor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

class DailyCallProcessorMultiKey:
    def __init__(self):
        # New RingCentral credentials
        self.config = {
            "clientId": os.getenv("RC_CLIENT_ID", "VNKRmCCWukXcPadmaLZoMu"),
            "clientSecret": os.getenv("RC_CLIENT_SECRET", "37zo0FbARv5fcHIDHyh9485r2EA57ulqTdo1znecBZwQ"),
            "server": os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com").rstrip('/')
        }
        self.jwt_token = os.getenv("RC_JWT")
        self.hubspot_token = os.getenv("HUBSPOT_ACCESS_TOKEN")
        
        # Multiple Groq API keys
        self.groq_api_keys = self._load_groq_keys()
        self.current_key_index = 0
        self.key_usage = {key: {'count': 0, 'last_error': None} for key in self.groq_api_keys}
        
        # Rate limiting settings
        self.download_delay = 5  # seconds between downloads
        self.max_retries = 3
        self.retry_delay = 30  # seconds
        
    def _load_groq_keys(self):
        """Load multiple Groq API keys from environment"""
        keys = []
        
        # Try to load multiple keys: GROQ_API_KEY_1, GROQ_API_KEY_2, etc.
        i = 1
        while True:
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                keys.append(key)
                i += 1
            else:
                break
        
        # Also check for the single key format
        single_key = os.getenv("GROQ_API_KEY")
        if single_key and single_key not in keys:
            keys.append(single_key)
        
        # Also check for comma-separated keys
        csv_keys = os.getenv("GROQ_API_KEYS", "")
        if csv_keys:
            for key in csv_keys.split(','):
                key = key.strip()
                if key and key not in keys:
                    keys.append(key)
        
        logging.info(f"Loaded {len(keys)} Groq API key(s)")
        return keys
    
    def get_next_groq_key(self):
        """Get the next available Groq API key"""
        if not self.groq_api_keys:
            return None
        
        # Try each key in rotation
        attempts = 0
        while attempts < len(self.groq_api_keys):
            key = self.groq_api_keys[self.current_key_index]
            
            # Check if this key recently had a rate limit error
            key_info = self.key_usage[key]
            if key_info['last_error']:
                # Check if enough time has passed (1 hour for rate limits)
                time_since_error = datetime.now() - key_info['last_error']
                if time_since_error.total_seconds() < 3600:
                    # Try next key
                    self.current_key_index = (self.current_key_index + 1) % len(self.groq_api_keys)
                    attempts += 1
                    continue
                else:
                    # Reset error status
                    key_info['last_error'] = None
            
            # Use this key
            key_info['count'] += 1
            self.current_key_index = (self.current_key_index + 1) % len(self.groq_api_keys)
            return key
        
        # All keys are rate limited
        logging.warning("All Groq API keys are currently rate limited")
        return None
    
    def mark_key_error(self, key, error):
        """Mark a key as having an error"""
        if key in self.key_usage:
            if 'rate_limit' in str(error).lower():
                self.key_usage[key]['last_error'] = datetime.now()
                logging.warning(f"Rate limit hit for key ending in ...{key[-6:]}")
    
    def authenticate(self):
        """Authenticate with RingCentral"""
        try:
            sdk = SDK(self.config["clientId"], self.config["clientSecret"], self.config["server"])
            platform = sdk.platform()
            platform.login(jwt=self.jwt_token)
            logging.info("Successfully authenticated with RingCentral")
            return platform
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            return None
    
    def fetch_daily_calls(self, platform, date=None):
        """Fetch all calls for a specific date"""
        if date is None:
            date = datetime.now().date()
        
        # Convert date to string
        date_str = date.strftime('%Y-%m-%d')
        date_from = f"{date_str}T00:00:00.000Z"
        date_to = f"{(date + timedelta(days=1)).strftime('%Y-%m-%d')}T00:00:00.000Z"
        
        logging.info(f"Fetching calls for: {date_str}")
        
        all_records = []
        page = 1
        per_page = 1000
        
        while True:
            try:
                # Fetch call logs with all details
                url = (f"/restapi/v1.0/account/~/call-log?"
                       f"dateFrom={date_from}&dateTo={date_to}"
                       f"&page={page}&perPage={per_page}"
                       f"&view=Detailed")
                
                response = platform.get(url)
                data = response.json_dict()
                
                records = data.get('records', [])
                all_records.extend(records)
                
                # Check if there are more pages
                paging = data.get('paging', {})
                total_pages = paging.get('totalPages', 1)
                
                if page >= total_pages:
                    break
                    
                page += 1
                time.sleep(1)  # Avoid rate limiting
                
            except Exception as e:
                logging.error(f"Error fetching page {page}: {e}")
                break
        
        logging.info(f"Total calls found: {len(all_records)}")
        return all_records
    
    def extract_call_details(self, records):
        """Extract all required fields from call records"""
        detailed_records = []
        
        for record in records:
            # Extract all fields as requested
            from_info = record.get('from', {})
            to_info = record.get('to', {})
            extension_info = record.get('extension', {})
            legs = record.get('legs', [])
            
            # Get forwarded to info from legs if available
            forwarded_to = ""
            if legs:
                for leg in legs:
                    if leg.get('legType') == 'Forward':
                        forwarded_to = leg.get('to', {}).get('phoneNumber', '')
                        break
            
            # Format duration
            duration = record.get('duration', 0)
            duration_formatted = f"{duration//60}:{duration%60:02d}"
            
            # Extract billing info
            billing = record.get('billing', {})
            cost = billing.get('costIncluded', 0.0)
            cost_purchased = billing.get('costPurchased', 0.0)
            
            # Check if has recording
            has_recording = 'recording' in record
            recording_info = record.get('recording', {})
            
            detail = {
                'Type': record.get('type', ''),
                'From': from_info.get('phoneNumber', ''),
                'From_Name': from_info.get('name', ''),
                'To': to_info.get('phoneNumber', ''),
                'To_Name': to_info.get('name', ''),
                'Ext': extension_info.get('extensionNumber', ''),
                'Ext_Name': extension_info.get('name', ''),
                'Forwarded_To': forwarded_to,
                'Date_Time': record.get('startTime', ''),
                'Has_Recording': 'Yes' if has_recording else 'No',
                'Recording_ID': recording_info.get('id', '') if has_recording else '',
                'Recording_Type': recording_info.get('type', '') if has_recording else '',
                'Action': record.get('action', ''),
                'Result': record.get('result', ''),
                'Length': duration_formatted,
                'Duration_Seconds': duration,
                'Included': f"${cost:.3f}",
                'Purchased': f"${cost_purchased:.3f}",
                'Direction': record.get('direction', ''),
                'Session_ID': record.get('sessionId', ''),
                'Call_ID': record.get('id', '')
            }
            
            detailed_records.append(detail)
        
        return detailed_records
    
    def download_and_transcribe_recording(self, platform, record, output_dir):
        """Download and transcribe a single recording with retry logic"""
        if record['Has_Recording'] != 'Yes':
            return None
        
        recording_id = record['Recording_ID']
        if not recording_id:
            return None
        
        # Construct content URI
        content_uri = f"/restapi/v1.0/account/~/recording/{recording_id}/content"
        
        for attempt in range(self.max_retries):
            try:
                logging.info(f"Downloading recording {recording_id} (attempt {attempt + 1})")
                
                # Download recording
                response = platform.get(content_uri)
                
                # Get content
                if hasattr(response, '_response'):
                    content = response._response.content
                else:
                    content = response.content() if hasattr(response, 'content') else None
                
                if content:
                    # Save audio file
                    ext_num = record['Ext'] or 'unknown'
                    filename = f"recording_{ext_num}_{recording_id}.mp3"
                    filepath = os.path.join(output_dir, filename)
                    
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    
                    logging.info(f"Downloaded: {filename}")
                    
                    # Transcribe with key rotation
                    transcription = ""
                    if len(content) < 25 * 1024 * 1024:  # 25MB limit
                        groq_key = self.get_next_groq_key()
                        if groq_key:
                            try:
                                result = transcribe_audio(filepath, groq_key)
                                transcription = result.get('text', '')
                                if transcription:
                                    trans_file = save_transcription(transcription, filepath)
                                    logging.info(f"Transcribed: {trans_file} (Key #{self.groq_api_keys.index(groq_key) + 1})")
                            except Exception as e:
                                logging.error(f"Transcription error: {e}")
                                self.mark_key_error(groq_key, e)
                                # Try with next key
                                groq_key = self.get_next_groq_key()
                                if groq_key:
                                    try:
                                        result = transcribe_audio(filepath, groq_key)
                                        transcription = result.get('text', '')
                                        if transcription:
                                            trans_file = save_transcription(transcription, filepath)
                                            logging.info(f"Transcribed on retry: {trans_file}")
                                    except Exception as e2:
                                        logging.error(f"Transcription retry failed: {e2}")
                                        self.mark_key_error(groq_key, e2)
                    
                    return {
                        'file': filename,
                        'transcription': transcription,
                        'size_mb': len(content) / (1024 * 1024)
                    }
                
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    logging.warning(f"Rate limit hit, waiting {self.retry_delay}s...")
                    time.sleep(self.retry_delay)
                else:
                    logging.error(f"Download error: {e}")
                    
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        return None
    
    def process_daily_calls(self, date=None):
        """Main process to run daily"""
        start_time = datetime.now()
        
        if date is None:
            date = datetime.now().date() - timedelta(days=1)  # Process yesterday by default
        
        logging.info(f"\n{'='*60}")
        logging.info(f"Starting daily call processing for {date}")
        logging.info(f"Using {len(self.groq_api_keys)} Groq API key(s)")
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
        
        # Extract detailed information
        detailed_records = self.extract_call_details(records)
        
        # Save call log CSV
        csv_filename = f"{output_dir}/call_log_{date.strftime('%Y%m%d')}.csv"
        with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
            if detailed_records:
                fieldnames = list(detailed_records[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(detailed_records)
        
        logging.info(f"Call log saved: {csv_filename}")
        
        # Filter recordings to download
        recordings_to_process = [r for r in detailed_records 
                               if r['Has_Recording'] == 'Yes' 
                               and r['Duration_Seconds'] >= 30]
        
        logging.info(f"Found {len(recordings_to_process)} recordings >= 30 seconds")
        
        # Process recordings with rate limiting
        processed_recordings = []
        for i, record in enumerate(recordings_to_process, 1):
            logging.info(f"\nProcessing {i}/{len(recordings_to_process)}")
            
            result = self.download_and_transcribe_recording(platform, record, output_dir)
            
            if result:
                record['Audio_File'] = result['file']
                record['Transcription'] = result['transcription']
                record['File_Size_MB'] = result['size_mb']
                processed_recordings.append(record)
            
            # Rate limiting
            if i < len(recordings_to_process):
                time.sleep(self.download_delay)
        
        # Save processed recordings with transcriptions
        if processed_recordings:
            processed_filename = f"{output_dir}/processed_recordings_{date.strftime('%Y%m%d')}.csv"
            with open(processed_filename, 'w', newline='', encoding='utf-8') as f:
                fieldnames = list(processed_recordings[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(processed_recordings)
            
            logging.info(f"Processed recordings saved: {processed_filename}")
        
        # Log key usage statistics
        logging.info("\nAPI Key Usage Statistics:")
        for i, key in enumerate(self.groq_api_keys):
            usage = self.key_usage[key]
            status = "Rate Limited" if usage['last_error'] else "Active"
            logging.info(f"  Key #{i+1}: {usage['count']} uses - {status}")
        
        # Generate summary
        summary = {
            'date': date.strftime('%Y-%m-%d'),
            'total_calls': len(detailed_records),
            'calls_with_recordings': sum(1 for r in detailed_records if r['Has_Recording'] == 'Yes'),
            'recordings_processed': len(processed_recordings),
            'processing_time': str(datetime.now() - start_time),
            'api_keys_used': len(self.groq_api_keys),
            'key_usage': {f"key_{i+1}": self.key_usage[key]['count'] for i, key in enumerate(self.groq_api_keys)},
            'timestamp': datetime.now().isoformat()
        }
        
        summary_file = f"{output_dir}/summary_{date.strftime('%Y%m%d')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logging.info(f"\nDaily processing complete!")
        logging.info(f"Summary: {summary}")
        
        # Optional: Send to HubSpot
        if self.hubspot_token:
            self.send_to_hubspot(processed_recordings)
        
        return summary
    
    def send_to_hubspot(self, records):
        """Send call data to HubSpot (placeholder for integration)"""
        logging.info(f"Would send {len(records)} records to HubSpot")
    
    def run_scheduled(self):
        """Run on schedule"""
        # Run daily at 2 AM (to process previous day's calls)
        schedule.every().day.at("02:00").do(self.process_daily_calls)
        
        logging.info("Scheduler started. Will run daily at 02:00 AM")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

def main():
    processor = DailyCallProcessorMultiKey()
    
    # For testing, process yesterday
    # processor.process_daily_calls()
    
    # Run on schedule
    processor.run_scheduled()

if __name__ == "__main__":
    main()
