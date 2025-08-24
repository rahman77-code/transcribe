#!/usr/bin/env python3
"""
Quick script to upload transcription results to Google Sheets
Run this after downloading your workflow artifacts
"""

import json
import sys
from pathlib import Path

print("📊 Quick Google Sheets Upload")
print("="*50)

# Check if files exist
json_files = list(Path('.').glob('transcriptions_*.json'))
if not json_files:
    print("❌ No transcription JSON files found in current directory!")
    print("Please download and extract your workflow artifacts first.")
    sys.exit(1)

print(f"✅ Found: {json_files[0]}")

# Load the data to show stats
with open(json_files[0], 'r', encoding='utf-8') as f:
    data = json.load(f)

if 'statistics' in data:
    stats = data['statistics']
    print(f"\n📈 Statistics:")
    print(f"   Date: {stats['processing_date']}")
    print(f"   Total Found: {stats['total_recordings_found']}")
    print(f"   Processed: {stats['total_recordings_processed']}")
    print(f"   Success Rate: {stats['success_rate']}")
else:
    print(f"\n📊 Found {len(data)} transcriptions")

print("\n🚀 To upload to Google Sheets:")
print("\n1. First time setup (only do once):")
print("   pip install gspread google-auth")

print("\n2. Create a Google Sheet and get credentials (see EXCEL_AND_PUBLIC_SHARING_GUIDE.md)")

print("\n3. Run this command with your credentials:")
print(f"""
python -c "
import json
import gspread
from google.oauth2.service_account import Credentials

# REPLACE THESE WITH YOUR VALUES
SERVICE_ACCOUNT_KEY = '''PASTE_YOUR_JSON_KEY_HERE'''
SHEET_ID = 'YOUR_SHEET_ID_HERE'

# Connect
creds = Credentials.from_service_account_info(
    json.loads(SERVICE_ACCOUNT_KEY),
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).get_worksheet(0)

# Load data
with open('{json_files[0]}', 'r') as f:
    data = json.load(f)

# Upload
sheet.clear()
if 'statistics' in data:
    stats = data['statistics']
    sheet.append_rows([
        [f'Call Transcriptions - ' + stats['processing_date']],
        [f'Total: ' + str(stats['total_recordings_found']) + ' | Processed: ' + str(stats['total_recordings_processed']) + ' | Success: ' + stats['success_rate']],
        [],
        ['Recording ID', 'Date/Time', 'Duration (min)', 'From', 'To', 'Direction', 'Transcription']
    ])
    transcriptions = data['transcriptions']
else:
    sheet.append_row(['Recording ID', 'Date/Time', 'Duration (min)', 'From', 'To', 'Direction', 'Transcription'])
    transcriptions = data

for t in transcriptions:
    sheet.append_row([
        t['id'], t['date'], round(t.get('duration', 0) / 60, 1),
        t['from'], t['to'], t['direction'], t['transcription']
    ])

print('✅ Uploaded to: https://docs.google.com/spreadsheets/d/' + SHEET_ID)
"
""")

print("\n📌 Or use the CSV file directly in Excel - it's already formatted!")
csv_files = list(Path('.').glob('transcriptions_*.csv'))
if csv_files:
    print(f"   Found: {csv_files[0]}")
    print("   Just double-click to open in Excel!")
