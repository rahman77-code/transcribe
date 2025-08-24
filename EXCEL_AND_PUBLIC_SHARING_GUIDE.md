# 📊 Excel & Public Sharing - Step by Step Guide

## 🚀 Quick Option: Manual Download to Excel

### Step 1: Get Your Results
1. Go to: https://github.com/rahman77-code/transcribe
2. Click **"Actions"** tab
3. Find your completed workflow (look for green checkmark ✅)
4. Click on the workflow run
5. Scroll down to **"Artifacts"** section
6. Download **"ultra-recordings-XXX"** (where XXX is the run number)

### Step 2: Extract and Open in Excel
1. Extract the downloaded ZIP file
2. Find the CSV file: `transcriptions_2025-08-XX.csv`
3. Double-click to open in Excel
4. Excel will show all your transcriptions with statistics at the top!

---

## 📈 Option 2: Google Sheets (Auto-Updated & Public)

### Step 1: Create Google Cloud Project
1. Go to: https://console.cloud.google.com/
2. Click **"Create Project"**
3. Name it: "Call Transcriptions"
4. Wait for project creation

### Step 2: Enable Google Sheets API
1. In your project, go to **"APIs & Services"** → **"Library"**
2. Search for **"Google Sheets API"**
3. Click on it and press **"ENABLE"**

### Step 3: Create Service Account
1. Go to **"APIs & Services"** → **"Credentials"**
2. Click **"+ CREATE CREDENTIALS"** → **"Service account"**
3. Name: "transcription-uploader"
4. Click **"CREATE AND CONTINUE"**
5. Skip the optional steps, click **"DONE"**

### Step 4: Get Service Account Key
1. Click on your new service account email
2. Go to **"KEYS"** tab
3. Click **"ADD KEY"** → **"Create new key"**
4. Choose **"JSON"** → **"CREATE"**
5. Save the downloaded JSON file (you'll need its contents)

### Step 5: Create Public Google Sheet
1. Go to: https://sheets.google.com
2. Create a new blank spreadsheet
3. Name it: **"Call Transcriptions - Public"**
4. Click **"Share"** button (top right)
5. Change to **"Anyone with the link"** → **"Viewer"**
6. Copy the sharing link
7. Also share with your service account email (from step 3)

### Step 6: Get Sheet ID
From your sheet URL: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
Copy the `SHEET_ID_HERE` part

### Step 7: Add to GitHub Secrets
1. Go to your repo: https://github.com/rahman77-code/transcribe
2. Go to **Settings** → **Secrets and variables** → **Actions**
3. Add two new secrets:
   - **Name**: `GOOGLE_SERVICE_ACCOUNT_KEY`
   - **Value**: Copy entire contents of the JSON file from Step 4
   
   - **Name**: `GOOGLE_SHEET_ID`  
   - **Value**: The Sheet ID from Step 6

---

## 🔧 Option 3: Quick Public Sharing (Without Google)

### Using GitHub Pages (Simplest)
1. After workflow completes, download the CSV
2. Go to: https://github.com/rahman77-code/transcribe
3. Click **"Add file"** → **"Upload files"**
4. Upload the CSV to a `docs` folder
5. Go to **Settings** → **Pages**
6. Source: **"Deploy from a branch"**
7. Branch: **"main"** → **"/docs"**
8. Your CSV will be public at: `https://rahman77-code.github.io/transcribe/transcriptions_2025-08-XX.csv`

### Using Pastebin (For Quick Sharing)
1. Download your CSV file
2. Go to: https://pastebin.com
3. Paste the CSV contents
4. Set expiration as needed
5. Click **"Create New Paste"**
6. Share the link with others

---

## 🤖 Automated Upload Script

Create this file locally as `upload_to_sheets.py`:

```python
import json
import gspread
from google.oauth2.service_account import Credentials

# Configuration
SERVICE_ACCOUNT_KEY = '''
PASTE YOUR ENTIRE JSON KEY FILE CONTENTS HERE
'''
SHEET_ID = 'YOUR_SHEET_ID_HERE'
JSON_FILE = 'transcriptions_2025-08-15.json'  # Change to your file

# Connect to Google Sheets
creds = Credentials.from_service_account_info(
    json.loads(SERVICE_ACCOUNT_KEY),
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID)
worksheet = sheet.get_worksheet(0)

# Load your data
with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Clear existing data
worksheet.clear()

# Add headers with stats
stats = data['statistics']
worksheet.append_rows([
    [f"Call Transcriptions - {stats['processing_date']}"],
    [f"Total: {stats['total_recordings_found']} | Processed: {stats['total_recordings_processed']} | Success: {stats['success_rate']}"],
    [],
    ["Recording ID", "Date/Time", "Duration (min)", "From", "To", "Direction", "Transcription"]
])

# Add all transcriptions
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

print(f"✅ Uploaded! View at: https://docs.google.com/spreadsheets/d/{SHEET_ID}")
```

### To run:
1. Install requirements: `pip install gspread google-auth`
2. Update the configuration in the script
3. Run: `python upload_to_sheets.py`

---

## 📱 Share Your Public Sheet

Once uploaded, your Google Sheet link can be shared with anyone:
- They can view without Google account
- They can download as Excel/PDF
- Updates automatically when you re-run the script
- Can embed in websites using iframe

Example public link:
```
https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit?usp=sharing
```

---

## 💡 Pro Tips

1. **For Excel**: The CSV already has statistics in the header - just share the Excel file!

2. **For Google Sheets**: Once set up, you can update the same sheet daily - it will overwrite with new data

3. **For Quick Sharing**: GitHub Gists (https://gist.github.com) also work great for CSV files

4. **Security**: Never share files with personal phone numbers publicly - consider removing/masking them first
