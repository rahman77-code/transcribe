"""
Create CSV from existing recordings and transcriptions
This processes what we already downloaded without making new API calls
"""

import os
import csv
import json
import re
from datetime import datetime
from pathlib import Path

def extract_phone_from_transcription(text):
    """Extract phone numbers mentioned in transcription text"""
    # Pattern for US phone numbers
    phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    phones = re.findall(phone_pattern, text)
    return phones

def process_existing_recordings():
    """Process all existing recordings and create CSV"""
    
    print("📊 Processing existing recordings and transcriptions...")
    
    # Get all audio files in recordings folder
    recordings_dir = Path('recordings')
    if not recordings_dir.exists():
        print("❌ No recordings folder found")
        return
    
    # Get all transcription files
    transcription_files = list(Path('.').glob('recording_*_transcription.txt'))
    print(f"Found {len(transcription_files)} transcription files")
    
    # Prepare data for CSV
    csv_data = []
    
    for trans_file in transcription_files:
        # Parse filename to get recording ID
        # Format: recording_unknown_3183430035008_transcription.txt
        parts = trans_file.stem.split('_')
        if len(parts) >= 3:
            extension = parts[1]  # 'unknown' in most cases
            recording_id = parts[2].replace('transcription', '')
            
            # Read transcription
            try:
                with open(trans_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Extract metadata from header
                    filename_line = lines[0].strip() if len(lines) > 0 else ""
                    date_line = lines[1].strip() if len(lines) > 1 else ""
                    transcription = ' '.join(lines[4:]).strip() if len(lines) > 4 else ""
                    
                    # Extract date/time
                    date_match = re.search(r'Transcribed on: (.+)', date_line)
                    transcribed_date = date_match.group(1) if date_match else ""
                    
                    # Look for phone numbers in transcription
                    phones_in_text = extract_phone_from_transcription(transcription)
                    
                    # Check if corresponding audio file exists
                    audio_filename = f"recording_{extension}_{recording_id}.mp3"
                    audio_path = recordings_dir / audio_filename
                    has_audio = audio_path.exists()
                    
                    # Get file size if exists
                    file_size_mb = 0
                    if has_audio:
                        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
                    
                    # Add to CSV data
                    csv_data.append({
                        'Recording_ID': recording_id,
                        'Extension': extension,
                        'Transcription_Date': transcribed_date,
                        'Audio_File': audio_filename if has_audio else 'Not downloaded',
                        'File_Size_MB': f"{file_size_mb:.2f}" if has_audio else "0",
                        'Transcription_File': trans_file.name,
                        'Phone_Numbers_In_Text': '; '.join(phones_in_text) if phones_in_text else '',
                        'Transcription_Preview': transcription[:200] + '...' if len(transcription) > 200 else transcription,
                        'Full_Transcription': transcription
                    })
                    
            except Exception as e:
                print(f"Error processing {trans_file}: {e}")
    
    # Sort by recording ID
    csv_data.sort(key=lambda x: x['Recording_ID'])
    
    # Create CSV file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f"existing_recordings_{timestamp}.csv"
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Recording_ID',
            'Extension', 
            'Transcription_Date',
            'Audio_File',
            'File_Size_MB',
            'Transcription_File',
            'Phone_Numbers_In_Text',
            'Transcription_Preview',
            'Full_Transcription'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    
    # Also save as JSON for easier processing
    json_filename = f"existing_recordings_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(csv_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n✅ CSV Export Complete!")
    print(f"📄 Files created:")
    print(f"   - {csv_filename}")
    print(f"   - {json_filename}")
    print(f"\n📊 Summary:")
    print(f"   - Total recordings processed: {len(csv_data)}")
    print(f"   - Recordings with audio files: {sum(1 for r in csv_data if r['Audio_File'] != 'Not downloaded')}")
    print(f"   - Recordings with phone numbers in text: {sum(1 for r in csv_data if r['Phone_Numbers_In_Text'])}")
    
    # Show sample of phone numbers found
    all_phones = []
    for record in csv_data:
        if record['Phone_Numbers_In_Text']:
            phones = record['Phone_Numbers_In_Text'].split('; ')
            all_phones.extend(phones)
    
    unique_phones = set(all_phones)
    if unique_phones:
        print(f"\n📱 Found {len(unique_phones)} unique phone numbers in transcriptions:")
        for i, phone in enumerate(sorted(unique_phones)[:10], 1):
            print(f"   {i}. {phone}")
        if len(unique_phones) > 10:
            print(f"   ... and {len(unique_phones) - 10} more")
    
    return csv_data

def create_full_csv_with_metadata():
    """Create a more detailed CSV if we have the original API response data"""
    
    # Check if we have any saved response data
    response_files = list(Path('.').glob('recordings_data_*.json'))
    
    if response_files:
        print(f"\n📂 Found {len(response_files)} saved response files")
        # Use the most recent one
        latest_file = max(response_files, key=lambda f: f.stat().st_mtime)
        
        print(f"Using: {latest_file}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create detailed CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"detailed_recordings_{timestamp}.csv"
        
        # Extract all possible fields
        if data and isinstance(data, list) and len(data) > 0:
            fieldnames = list(data[0].keys())
            
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            print(f"\n✅ Detailed CSV created: {csv_filename}")
            print(f"   Contains {len(data)} records with {len(fieldnames)} fields each")

if __name__ == "__main__":
    # Process existing recordings
    process_existing_recordings()
    
    # Also check for detailed data
    create_full_csv_with_metadata()


