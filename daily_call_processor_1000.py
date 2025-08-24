"""
Ultra High-Volume Daily RingCentral Call Recording Processor
Optimized for 1000+ calls in ~15 hours with 11 API keys
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
        logging.FileHandler('daily_call_processor_1000.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

class UltraHighVolumeProcessor:
    def __init__(self):
        # RingCentral credentials
        self.config = {
            "clientId": os.getenv("RC_CLIENT_ID"),
            "clientSecret": os.getenv("RC_CLIENT_SECRET"),
            "server": os.getenv("RC_SERVER_URL", "https://platform.ringcentral.com").rstrip('/')
        }
        self.jwt_token = os.getenv("RC_JWT")
        
        # Load ALL Groq API keys
        self.groq_api_keys = self._load_groq_keys()
        self.current_key_index = 0
        
        # FAST delays for 1000 recordings in 15 hours
        # 1000 recordings * 54s = 54,000s = 15 hours
        self.download_delay = 20  # 20 seconds between downloads
        self.transcription_delay = 34  # 34 seconds between transcriptions
        self.api_call_delay = 1  # 1 second between API calls
        
        # Track usage per key
        self.key_usage = {
            key: {
                'seconds_used': 0,
                'last_reset': datetime.now(),
                'calls_made': 0,
                'total_seconds_processed': 0
            } for key in self.groq_api_keys
        }
        
        # With 11 keys, we can be more aggressive
        self.max_seconds_per_key_per_hour = 6800  # Close to 7200 limit
        self.max_calls_per_key_per_hour = 80  # Higher call limit
        
        logging.info(f"🚀 ULTRA HIGH VOLUME PROCESSOR INITIALIZED")
        logging.info(f"⚡ Optimized for 1000+ calls in ~15 hours")
        logging.info(f"🔑 Using {len(self.groq_api_keys)} Groq API keys")
        logging.info(f"⏱️  Delays: {self.download_delay}s download, {self.transcription_delay}s transcription")
        
    def _load_groq_keys(self):
        """Load ALL available Groq API keys"""
        keys = []
        
        # Load up to 20 numbered keys
        for i in range(1, 21):
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                keys.append(key)
        
        # Also check single key format
        single_key = os.getenv("GROQ_API_KEY")
        if single_key and single_key not in keys:
            keys.append(single_key)
        
        logging.info(f"✅ Loaded {len(keys)} Groq API keys")
        
        if len(keys) >= 10:
            logging.info("💪 Excellent! You have enough keys for 1000+ calls!")
        
        return keys
    
    def estimate_completion(self, num_recordings):
        """Estimate completion time with 11 keys"""
        total_seconds = num_recordings * (self.download_delay + self.transcription_delay)
        hours = total_seconds / 3600
        
        # With 11 keys, calculate massive capacity
        keys_available = len(self.groq_api_keys)
        capacity_per_key_per_hour = 6800  # seconds
        total_capacity_per_hour = (capacity_per_key_per_hour * keys_available) / 60  # minutes
        
        # Assume 2 min average per recording
        audio_minutes_per_hour = (3600 / (self.download_delay + self.transcription_delay)) * 2
        
        logging.info(f"\n📊 ULTRA HIGH VOLUME PROCESSING ESTIMATE:")
        logging.info(f"├─ Recordings to process: {num_recordings}")
        logging.info(f"├─ Time per recording: {self.download_delay + self.transcription_delay}s")
        logging.info(f"├─ Total processing time: {hours:.1f} hours")
        logging.info(f"├─ API keys available: {keys_available}")
        logging.info(f"├─ Transcription capacity: {total_capacity_per_hour:.0f} minutes/hour")
        logging.info(f"└─ Required: ~{audio_minutes_per_hour:.0f} minutes/hour")
        
        if audio_minutes_per_hour > total_capacity_per_hour:
            logging.warning(f"⚠️  May be tight! Consider adding 1-2 more keys for safety.")
        else:
            margin = ((total_capacity_per_hour - audio_minutes_per_hour) / total_capacity_per_hour) * 100
            logging.info(f"✅ Excellent capacity! {margin:.0f}% safety margin")
        
        return hours
    
    def get_best_available_key(self, audio_duration_seconds):
        """Get the best available key using smart load balancing"""
        current_time = datetime.now()
        
        # Reset keys that have been idle for an hour
        for key in self.groq_api_keys:
            usage = self.key_usage[key]
            time_since_reset = (current_time - usage['last_reset']).total_seconds()
            if time_since_reset >= 3600:
                usage['seconds_used'] = 0
                usage['calls_made'] = 0
                usage['last_reset'] = current_time
        
        # Find key with most capacity
        best_key = None
        best_score = -1
        
        for i, key in enumerate(self.groq_api_keys):
            usage = self.key_usage[key]
            
            # Skip if over limits
            if (usage['seconds_used'] + audio_duration_seconds > self.max_seconds_per_key_per_hour or
                usage['calls_made'] >= self.max_calls_per_key_per_hour):
                continue
            
            # Calculate score (prefer keys with less usage)
            seconds_remaining = self.max_seconds_per_key_per_hour - usage['seconds_used']
            calls_remaining = self.max_calls_per_key_per_hour - usage['calls_made']
            score = (seconds_remaining / self.max_seconds_per_key_per_hour) * (calls_remaining / self.max_calls_per_key_per_hour)
            
            if score > best_score:
                best_score = score
                best_key = key
        
        if best_key:
            usage = self.key_usage[best_key]
            usage['seconds_used'] += audio_duration_seconds
            usage['calls_made'] += 1
            usage['total_seconds_processed'] += audio_duration_seconds
            
            key_index = self.groq_api_keys.index(best_key) + 1
            logging.debug(f"🔑 Key #{key_index}: {usage['seconds_used']}/{self.max_seconds_per_key_per_hour}s, "
                         f"{usage['calls_made']}/{self.max_calls_per_key_per_hour} calls")
            return best_key
        
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
                
                logging.info(f"  📑 Page {page}/{total_pages}: {len(records)} records")
                
                if page >= total_pages:
                    break
                
                page += 1
                time.sleep(self.api_call_delay)
                
            except Exception as e:
                logging.error(f"Error fetching page {page}: {e}")
                break
        
        logging.info(f"📞 Total calls found: {len(all_records)}")
        return all_records
    
    def process_recording_fast(self, platform, record, output_dir, index, total, start_time):
        """Process recordings with fast delays for high volume"""
        if not record.get('recording', {}).get('id'):
            return None
            
        recording_id = record['recording']['id']
        duration_seconds = record.get('duration', 0)
        
        # Calculate progress and ETA
        progress = (index / total) * 100
        elapsed = (datetime.now() - start_time).total_seconds()
        if index > 10:  # After first few for accuracy
            avg_time = elapsed / index
            remaining_time = (total - index) * avg_time
            eta = datetime.now() + timedelta(seconds=remaining_time)
            eta_str = eta.strftime('%I:%M %p')
        else:
            eta_str = "Calculating..."
        
        logging.info(f"\n[{index}/{total}] Processing {recording_id} | {progress:.1f}% | ETA: {eta_str}")
        
        try:
            # Fast download
            time.sleep(self.download_delay)
            
            content_uri = f"/restapi/v1.0/account/~/recording/{recording_id}/content"
            response = platform.get(content_uri)
            
            if hasattr(response, '_response'):
                content = response._response.content
            else:
                content = response.content() if hasattr(response, 'content') else None
            
            if content:
                # Save with phone numbers in filename
                from_phone = record.get('from', {}).get('phoneNumber', 'unknown').replace('+', '')
                to_phone = record.get('to', {}).get('phoneNumber', 'unknown').replace('+', '')
                direction = record.get('direction', 'unknown')
                
                filename = f"{index:04d}_{from_phone}_to_{to_phone}_{direction}_{recording_id}.mp3"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                file_size_mb = len(content) / (1024 * 1024)
                logging.info(f"  ✅ Downloaded: {file_size_mb:.2f} MB")
                
                # Fast transcription
                transcription = ""
                if file_size_mb < 25:
                    time.sleep(self.transcription_delay)
                    
                    # Estimate audio duration conservatively
                    estimated_seconds = min(duration_seconds * 0.8, 600)  # Cap at 10 minutes
                    
                    groq_key = self.get_best_available_key(estimated_seconds)
                    
                    if groq_key:
                        try:
                            result = transcribe_audio(filepath, groq_key)
                            transcription = result.get('text', '')
                            
                            if transcription:
                                trans_file = save_transcription(transcription, filepath)
                                key_num = self.groq_api_keys.index(groq_key) + 1
                                logging.info(f"  ✅ Transcribed with key #{key_num}")
                        except Exception as e:
                            if "rate_limit" in str(e).lower():
                                logging.warning(f"  ⚠️  Rate limit on key, rotating...")
                            else:
                                logging.error(f"  ❌ Transcription error: {str(e)[:100]}")
                    else:
                        logging.warning("  ⏳ All keys busy, will retry later")
                
                return {
                    'index': index,
                    'file': filename,
                    'transcription': transcription,
                    'size_mb': file_size_mb,
                    'from': from_phone,
                    'to': to_phone,
                    'direction': direction,
                    'duration': duration_seconds
                }
                
        except Exception as e:
            logging.error(f"❌ Error processing recording {recording_id}: {str(e)[:100]}")
            if "429" in str(e):
                time.sleep(60)  # 1 minute wait for rate limits
        
        return None
    
    def process_daily_calls(self, date=None):
        """Main process optimized for 1000+ calls in 15 hours"""
        start_time = datetime.now()
        
        if date is None:
            date = datetime.now().date() - timedelta(days=1)
        
        logging.info(f"\n{'='*70}")
        logging.info(f"🚀 ULTRA HIGH VOLUME PROCESSOR - {date}")
        logging.info(f"⚡ Target: 1000+ calls in ~15 hours")
        logging.info(f"🔑 Power: {len(self.groq_api_keys)} API keys")
        logging.info(f"{'='*70}")
        
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
        
        # Save initial call log
        all_calls_csv = f"{output_dir}/all_calls_{date.strftime('%Y%m%d')}.csv"
        if records:
            with open(all_calls_csv, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['Call_ID', 'From', 'To', 'Duration', 'Start_Time', 'Direction', 'Has_Recording']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in records:
                    writer.writerow({
                        'Call_ID': r.get('id', ''),
                        'From': r.get('from', {}).get('phoneNumber', ''),
                        'To': r.get('to', {}).get('phoneNumber', ''),
                        'Duration': r.get('duration', 0),
                        'Start_Time': r.get('startTime', ''),
                        'Direction': r.get('direction', ''),
                        'Has_Recording': 'Yes' if r.get('recording') else 'No'
                    })
        
        # Process recordings at high speed
        processed = []
        failed_indices = []
        
        logging.info(f"\n🏁 Starting high-speed processing...")
        logging.info(f"⏱️  Estimated completion: {estimated_hours:.1f} hours\n")
        
        for i, record in enumerate(recordings_to_process, 1):
            result = self.process_recording_fast(platform, record, output_dir, i, total_recordings, start_time)
            
            if result:
                processed.append(result)
                
                # Save progress every 25 recordings
                if i % 25 == 0:
                    self._save_progress(processed, output_dir, date)
                    self._show_key_stats()
            else:
                failed_indices.append(i)
        
        # Final save
        self._save_progress(processed, output_dir, date)
        
        # Retry failed recordings once
        if failed_indices:
            logging.info(f"\n🔄 Retrying {len(failed_indices)} failed recordings...")
            for idx in failed_indices[:20]:  # Retry up to 20
                if idx <= len(recordings_to_process):
                    record = recordings_to_process[idx-1]
                    result = self.process_recording_fast(platform, record, output_dir, idx, total_recordings, start_time)
                    if result:
                        processed.append(result)
        
        # Final save after retries
        self._save_progress(processed, output_dir, date)
        
        # Generate final summary
        end_time = datetime.now()
        duration = end_time - start_time
        
        summary = {
            'date': date.strftime('%Y-%m-%d'),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration': str(duration),
            'duration_hours': duration.total_seconds() / 3600,
            'total_calls': len(records),
            'recordings_found': total_recordings,
            'recordings_processed': len(processed),
            'success_rate': f"{(len(processed)/total_recordings*100):.1f}%" if total_recordings > 0 else "0%",
            'failed_count': total_recordings - len(processed),
            'api_keys_used': len(self.groq_api_keys),
            'total_audio_hours': sum(k['total_seconds_processed'] for k in self.key_usage.values()) / 3600,
            'settings': {
                'download_delay': self.download_delay,
                'transcription_delay': self.transcription_delay
            }
        }
        
        with open(f"{output_dir}/summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Show final statistics
        logging.info(f"\n{'='*70}")
        logging.info(f"✅ ULTRA HIGH VOLUME PROCESSING COMPLETE!")
        logging.info(f"{'='*70}")
        logging.info(f"📊 Final Statistics:")
        logging.info(f"├─ Total calls: {len(records)}")
        logging.info(f"├─ Recordings processed: {len(processed)}/{total_recordings}")
        logging.info(f"├─ Success rate: {(len(processed)/total_recordings*100):.1f}%")
        logging.info(f"├─ Processing time: {duration}")
        logging.info(f"├─ Average: {duration.total_seconds()/len(processed):.1f}s per recording")
        logging.info(f"└─ Audio transcribed: {summary['total_audio_hours']:.1f} hours")
        
        self._show_key_stats()
        
        logging.info(f"\n📁 Results saved to: {output_dir}")
        logging.info(f"{'='*70}")
        
        return summary
    
    def _save_progress(self, processed, output_dir, date):
        """Save progress to CSV"""
        if processed:
            csv_file = f"{output_dir}/processed_{date.strftime('%Y%m%d')}.csv"
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['Index', 'From', 'To', 'Direction', 'Duration', 'Audio_File', 
                            'Transcription_Preview', 'File_Size_MB']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for p in sorted(processed, key=lambda x: x['index']):
                    writer.writerow({
                        'Index': p['index'],
                        'From': p['from'],
                        'To': p['to'],
                        'Direction': p['direction'],
                        'Duration': p['duration'],
                        'Audio_File': p['file'],
                        'Transcription_Preview': p['transcription'][:100] + '...' if p['transcription'] else '',
                        'File_Size_MB': f"{p['size_mb']:.2f}"
                    })
    
    def _show_key_stats(self):
        """Show API key usage statistics"""
        logging.info("\n🔑 API Key Usage:")
        total_seconds = sum(k['total_seconds_processed'] for k in self.key_usage.values())
        
        for i, key in enumerate(self.groq_api_keys):
            usage = self.key_usage[key]
            pct = (usage['total_seconds_processed'] / total_seconds * 100) if total_seconds > 0 else 0
            logging.info(f"  Key #{i+1}: {usage['total_seconds_processed']/60:.0f} min processed ({pct:.0f}%)")

def main():
    processor = UltraHighVolumeProcessor()
    processor.process_daily_calls()

if __name__ == "__main__":
    main()
