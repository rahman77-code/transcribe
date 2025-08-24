# 🚀 GitHub Actions Setup - SAFE 10-12 Hour Processing

## 🎯 What This Does
- Runs every night at 6 PM (takes 10-12 hours)
- Processes yesterday's calls SAFELY with no rate limits
- Downloads all recordings and transcriptions
- Saves everything as downloadable files
- 100% FREE - no credit card needed

## 📋 Step-by-Step Setup (10 minutes)

### Step 1: Create GitHub Account (if needed)
1. Go to [GitHub.com](https://github.com)
2. Click "Sign up"
3. Use any email address

### Step 2: Create New Repository
1. Click the **+** icon (top right)
2. Select **New repository**
3. Name it: `ringcentral-processor`
4. Keep it **Private**
5. Click **Create repository**

### Step 3: Upload Your Code
```bash
# In your terminal (in the recording folder)
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ringcentral-processor.git
git push -u origin main
```

**OR** use GitHub Desktop (easier):
1. Download [GitHub Desktop](https://desktop.github.com/)
2. Click "Add" → "Add Existing Repository"
3. Select your `recording` folder
4. Click "Publish repository"

### Step 4: Add Your Secret API Keys
1. Go to your repository on GitHub.com
2. Click **Settings** (in the repository menu)
3. Click **Secrets and variables** → **Actions**
4. Click **New repository secret**

Add these secrets ONE BY ONE:

| Secret Name | Value |
|------------|-------|
| `RC_CLIENT_ID` | `VNKRmCCWukXcPadmaLZoMu` |
| `RC_CLIENT_SECRET` | `37zo0FbARv5fcHIDHyh9485r2EA57ulqTdo1znecBZwQ` |
| `RC_JWT` | `eyJraWQiOiI4NzYyZjU5OGQwNTk0NGRiODZiZjVjYTk3ODA0NzYwOCIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0...` (your full JWT) |
| `GROQ_API_KEY_1` | `your_groq_api_key_1_here` |
| `GROQ_API_KEY_2` | `your_groq_api_key_2_here` |
| `GROQ_API_KEY_3` | `your_groq_api_key_3_here` |
| `HUBSPOT_ACCESS_TOKEN` | `your_hubspot_access_token_here` |

⚠️ **IMPORTANT**: Copy each value EXACTLY as shown, no extra spaces!

### Step 5: Enable GitHub Actions
1. Go to **Actions** tab in your repository
2. Click **I understand my workflows, go ahead and enable them**

### Step 6: Run It Now (Optional)
1. Go to **Actions** tab
2. Click **Safe Daily Call Processor (10-12 hours)**
3. Click **Run workflow** → **Run workflow**
4. It will start processing immediately!

## 📅 Automatic Schedule
- Runs every day at 6 PM automatically
- Takes 10-12 hours (finishes by 6 AM)
- Processes previous day's calls
- NO RATE LIMITS - guaranteed to complete

## 📥 How to Download Results
1. Go to **Actions** tab
2. Click on the completed workflow run
3. Scroll down to **Artifacts**
4. Download `recordings-XXX.zip`
5. Contains all MP3s and transcriptions!

## 🔧 Monitoring Progress
While it's running:
1. Go to **Actions** tab
2. Click on the running workflow
3. Click on **process-calls-safely**
4. Watch the live logs!

## 💡 Pro Tips

### Add More API Keys (Optional)
If you have more Groq keys:
1. Add as `GROQ_API_KEY_4`, `GROQ_API_KEY_5`, etc.
2. The script automatically detects them

### Change Schedule
Edit `.github/workflows/daily-processor-safe.yml`:
```yaml
# Change this line to your preferred time
- cron: '0 0 * * *'  # Currently 6 PM Central
```

[Cron Schedule Helper](https://crontab.guru/)

### Manual Processing
You can run it anytime:
1. Actions → Safe Daily Call Processor
2. Run workflow → Run workflow

## ❓ Troubleshooting

**"Permission denied" error?**
- Make sure repository is set to Private
- Check all secrets are added correctly

**"Not seeing Actions tab?"**
- Push the `.github` folder to your repository
- Refresh the page

**"Want to process specific date?"**
- Edit `daily_call_processor_safe.py`
- Change the date in the code
- Push changes and run

## 🎉 That's It!
Your calls will be processed automatically every night. Wake up to find all your transcriptions ready!

No laptop needed. No manual work. Just results! 🚀
