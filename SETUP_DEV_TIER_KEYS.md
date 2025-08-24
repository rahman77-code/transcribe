# 🚀 Setting Up Your Dev Tier Keys for 1000+ Recordings

## Your Dev Tier Keys (Replace with your actual keys)
1. `gsk_YOUR_FIRST_GROQ_API_KEY_HERE`
2. `gsk_YOUR_SECOND_GROQ_API_KEY_HERE`
3. `gsk_YOUR_THIRD_GROQ_API_KEY_HERE`
4. `gsk_YOUR_FOURTH_GROQ_API_KEY_HERE`
5. `gsk_YOUR_FIFTH_GROQ_API_KEY_HERE`
6. `gsk_YOUR_SIXTH_GROQ_API_KEY_HERE`

## Step 1: Add Keys to GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Update these secrets (replace with your new keys):

```
GROQ_API_KEY_1 = gsk_YOUR_FIRST_GROQ_API_KEY_HERE
GROQ_API_KEY_2 = gsk_YOUR_SECOND_GROQ_API_KEY_HERE
GROQ_API_KEY_3 = gsk_YOUR_THIRD_GROQ_API_KEY_HERE
GROQ_API_KEY_4 = gsk_YOUR_FOURTH_GROQ_API_KEY_HERE
GROQ_API_KEY_5 = gsk_YOUR_FIFTH_GROQ_API_KEY_HERE
GROQ_API_KEY_6 = gsk_YOUR_SIXTH_GROQ_API_KEY_HERE
```

4. Add this configuration secret:
```
DEV_TIER_KEYS = 1,2,3,4,5,6
```

## Step 2: Test Locally (Optional)

Create a `.env` file in your project:
```env
# RingCentral credentials
RC_CLIENT_ID=your_client_id
RC_CLIENT_SECRET=your_client_secret
RC_JWT=your_jwt_token
RC_SERVER_URL=https://platform.ringcentral.com

# Your dev tier keys
GROQ_API_KEY_1=gsk_YOUR_FIRST_GROQ_API_KEY_HERE
GROQ_API_KEY_2=gsk_YOUR_SECOND_GROQ_API_KEY_HERE
GROQ_API_KEY_3=gsk_YOUR_THIRD_GROQ_API_KEY_HERE
GROQ_API_KEY_4=gsk_YOUR_FOURTH_GROQ_API_KEY_HERE
GROQ_API_KEY_5=gsk_YOUR_FIFTH_GROQ_API_KEY_HERE
GROQ_API_KEY_6=gsk_YOUR_SIXTH_GROQ_API_KEY_HERE

# Mark them as dev tier
DEV_TIER_KEYS=1,2,3,4,5,6
```

Run locally:
```bash
python daily_call_processor_dev_tier.py --date 2024-01-15
```

## Step 3: Run in GitHub Actions

### Option A: Manual Run
1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **"Process Daily Calls (Dev Tier)"**
4. Click **"Run workflow"**
5. Optionally specify a date
6. Click **"Run workflow"** button

### Option B: Automatic Daily Run
The workflow is already set to run daily at 2 AM UTC.

## Step 4: Monitor Progress

The processor will show:
```
🚀 Dev Tier Processor initialized with 6 API keys
⚡ Limits: 7200s audio/hour, 300 req/min

📊 CAPACITY ANALYSIS
==================================================
API Keys: 6 dev tier keys
Audio capacity: 259.2 hours total
Max recordings by audio: 7776.0
Max recordings by time: 3085.7
✅ Can process ~3085 recordings in 6 hours
==================================================

[1/1000] Processing recording | 0.1% | ETA: 3.6h | Elapsed: 0.0h
🔑 Transcribing with dev key #1 (120/7200s, 2/300 req/min)
✅ Transcription successful with key #1
```

## Expected Performance

With 6 dev tier keys (300 RPM each):
- **Processing time**: ~3.6 hours for 1000 recordings
- **Success rate**: >99%
- **No rate limit errors**
- **2.4 hour safety buffer**

## Files Created

1. **`daily_call_processor_dev_tier.py`** - The optimized processor
2. **`.github/workflows/process_calls_dev_tier.yml`** - GitHub Actions workflow
3. **`DEV_TIER_SETUP_GUIDE.md`** - Detailed setup guide

## 🚨 Delete This File After Setup!

This file contains your API keys. After adding them to GitHub Secrets, delete this file for security.

## Ready to Process 1000+ Recordings! 🎉


