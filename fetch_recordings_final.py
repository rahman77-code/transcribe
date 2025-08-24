"""
Fetch RingCentral recordings with all permissions enabled
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

def fetch_recordings_with_all_permissions(date_str=None, min_duration=15):
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
        print("✅ All permissions should now be enabled!")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("\n💡 If authentication fails, you may need to generate a new JWT token")
        print("   after adding the new permissions.")
        return []
    
    # Build query URL
    base_url = "/restapi/v1.0/account/~/extension/~/call-log"
    params = []
    
    if date_str:
        try:
            # Parse date - handle both past and future dates
            date = datetime.strptime(date_str, '%Y-%m-%d')
            
            # For Central Time (Chicago timezone)
            # August is CDT (UTC-5)
            utc_offset = 5
            
            # Convert local midnight to UTC
            date_from_utc = date + timedelta(hours=utc_offset)
            date_to_utc = date + timedelta(days=1, hours=utc_offset)
            
            date_from = date_from_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            date_to = date_to_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            params.append(f"dateFrom={date_from}")
            params.append(f"dateTo={date_to}")
            
            print(f"\n📅 Fetching recordings for: {date_str}")
            print(f"   Central Time: {date.strftime('%Y-%m-%d')} 00:00 to 23:59")
            print(f"   UTC Time: {date_from} to {date_to}")
        except Exception as e:
            print(f"⚠️  Invalid date format: {date_str}")
            print(f"   Error: {e}")
            date_str = None
    
    if not date_str:
        print("\n📅 Fetching recent recordings (last 90 days)")
    
    # Add other parameters
    params.extend([
        "perPage=100",
        "view=Detailed"
    ])
    
    # Build final URL
    url = f"{base_url}?{'&'.join(params)}" if params else base_url
    
    print(f"⏱️  Minimum duration filter: {min_duration} seconds")
    print(f"\n🔍 Querying: {url}")
    
    try:
        # Get call logs
        response = platform.get(url)
        data = response.json_dict()
        
        # Debug: show what we got
        if 'error' in data:
            print(f"❌ API Error: {data}")
            return []
        
        records = data.get('records', [])
        total_count = data.get('paging', {}).get('totalElements', len(records))
        
        print(f"\n📊 Response summary:")
        print(f"   Total records in system: {total_count}")
        print(f"   Records returned: {len(records)}")
        
        if records:
            # Show date range of returned records
            dates = [r.get('startTime', '') for r in records if r.get('startTime')]
            if dates:
                dates.sort()
                print(f"   Date range: {dates[0]} to {dates[-1]}")
        
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
            print(f"\n📌 All recording durations:")
            for r in all_recordings[:10]:
                dur = r.get('duration', 0)
                to_num = r.get('to', {}).get('phoneNumber', 'Unknown')
                print(f"   - {dur}s to {to_num}")
        
        if filtered_recordings:
            print(f"\n📞 Recordings to process:")
            for i, record in enumerate(filtered_recordings[:10], 1):
                duration = record.get('duration', 0)
                to_num = record.get('to', {}).get('phoneNumber', 'Unknown')
                from_num = record.get('from', {}).get('phoneNumber', 'Unknown')
                start_time = record.get('startTime', 'Unknown')
                recording_type = record.get('recording', {}).get('type', 'Unknown')
                
                print(f"\n   {i}. {start_time}")
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
        
        # More detailed error info
        if hasattr(e, 'response'):
            print(f"   Response status: {e.response.status_code}")
            print(f"   Response body: {e.response.text[:500]}")
        
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
        
        # Display info
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
            
            # The content URI might be on media.ringcentral.com
            # The SDK should handle this automatically
            audio_response = platform.get(content_uri)
            
            # Save audio file
            filename = f"recording_{recording_id}.mp3"
            filepath = os.path.join('recordings', filename)
            
            # Get content from response - try different methods
            content = None
            if hasattr(audio_response, '_response'):
                content = audio_response._response.content
            elif hasattr(audio_response, 'response'):
                content = audio_response.response.content
            elif hasattr(audio_response, 'body'):
                content = audio_response.body
            elif hasattr(audio_response, 'content'):
                content = audio_response.content
            elif hasattr(audio_response, '_content'):
                content = audio_response._content
            
            if content:
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                file_size_mb = len(content) / 1024 / 1024
                print(f"   ✅ Downloaded: {filename} ({file_size_mb:.2f} MB)")
                
                # Transcribe
                if groq_api_key:
                    try:
                        print(f"   🎤 Transcribing with Groq Whisper...")
                        result = transcribe_audio(filepath, groq_api_key)
                        transcription = result.get('text', '')
                        
                        if transcription:
                            # Save transcription
                            trans_file = save_transcription(transcription, filepath)
                            print(f"   ✅ Transcribed successfully!")
                            
                            # Show preview
                            preview = transcription[:200]
                            if len(transcription) > 200:
                                preview += "..."
                            print(f"   📝 Preview: {preview}")
                            
                            # Add to processed list
                            processed.append({
                                'id': recording_id,
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
                            processed.append({
                                'id': recording_id,
                                'duration': duration,
                                'from': from_info.get('phoneNumber'),
                                'to': to_info.get('phoneNumber'),
                                'time': record.get('startTime'),
                                'file': filepath,
                                'file_size_mb': file_size_mb,
                                'transcription_error': 'No text returned'
                            })
                    except Exception as e:
                        print(f"   ⚠️  Transcription error: {e}")
                        processed.append({
                            'id': recording_id,
                            'duration': duration,
                            'from': from_info.get('phoneNumber'),
                            'to': to_info.get('phoneNumber'),
                            'time': record.get('startTime'),
                            'file': filepath,
                            'file_size_mb': file_size_mb,
                            'transcription_error': str(e)
                        })
                else:
                    # No API key, just save the file
                    processed.append({
                        'id': recording_id,
                        'duration': duration,
                        'from': from_info.get('phoneNumber'),
                        'to': to_info.get('phoneNumber'),
                        'time': record.get('startTime'),
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
        print("   python fetch_recordings_final.py                    # Fetch recent recordings")
        print("   python fetch_recordings_final.py 2025-08-12        # Fetch specific date")
        print("   python fetch_recordings_final.py 2025-08-12 15     # With custom duration filter")
        print("")
    
    fetch_recordings_with_all_permissions(date_str, min_duration)
