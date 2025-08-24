# 🚀 SIMPLE SETUP GUIDE - WHERE TO RUN & HOW IT WORKS

## 📍 WHERE TO RUN THE COMMAND

**You run it RIGHT HERE in your current PowerShell terminal!**

```powershell
# Step 1: First update your .env with the new API keys
Copy-Item updated_env_with_keys.txt .env -Force

# Step 2: Then run this in the SAME terminal window
.\setup_daily_schedule.ps1
```

## ⚠️ IMPORTANT: About Your Laptop

### ❌ **The script WON'T run if your laptop is OFF**
### ✅ **The script WILL run if:**
- Your laptop is ON but you're logged out
- Your laptop is sleeping but plugged in (configure Power Settings)
- Your laptop lid is closed but still powered on

## 🔧 How Windows Task Scheduler Works

1. **When you run `.\setup_daily_schedule.ps1`**, it creates a scheduled task in Windows
2. This task is stored in Windows and runs at 2:00 AM daily
3. **BUT** - Windows can't run anything if the computer is completely OFF

## 💡 SOLUTIONS FOR 24/7 OPERATION

### Option 1: Leave Laptop On (Recommended for Testing)
- Plug in your laptop
- Go to **Settings > Power & Sleep**
- Set "When plugged in, PC goes to sleep after" to **Never**
- Close the lid or just leave it running

### Option 2: Use Wake Timers
```powershell
# This will wake your computer at 1:55 AM to run the task
powercfg /waketimer enable
```

### Option 3: Cloud Server (Best for Production)
- Deploy to a cloud VM (AWS, Azure, etc.)
- Runs 24/7 without your laptop

## 🎯 QUICK SETUP RIGHT NOW

Run these commands in your current PowerShell window:

```powershell
# 1. Update your API keys
Copy-Item updated_env_with_keys.txt .env -Force

# 2. Set up the daily schedule
.\setup_daily_schedule.ps1

# 3. (Optional) Test it works right now
python daily_call_processor_multi_key.py
```

## 📊 What Happens Each Day

**At 2:00 AM (if laptop is ON):**
1. Script automatically starts
2. Fetches yesterday's calls
3. Downloads recordings
4. Transcribes using your 3 API keys (rotates automatically)
5. Saves to `daily_recordings/YYYY-MM-DD/`
6. Goes back to sleep until next day

## 🤔 ALTERNATIVE: Run Manually When Needed

If you prefer to run it manually when your laptop is on:

```powershell
# Just run this whenever you want to process yesterday's calls
python daily_call_processor_multi_key.py
```

You can also modify it to run at startup instead of 2 AM!
