"""
Extract phone numbers from RingCentral call logs
This will fetch the call log data and extract all From/To phone numbers
"""

import os
import csv
import json
from datetime import datetime, timedelta
from ringcentral import SDK
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

def fetch_call_logs_for_phone_numbers(date_str, min_duration=30):
    """Fetch call logs just to extract phone numbers (no downloads)"""
    
    # RingCentral credentials
    config = {
        "clientId": "0gAEMMaAIb9aVRHMOSW5se",
        "clientSecret": "5TQ84XRt1eNfG90l558cie9TWqoVHQTcZfRT7zHJXZA2",
        "server": "https://platform.ringcentral.com"
    }
    
    JWT_TOKEN = os.getenv("RINGCENTRAL_JWT_TOKEN")
    
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
    
    params.extend([
        "perPage=1000",
        "view=Detailed",
        "recordingType=All"
    ])
    
    url = f"{base_url}?{'&'.join(params)}"
    
    print(f"\n📅 Fetching call logs for: {date_str}")
    print(f"⏱️  Filtering for calls >= {min_duration} seconds with recordings")
    
    try:
        # Get call logs (no downloads, just metadata)
        response = platform.get(url)
        data = response.json_dict()
        records = data.get('records', [])
        
        print(f"📊 Found {len(records)} total call logs")
        
        # Filter for recordings >= min_duration
        filtered_records = []
        for record in records:
            if 'recording' in record and record.get('duration', 0) >= min_duration:
                filtered_records.append(record)
        
        print(f"🎯 Found {len(filtered_records)} recordings >= {min_duration} seconds")
        
        return filtered_records
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def create_phone_numbers_csv(records):
    """Create CSV with phone numbers and call details"""
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f"phone_numbers_{timestamp}.csv"
    
    # Prepare data
    csv_data = []
    phone_stats = defaultdict(lambda: {'as_caller': 0, 'as_receiver': 0, 'names': set()})
    
    for record in records:
        recording_info = record.get('recording', {})
        recording_id = recording_info.get('id', '')
        
        from_info = record.get('from', {})
        to_info = record.get('to', {})
        ext_info = record.get('extension', {})
        
        from_number = from_info.get('phoneNumber', '').lstrip('+')
        from_name = from_info.get('name', '')
        to_number = to_info.get('phoneNumber', '').lstrip('+')
        to_name = to_info.get('name', '')
        
        duration = record.get('duration', 0)
        
        # Update phone statistics
        if from_number:
            phone_stats[from_number]['as_caller'] += 1
            if from_name:
                phone_stats[from_number]['names'].add(from_name)
        
        if to_number:
            phone_stats[to_number]['as_receiver'] += 1
            if to_name:
                phone_stats[to_number]['names'].add(to_name)
        
        # Add to CSV data
        csv_data.append({
            'Recording_ID': recording_id,
            'Date_Time': record.get('startTime', ''),
            'Duration_Seconds': duration,
            'Duration_Formatted': f"{duration//60}:{duration%60:02d}",
            'From_Number': from_number,
            'From_Name': from_name,
            'To_Number': to_number,
            'To_Name': to_name,
            'Direction': record.get('direction', ''),
            'Call_Type': record.get('type', ''),
            'Extension': ext_info.get('extensionNumber', ''),
            'Extension_Name': ext_info.get('name', ''),
            'Recording_Type': recording_info.get('type', ''),
            'Recording_ID_Full': recording_id
        })
    
    # Write main CSV
    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Recording_ID', 'Date_Time', 'Duration_Seconds', 'Duration_Formatted',
            'From_Number', 'From_Name', 'To_Number', 'To_Name',
            'Direction', 'Call_Type', 'Extension', 'Extension_Name',
            'Recording_Type', 'Recording_ID_Full'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)
    
    # Create phone number summary CSV
    summary_filename = f"phone_summary_{timestamp}.csv"
    summary_data = []
    
    for phone, stats in phone_stats.items():
        summary_data.append({
            'Phone_Number': phone,
            'Total_Calls': stats['as_caller'] + stats['as_receiver'],
            'As_Caller': stats['as_caller'],
            'As_Receiver': stats['as_receiver'],
            'Names': '; '.join(stats['names']) if stats['names'] else 'Unknown'
        })
    
    # Sort by total calls
    summary_data.sort(key=lambda x: x['Total_Calls'], reverse=True)
    
    with open(summary_filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Phone_Number', 'Total_Calls', 'As_Caller', 'As_Receiver', 'Names']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_data)
    
    # Also save as JSON
    json_filename = f"call_logs_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(csv_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print(f"\n✅ Phone Number Extraction Complete!")
    print(f"\n📄 Files created:")
    print(f"   - {csv_filename} (All call details)")
    print(f"   - {summary_filename} (Phone number summary)")
    print(f"   - {json_filename} (JSON backup)")
    
    print(f"\n📊 Summary:")
    print(f"   - Total recordings: {len(csv_data)}")
    print(f"   - Unique phone numbers: {len(phone_stats)}")
    
    # Show top 10 most frequent numbers
    print(f"\n📱 Top 10 Most Frequent Numbers:")
    for i, data in enumerate(summary_data[:10], 1):
        print(f"   {i}. {data['Phone_Number']} - {data['Total_Calls']} calls ({data['Names']})")
    
    print(f"\n💡 Note: These are all recordings >= 30 seconds from {records[0].get('startTime', '')[:10] if records else 'N/A'}")
    
    return csv_data, summary_data

if __name__ == "__main__":
    # Fetch call logs for August 12, 2025
    date_str = "2025-08-12"
    min_duration = 30
    
    print("📱 Extracting Phone Numbers from RingCentral Call Logs")
    print("=" * 60)
    
    # Fetch the call logs (metadata only, no downloads)
    records = fetch_call_logs_for_phone_numbers(date_str, min_duration)
    
    if records:
        # Create CSV files
        create_phone_numbers_csv(records)
    else:
        print("❌ No records found to process")


