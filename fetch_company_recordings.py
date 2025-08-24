"""
Fetch RingCentral recordings from company-wide call logs
This uses the account-level endpoint instead of extension-level
"""

import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from ringcentral import SDK
from transcribe_audio import transcribe_audio, save_transcription
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def fetch_company_recordings(date_str=None, min_duration=15):
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
        print("✅ Using company-wide call log endpoint")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return []
    
    # Build query URL - USING COMPANY ENDPOINT (no /extension/~)
    base_url = "/restapi/v1.0/account/~/call-log"  # Company-wide endpoint
    params = []
    
    if date_str:
        try:
            # Simple date format works fine
            params.append(f"dateFrom={date_str}")
            # Add one day for date range
            date = datetime.strptime(date_str, '%Y-%m-%d')
            date_to = (date + timedelta(days=1)).strftime('%Y-%m-%d')
            params.append(f"dateTo={date_to}")
            
            print(f"\n📅 Fetching recordings for: {date_str}")
        except Exception as e:
            print(f"⚠️  Invalid date format: {date_str}")
            date_str = None
    
    if not date_str:
        print("\n📅 Fetching recent recordings")
    
    # Add other parameters
    params.extend([
        "perPage=1000",  # Get more records
        "view=Detailed",
        "recordingType=All"  # Ensure we get recordings
    ])
    
    # Build final URL
    url = f"{base_url}?{'&'.join(params)}"
    
    print(f"⏱️  Minimum duration filter: {min_duration} seconds")
    print(f"\n🔍 Querying company-wide call logs...")
    
    try:
        # Get call logs
        response = platform.get(url)
        data = response.json_dict()
        
        records = data.get('records', [])
        total_count = data.get('paging', {}).get('totalElements', len(records))
        
        print(f"\n📊 Response summary:")
        print(f"   Total records in system: {total_count}")
        print(f"   Records returned: {len(records)}")
        
        # Filter for recordings
        all_recordings = []
        filtered_recordings = []
        
        for record in records:
            if 'recording' in record:
                all_recordings.append(record)
                if record.get('duration', 0) >= min_duration:
                    filtered_recordings.append(record)
        
        print(f"\n🎙️ Recording summary:")
        print(f"   Total calls with recordings: {len(all_recordings)}")
        print(f"   Recordings >= {min_duration} seconds: {len(filtered_recordings)}")
        
        if all_recordings and not filtered_recordings:
            print(f"\n📌 Recording durations (showing first 10):")
            for r in all_recordings[:10]:
                dur = r.get('duration', 0)
                to_num = r.get('to', {}).get('phoneNumber', 'Unknown')
                ext = r.get('extension', {}).get('extensionNumber', 'Unknown')
                print(f"   - {dur}s to {to_num} (Ext: {ext})")
        
        if filtered_recordings:
            print(f"\n📞 Found {len(filtered_recordings)} recordings to process:")
            
            # Group by extension
            by_extension = {}
            for record in filtered_recordings:
                ext_info = record.get('extension', {})
                ext_num = ext_info.get('extensionNumber', 'Unknown')
                ext_name = ext_info.get('name', 'Unknown')
                ext_key = f"{ext_num} - {ext_name}"
                
                if ext_key not in by_extension:
                    by_extension[ext_key] = []
                by_extension[ext_key].append(record)
            
            # Show summary by extension
            print("\n📊 Recordings by extension:")
            for ext_key, ext_records in by_extension.items():
                print(f"   {ext_key}: {len(ext_records)} recordings")
            
            # Show first 10 recordings
            print(f"\n📋 First {min(10, len(filtered_recordings))} recordings:")
            for i, record in enumerate(filtered_recordings[:10], 1):
                duration = record.get('duration', 0)
                to_num = record.get('to', {}).get('phoneNumber', 'Unknown')
                from_num = record.get('from', {}).get('phoneNumber', 'Unknown')
                start_time = record.get('startTime', 'Unknown')
                recording_type = record.get('recording', {}).get('type', 'Unknown')
                ext_info = record.get('extension', {})
                ext = f"{ext_info.get('extensionNumber', '?')} - {ext_info.get('name', 'Unknown')}"
                
                print(f"\n   {i}. {start_time}")
                print(f"      Extension: {ext}")
                print(f"      Duration: {duration//60}:{duration%60:02d} ({duration}s)")
                print(f"      From: {from_num} → To: {to_num}")
                print(f"      Recording Type: {recording_type}")
            
            if len(filtered_recordings) > 10:
                print(f"\n   ... and {len(filtered_recordings) - 10} more recordings")
            
            # Ask to process
            process = input(f"\n❓ Download and transcribe these {len(filtered_recordings)} recordings? (y/n): ")
            
            if process.lower() == 'y':
                return process_recordings(platform, filtered_recordings, GROQ_API_KEY)
        
        return []
        
    except Exception as e:
        print(f"\n❌ Error fetching call logs: {e}")
        import traceback
        traceback.print_exc()
        return []

def process_recordings(platform, recordings, groq_api_key):
    """Download and transcribe recordings"""
    
    # Create recordings directory
    Path('recordings').mkdir(exist_ok=True)
    
    processed = []
    errors = []
    
    print(f"\n{'='*60}")
    print(f"PROCESSING {len(recordings)} RECORDINGS")
    print(f"{'='*60}")
    
    for i, record in enumerate(recordings, 1):
        print(f"\n📞 Recording {i}/{len(recordings)}")
        print(f"{'─'*40}")
        
        # Extract info
        recording_info = record.get('recording', {})
        duration = record.get('duration', 0)
        from_info = record.get('from', {})
        to_info = record.get('to', {})
        ext_info = record.get('extension', {})
        
        # Display info
        print(f"   Extension: {ext_info.get('extensionNumber', '?')} - {ext_info.get('name', 'Unknown')}")
        print(f"   Time: {record.get('startTime', 'Unknown')}")
        print(f"   Duration: {duration//60}:{duration%60:02d} ({duration}s)")
        print(f"   Direction: {record.get('direction', 'Unknown')}")
        print(f"   From: {from_info.get('phoneNumber', 'Unknown')} ({from_info.get('name', 'Unknown')})")
        print(f"   To: {to_info.get('phoneNumber', 'Unknown')} ({to_info.get('name', 'Unknown')})")
        print(f"   Recording Type: {recording_info.get('type', 'Unknown')}")
        
        # Download recording
        recording_id = recording_info.get('id')
        content_uri = recording_info.get('contentUri')
        
        if not content_uri:
            print("   ❌ No content URI - skipping")
            continue
        
        try:
            print(f"   ⬇️  Downloading recording...")
            
            # Download the recording
            audio_response = platform.get(content_uri)
            
            # Create filename with extension info
            ext_num = ext_info.get('extensionNumber', 'unknown')
            filename = f"recording_{ext_num}_{recording_id}.mp3"
            filepath = os.path.join('recordings', filename)
            
            # Get content from response
            content = None
            if hasattr(audio_response, '_response'):
                content = audio_response._response.content
            elif hasattr(audio_response, 'response'):
                content = audio_response.response()
                if hasattr(content, 'content'):
                    content = content.content
                else:
                    content = content
            elif hasattr(audio_response, 'content'):
                content = audio_response.content()
            
            if content:
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                file_size_mb = len(content) / 1024 / 1024
                print(f"   ✅ Downloaded: {filename} ({file_size_mb:.2f} MB)")
                
                # Transcribe
                if groq_api_key and file_size_mb < 25:  # Groq limit is 25MB
                    try:
                        print(f"   🎤 Transcribing with Groq Whisper...")
                        result = transcribe_audio(filepath, groq_api_key)
                        transcription = result.get('text', '')
                        
                        if transcription:
                            # Save transcription
                            trans_file = save_transcription(transcription, filepath)
                            print(f"   ✅ Transcribed successfully!")
                            
                            # Show preview
                            preview = transcription[:200].replace('\n', ' ')
                            if len(transcription) > 200:
                                preview += "..."
                            print(f"   📝 Preview: {preview}")
                            
                            # Add to processed list
                            processed.append({
                                'id': recording_id,
                                'extension': ext_info.get('extensionNumber'),
                                'extension_name': ext_info.get('name'),
                                'duration': duration,
                                'from': from_info.get('phoneNumber'),
                                'from_name': from_info.get('name'),
                                'to': to_info.get('phoneNumber'),
                                'to_name': to_info.get('name'),
                                'direction': record.get('direction'),
                                'time': record.get('startTime'),
                                'type': recording_info.get('type'),
                                'file': filepath,
                                'file_size_mb': file_size_mb,
                                'transcription_file': trans_file,
                                'transcription': transcription
                            })
                        else:
                            print("   ⚠️  No transcription text returned")
                    except Exception as e:
                        print(f"   ⚠️  Transcription error: {e}")
                        processed.append({
                            'id': recording_id,
                            'extension': ext_info.get('extensionNumber'),
                            'file': filepath,
                            'file_size_mb': file_size_mb,
                            'transcription_error': str(e)
                        })
                elif file_size_mb >= 25:
                    print(f"   ⚠️  File too large for Groq ({file_size_mb:.2f} MB > 25 MB limit)")
                    processed.append({
                        'id': recording_id,
                        'extension': ext_info.get('extensionNumber'),
                        'file': filepath,
                        'file_size_mb': file_size_mb,
                        'transcription_error': 'File too large for Groq API'
                    })
                else:
                    # No API key
                    processed.append({
                        'id': recording_id,
                        'extension': ext_info.get('extensionNumber'),
                        'file': filepath,
                        'file_size_mb': file_size_mb
                    })
            else:
                print("   ❌ Could not extract content from response")
                errors.append({
                    'recording_id': recording_id,
                    'error': 'No content in response'
                })
                
        except Exception as e:
            print(f"   ❌ Download error: {e}")
            errors.append({
                'recording_id': recording_id,
                'error': str(e)
            })
        
        # Rate limit pause
        if i < len(recordings):
            print("   ⏳ Pausing 2 seconds (rate limit)...")
            time.sleep(2)
    
    # Save summary
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_file = f"recordings_summary_{timestamp}.json"
    
    summary_data = {
        'timestamp': timestamp,
        'total_recordings': len(recordings),
        'successfully_processed': len(processed),
        'errors': len(errors),
        'processed_recordings': processed,
        'error_details': errors
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"✅ PROCESSING COMPLETE!")
    print(f"{'='*60}")
    print(f"📊 Results:")
    print(f"   - Total recordings: {len(recordings)}")
    print(f"   - Successfully processed: {len(processed)}")
    print(f"   - Errors: {len(errors)}")
    print(f"\n📄 Summary saved to: {summary_file}")
    print(f"📁 Audio files saved to: recordings/")
    print(f"📝 Transcriptions saved to: recordings/")
    
    return processed

if __name__ == "__main__":
    import sys
    
    # Parse command line arguments
    date_str = None
    min_duration = 30
    
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            min_duration = int(sys.argv[2])
        except:
            pass
    
    # Show usage if no arguments
    if not date_str:
        print("\n📖 Usage:")
        print("   python fetch_company_recordings.py                    # Fetch recent recordings")
        print("   python fetch_company_recordings.py 2025-08-12        # Fetch specific date")
        print("   python fetch_company_recordings.py 2025-08-12 15     # With custom duration filter")
        print("")
    
    fetch_company_recordings(date_str, min_duration)
