"""
Fetch RingCentral recordings and export to CSV with phone numbers and transcriptions
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

# Load environment variables
load_dotenv()

def fetch_and_export_recordings(date_str=None, min_duration=30):
    # RingCentral credentials
    config = {
        "clientId": "0gAEMMaAIb9aVRHMOSW5se",
        "clientSecret": "5TQ84XRt1eNfG90l558cie9TWqoVHQTcZfRT7zHJXZA2",
        "server": "https://platform.ringcentral.com"
    }
    
    JWT_TOKEN = os.getenv("RINGCENTRAL_JWT_TOKEN")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    
    # Initialize SDK
    sdk = SDK(config["clientId"], config["clientSecret"], config["server"])
    platform = sdk.platform()
    
    # Authenticate
    try:
        platform.login(jwt=JWT_TOKEN)
        print("✅ Successfully authenticated with RingCentral")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return []
    
    # Build query URL
    base_url = "/restapi/v1.0/account/~/call-log"
    params = []
    
    if date_str:
        params.append(f"dateFrom={date_str}")
        date = datetime.strptime(date_str, '%Y-%m-%d')
        date_to = (date + timedelta(days=1)).strftime('%Y-%m-%d')
        params.append(f"dateTo={date_to}")
        print(f"\n📅 Fetching recordings for: {date_str}")
    else:
        print("\n📅 Fetching recent recordings")
    
    params.extend([
        "perPage=1000",
        "view=Detailed",
        "recordingType=All"
    ])
    
    url = f"{base_url}?{'&'.join(params)}"
    
    print(f"⏱️  Minimum duration filter: {min_duration} seconds")
    print(f"🔍 Fetching call logs...")
    
    try:
        # Get call logs
        response = platform.get(url)
        data = response.json_dict()
        records = data.get('records', [])
        
        # Filter for recordings >= min_duration
        filtered_recordings = []
        for record in records:
            if 'recording' in record and record.get('duration', 0) >= min_duration:
                filtered_recordings.append(record)
        
        print(f"\n📊 Found {len(filtered_recordings)} recordings >= {min_duration} seconds")
        
        if not filtered_recordings:
            print("No recordings found matching criteria")
            return []
        
        # Process recordings
        Path('recordings').mkdir(exist_ok=True)
        
        # Prepare CSV file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"recordings_export_{timestamp}.csv"
        
        # CSV headers
        csv_headers = [
            'Recording_ID',
            'Date_Time',
            'Duration_Seconds',
            'Duration_Formatted',
            'From_Number',
            'From_Name',
            'To_Number',
            'To_Name',
            'Direction',
            'Extension',
            'Extension_Name',
            'Recording_Type',
            'Audio_File',
            'Transcription',
            'Transcription_File'
        ]
        
        processed_data = []
        
        print(f"\n{'='*60}")
        print(f"PROCESSING {len(filtered_recordings)} RECORDINGS")
        print(f"{'='*60}")
        
        for i, record in enumerate(filtered_recordings, 1):
            print(f"\n📞 Processing {i}/{len(filtered_recordings)}...")
            
            # Extract data
            recording_info = record.get('recording', {})
            recording_id = recording_info.get('id')
            duration = record.get('duration', 0)
            duration_formatted = f"{duration//60}:{duration%60:02d}"
            
            from_info = record.get('from', {})
            to_info = record.get('to', {})
            ext_info = record.get('extension', {})
            
            from_number = from_info.get('phoneNumber', '')
            from_name = from_info.get('name', '')
            to_number = to_info.get('phoneNumber', '')
            to_name = to_info.get('name', '')
            
            # Clean phone numbers (remove + prefix if present)
            from_number_clean = from_number.lstrip('+')
            to_number_clean = to_number.lstrip('+')
            
            row_data = {
                'Recording_ID': recording_id,
                'Date_Time': record.get('startTime', ''),
                'Duration_Seconds': duration,
                'Duration_Formatted': duration_formatted,
                'From_Number': from_number_clean,
                'From_Name': from_name,
                'To_Number': to_number_clean,
                'To_Name': to_name,
                'Direction': record.get('direction', ''),
                'Extension': ext_info.get('extensionNumber', ''),
                'Extension_Name': ext_info.get('name', ''),
                'Recording_Type': recording_info.get('type', ''),
                'Audio_File': '',
                'Transcription': '',
                'Transcription_File': ''
            }
            
            # Show progress
            print(f"   📱 From: {from_number} → To: {to_number}")
            print(f"   ⏱️  Duration: {duration_formatted}")
            
            # Download recording
            content_uri = recording_info.get('contentUri')
            if content_uri:
                try:
                    print(f"   ⬇️  Downloading...")
                    audio_response = platform.get(content_uri)
                    
                    # Get content
                    content = None
                    if hasattr(audio_response, '_response'):
                        content = audio_response._response.content
                    elif hasattr(audio_response, 'response'):
                        resp = audio_response.response()
                        content = resp.content if hasattr(resp, 'content') else resp
                    elif hasattr(audio_response, 'content'):
                        content = audio_response.content()
                    
                    if content:
                        # Save audio
                        ext_num = ext_info.get('extensionNumber', 'unknown')
                        filename = f"recording_{ext_num}_{recording_id}.mp3"
                        filepath = os.path.join('recordings', filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        
                        row_data['Audio_File'] = filename
                        print(f"   ✅ Downloaded: {filename}")
                        
                        # Transcribe
                        if GROQ_API_KEY and len(content) < 25 * 1024 * 1024:  # 25MB limit
                            try:
                                print(f"   🎤 Transcribing...")
                                result = transcribe_audio(filepath, GROQ_API_KEY)
                                transcription = result.get('text', '')
                                
                                if transcription:
                                    trans_file = save_transcription(transcription, filepath)
                                    row_data['Transcription'] = transcription.replace('\n', ' ').strip()
                                    row_data['Transcription_File'] = os.path.basename(trans_file)
                                    print(f"   ✅ Transcribed")
                            except Exception as e:
                                print(f"   ⚠️  Transcription error: {e}")
                except Exception as e:
                    print(f"   ❌ Download error: {e}")
            
            processed_data.append(row_data)
            
            # Rate limit
            if i < len(filtered_recordings) and i % 10 == 0:
                print("   ⏳ Pausing 3 seconds...")
                time.sleep(3)
        
        # Write to CSV
        print(f"\n📊 Writing to CSV file: {csv_filename}")
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_headers)
            writer.writeheader()
            writer.writerows(processed_data)
        
        # Also save as JSON for reference
        json_filename = f"recordings_data_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, indent=2, ensure_ascii=False)
        
        # Summary statistics
        print(f"\n{'='*60}")
        print(f"✅ EXPORT COMPLETE!")
        print(f"{'='*60}")
        print(f"📊 Summary:")
        print(f"   - Total recordings processed: {len(processed_data)}")
        print(f"   - CSV file: {csv_filename}")
        print(f"   - JSON backup: {json_filename}")
        print(f"   - Audio files: recordings/ folder")
        
        # Phone number statistics
        unique_from = set(r['From_Number'] for r in processed_data if r['From_Number'])
        unique_to = set(r['To_Number'] for r in processed_data if r['To_Number'])
        
        print(f"\n📱 Phone Number Statistics:")
        print(f"   - Unique 'From' numbers: {len(unique_from)}")
        print(f"   - Unique 'To' numbers: {len(unique_to)}")
        print(f"   - Total unique numbers: {len(unique_from | unique_to)}")
        
        return processed_data
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    import sys
    
    # Default: fetch recordings >= 30 seconds
    date_str = None
    min_duration = 30
    
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            min_duration = int(sys.argv[2])
        except:
            pass
    
    print("🎯 RingCentral Recording Exporter")
    print("=" * 50)
    
    if date_str:
        print(f"Date: {date_str}")
    else:
        print("Date: Recent recordings")
    
    print(f"Minimum duration: {min_duration} seconds")
    print("=" * 50)
    
    # Auto-confirm processing
    print("\n⚡ Auto-processing all recordings...")
    fetch_and_export_recordings(date_str, min_duration)
