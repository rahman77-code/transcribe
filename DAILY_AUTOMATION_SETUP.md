# 📞 Daily RingCentral Call Recording Automation

This system automatically fetches, downloads, and transcribes your RingCentral call recordings every day.

## 🚀 Features

- ✅ **Daily Automation**: Runs automatically every day at 1:00 AM
- ✅ **Complete Call Logs**: Captures all fields you requested (Type, From, To, Ext, etc.)
- ✅ **Smart Filtering**: Only processes recordings >= 30 seconds
- ✅ **Automatic Transcription**: Uses Groq Whisper AI for transcription
- ✅ **Rate Limit Handling**: Built-in retry logic and delays
- ✅ **Organized Output**: Creates dated folders with all data
- ✅ **HubSpot Ready**: Prepared for HubSpot integration

## 📁 File Structure

```
daily_recordings/
├── 2025-08-13/
│   ├── call_log_20250813.csv          # All calls for the day
│   ├── processed_recordings_20250813.csv # Calls with transcriptions
│   ├── summary_20250813.json          # Daily summary
│   ├── recording_*.mp3                # Audio files
│   └── recording_*_transcription.txt  # Transcription files
└── 2025-08-14/
    └── ... (next day's files)
```

## 🔧 Setup Instructions

### 1. Update Environment Variables

1. Copy your new credentials:
   ```bash
   Copy-Item new_credentials.env .env -Force
   ```

2. Or manually update your `.env` file with:
   ```
   RC_SERVER_URL=https://platform.ringcentral.com/
   RC_CLIENT_ID=VNKRmCCWukXcPadmaLZoMu
   RC_CLIENT_SECRET=37zo0FbARv5fcHIDHyh9485r2EA57ulqTdo1znecBZwQ
   RC_JWT=eyJraWQiOiI4NzYyZjU5OGQwNTk0NGRiODZiZjVjYTk3ODA0NzYwOCIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0...
   GROQ_API_KEY=your_groq_api_key_here
   HUBSPOT_ACCESS_TOKEN=your_hubspot_access_token_here
   ```

### 2. Install Required Package

```bash
pip install schedule
```

### 3. Test the Script

Run once to test:
```bash
python daily_call_processor.py
```

### 4. Set Up Daily Automation

#### Option A: Windows Task Scheduler (Recommended)

1. Open PowerShell as Administrator
2. Navigate to the script directory:
   ```powershell
   cd C:\Users\airkooled\Desktop\recording
   ```
3. Run the setup script:
   ```powershell
   .\setup_daily_schedule.ps1
   ```

#### Option B: Manual Task Scheduler Setup

1. Open Task Scheduler (taskschd.msc)
2. Create Basic Task
3. Name: "RingCentral Daily Call Processor"
4. Trigger: Daily at 1:00 AM
5. Action: Start `run_daily_processor.bat`
6. Set to run whether user is logged on or not

#### Option C: Keep Script Running

Run continuously with built-in scheduler:
```bash
python daily_call_processor.py --scheduled
```

## 📊 Output Files Explained

### 1. `call_log_YYYYMMDD.csv`
Contains ALL calls for the day with these columns:
- Type (VoIP Call, Phone Call, etc.)
- From / From_Name
- To / To_Name
- Ext / Ext_Name
- Forwarded_To
- Date_Time
- Has_Recording (Yes/No)
- Recording_ID
- Action
- Result
- Length (formatted as MM:SS)
- Duration_Seconds
- Included (cost)
- Purchased (cost)
- Direction
- Session_ID
- Call_ID

### 2. `processed_recordings_YYYYMMDD.csv`
Contains only calls with recordings that were downloaded and transcribed:
- All columns from call_log
- Audio_File
- Transcription
- File_Size_MB

### 3. `summary_YYYYMMDD.json`
Daily processing summary:
```json
{
  "date": "2025-08-13",
  "total_calls": 500,
  "calls_with_recordings": 400,
  "recordings_processed": 350,
  "processing_time": "0:45:30",
  "timestamp": "2025-08-13T02:15:30"
}
```

## 🔍 Monitoring

### Check Logs
```bash
type daily_call_processor.log
```

### View Today's Summary
```powershell
Get-Content "daily_recordings\$(Get-Date -Format 'yyyy-MM-dd')\summary_$(Get-Date -Format 'yyyyMMdd').json"
```

### Check Task Status
```powershell
Get-ScheduledTask -TaskName "RingCentral Daily Call Processor"
```

## ⚙️ Configuration

Edit `daily_call_processor.py` to adjust:
- `download_delay`: Seconds between downloads (default: 5)
- `max_retries`: Retry attempts for failed downloads (default: 3)
- `retry_delay`: Seconds to wait between retries (default: 30)
- Schedule time: Change from "01:00" to your preferred time

## 🚨 Troubleshooting

### Rate Limiting
If you hit rate limits:
1. Increase `download_delay` in the script
2. Process in smaller batches
3. Run at different times

### Missing Recordings
Check:
1. Recording duration >= 30 seconds
2. Recording exists in RingCentral
3. Sufficient API permissions

### Authentication Errors
1. Verify JWT token is current
2. Check client ID and secret
3. Ensure all permissions are enabled

## 🔗 HubSpot Integration

The script is prepared for HubSpot integration. To enable:
1. Implement the `send_to_hubspot()` method
2. Use the HUBSPOT_ACCESS_TOKEN to authenticate
3. Map call data to HubSpot contact/deal properties

## 📈 Daily Workflow

1. **1:00 AM**: Script runs automatically
2. **Fetches**: All calls from previous day
3. **Downloads**: Recordings >= 30 seconds
4. **Transcribes**: Each recording with Groq
5. **Saves**: CSV files and audio/text files
6. **Logs**: All activities to log file
7. **Optional**: Sends data to HubSpot

## 🛑 Stop Automation

To stop the daily automation:
```powershell
Unregister-ScheduledTask -TaskName "RingCentral Daily Call Processor" -Confirm:$false
```

## 📞 Support

Check the log file for detailed information about each run:
- Success/failure of each download
- Rate limit warnings
- Processing statistics
- Error details

