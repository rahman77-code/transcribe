# ☁️ Cloud Deployment Guide for RingCentral Call Processor

## 🎯 Why Cloud is Better
- ✅ Runs 24/7 without your laptop
- ✅ Never misses a day
- ✅ More reliable
- ✅ Can handle high volume
- ✅ Professional solution

## 🔥 Option 1: Railway (EASIEST - 5 Minutes!)

Railway offers $5 free credits monthly and super easy deployment.

### Steps:
1. Go to [Railway.app](https://railway.app)
2. Sign up with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Railway will automatically:
   - Create a server
   - Install Python
   - Run your script daily

### Setup Commands:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project in your folder
railway init

# Add your environment variables
railway variables set RC_CLIENT_ID=VNKRmCCWukXcPadmaLZoMu
railway variables set RC_CLIENT_SECRET=37zo0FbARv5fcHIDHyh9485r2EA57ulqTdo1znecBZwQ
railway variables set RC_JWT="your_jwt_token"
railway variables set GROQ_API_KEY_1="your_key_1"
railway variables set GROQ_API_KEY_2="your_key_2"
railway variables set GROQ_API_KEY_3="your_key_3"

# Deploy
railway up
```

## 💻 Option 2: Heroku (FREE Tier Available)

### Steps:
1. Create account at [Heroku.com](https://heroku.com)
2. Install Heroku CLI
3. Deploy with these commands:

```bash
# Create app
heroku create your-ringcentral-processor

# Add buildpack
heroku buildpacks:add heroku/python

# Set environment variables
heroku config:set RC_CLIENT_ID=VNKRmCCWukXcPadmaLZoMu
heroku config:set RC_CLIENT_SECRET=37zo0FbARv5fcHIDHyh9485r2EA57ulqTdo1znecBZwQ
heroku config:set RC_JWT="your_jwt_token"
heroku config:set GROQ_API_KEY_1="your_key_1"

# Deploy
git push heroku main

# Add scheduler
heroku addons:create scheduler:standard
heroku addons:open scheduler
# Set it to run: python daily_call_processor_multi_key.py
```

## 🔷 Option 3: Google Cloud Run (Pay Per Use)

Best for production - only pay when it runs.

```bash
# Install gcloud CLI
# Create project in Google Cloud Console

# Build and deploy
gcloud run deploy ringcentral-processor \
  --source . \
  --set-env-vars RC_CLIENT_ID=VNKRmCCWukXcPadmaLZoMu \
  --region us-central1

# Add Cloud Scheduler
gcloud scheduler jobs create http daily-processor \
  --schedule="0 2 * * *" \
  --uri=YOUR_CLOUD_RUN_URL \
  --http-method=GET
```

## 🌊 Option 4: DigitalOcean ($6/month)

Simple VPS solution:

1. Create a $6/month Droplet
2. SSH into server
3. Clone your code
4. Set up cron job:

```bash
# On the server
sudo apt update
sudo apt install python3 python3-pip

# Clone your code
git clone your-repo

# Install dependencies
pip3 install -r requirements.txt

# Add to crontab
crontab -e
# Add: 0 2 * * * cd /path/to/project && python3 daily_call_processor_multi_key.py
```

## 🚅 Option 5: AWS Lambda (Serverless)

Perfect for scheduled tasks:

```python
# Create lambda_handler.py
import os
from daily_call_processor_multi_key import DailyCallProcessorMultiKey

def lambda_handler(event, context):
    processor = DailyCallProcessorMultiKey()
    result = processor.process_daily_calls()
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
```

Then use AWS EventBridge to schedule it daily.

## 🎈 Option 6: Render.com (FREE)

1. Go to [Render.com](https://render.com)
2. Connect GitHub
3. Create "Background Worker"
4. Add environment variables
5. Deploy!

## 📦 Option 7: GitHub Actions (FREE)

Run directly from GitHub:

```yaml
# .github/workflows/daily-processor.yml
name: Daily Call Processor

on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily
  workflow_dispatch:  # Manual trigger

jobs:
  process-calls:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run processor
        env:
          RC_CLIENT_ID: ${{ secrets.RC_CLIENT_ID }}
          RC_CLIENT_SECRET: ${{ secrets.RC_CLIENT_SECRET }}
          RC_JWT: ${{ secrets.RC_JWT }}
          GROQ_API_KEY_1: ${{ secrets.GROQ_API_KEY_1 }}
          GROQ_API_KEY_2: ${{ secrets.GROQ_API_KEY_2 }}
          GROQ_API_KEY_3: ${{ secrets.GROQ_API_KEY_3 }}
        run: python daily_call_processor_multi_key.py
```
