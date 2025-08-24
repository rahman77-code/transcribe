#!/usr/bin/env python3
"""
Setup script for automatic Google Sheets integration
This will create a public Google Sheet that updates automatically
"""

import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

def setup_google_sheets():
    """
    Step-by-step setup for Google Sheets integration
    """
    print("📊 Google Sheets Setup Guide")
    print("="*50)
    print("\n1. First, you need a Google Service Account:")
    print("   a. Go to https://console.cloud.google.com/")
    print("   b. Create a new project or select existing")
    print("   c. Enable Google Sheets API")
    print("   d. Create Service Account credentials")
    print("   e. Download the JSON key file")
    print("\n2. Create a Google Sheet:")
    print("   a. Go to https://sheets.google.com")
    print("   b. Create a new spreadsheet")
    print("   c. Name it 'Call Transcriptions'")
    print("   d. Share it with your service account email")
    print("   e. Set sharing to 'Anyone with link can view'")
    print("\n3. Add these secrets to GitHub:")
    print("   - GOOGLE_SERVICE_ACCOUNT_KEY (the JSON content)")
    print("   - GOOGLE_SHEET_ID (from the sheet URL)")
    print("="*50)

def upload_to_sheets(json_file_path, sheet_id, creds_json):
    """
    Upload transcription data to Google Sheets
    """
    # Parse credentials
    creds = Credentials.from_service_account_info(
        json.loads(creds_json),
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    
    # Connect to Google Sheets
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(sheet_id)
    worksheet = sheet.get_worksheet(0)
    
    # Load transcription data
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Clear existing data
    worksheet.clear()
    
    # Add headers with statistics
    headers = [
        f"Call Transcriptions - {data['statistics']['processing_date']}",
        f"Total: {data['statistics']['total_recordings_found']} | Processed: {data['statistics']['total_recordings_processed']} | Success Rate: {data['statistics']['success_rate']}"
    ]
    worksheet.append_rows([headers, []])
    
    # Add column headers
    worksheet.append_row([
        "Recording ID", "Date/Time", "Duration (min)", 
        "From", "To", "Direction", "Transcription"
    ])
    
    # Add data rows
    for trans in data['transcriptions']:
        worksheet.append_row([
            trans['id'],
            trans['date'],
            round(trans['duration'] / 60, 1),
            trans['from'],
            trans['to'],
            trans['direction'],
            trans['transcription']
        ])
    
    # Format the sheet
    worksheet.format('A3:G3', {
        "backgroundColor": {"red": 0.2, "green": 0.5, "blue": 0.8},
        "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
    })
    
    # Get the public URL
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"
    return sheet_url

if __name__ == "__main__":
    setup_google_sheets()
