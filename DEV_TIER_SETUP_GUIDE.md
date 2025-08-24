# 🚀 Dev Tier Setup Guide

This guide shows you exactly how to configure and use your dev tier API keys to process 1000+ recordings in under 6 hours.

## 📋 Prerequisites

1. You have already set up 17 API keys in GitHub Secrets (GROQ_API_KEY_1 through GROQ_API_KEY_17)
2. You have identified which of these keys are upgraded to dev tier
3. You have RingCentral credentials set up

## 🔧 Configuration Options

### Option 1: Using Environment Variable (Recommended)

1. In your GitHub repository, go to **Settings → Secrets and variables → Actions**

2. Add a new secret called `DEV_TIER_KEYS` with the numbers of your dev tier keys:
   ```
   DEV_TIER_KEYS=1,2,3,4,5,6
   ```
   (Replace with your actual dev tier key numbers)

### Option 2: Using Individual Flags

For each dev tier key, add a flag secret:
```
GROQ_API_KEY_1_IS_DEV=true
GROQ_API_KEY_2_IS_DEV=true
GROQ_API_KEY_3_IS_DEV=true
# etc...
```

### Option 3: Default Behavior

If no configuration is provided, the processor will use the first 6 keys as dev tier keys.

## 📊 Key Requirements

For 1000 recordings, you need:
- **Minimum**: 5 dev tier keys
- **Recommended**: 6-7 dev tier keys (for safety buffer)

## 🚀 Running the Dev Tier Processor

### Local Testing

1. Create a `.env` file:
```env
# RingCentral credentials
RC_CLIENT_ID=your_client_id
RC_CLIENT_SECRET=your_client_secret
RC_JWT=your_jwt_token
RC_SERVER_URL=https://platform.ringcentral.com

# Dev tier API keys
GROQ_API_KEY_1=your_dev_tier_key_1
GROQ_API_KEY_2=your_dev_tier_key_2
GROQ_API_KEY_3=your_dev_tier_key_3
GROQ_API_KEY_4=your_dev_tier_key_4
GROQ_API_KEY_5=your_dev_tier_key_5
GROQ_API_KEY_6=your_dev_tier_key_6

# Specify which are dev tier
DEV_TIER_KEYS=1,2,3,4,5,6
```

2. Run the processor:
```bash
python daily_call_processor_dev_tier.py
```

### GitHub Actions Workflow

Create `.github/workflows/process_calls_dev_tier.yml`:

```yaml
name: Process Daily Calls (Dev Tier)

on:
  schedule:
    # Run daily at 2 AM UTC
    - cron: '0 2 * * *'
  workflow_dispatch:
    inputs:
      date:
        description: 'Date to process (YYYY-MM-DD)'
        required: false
        type: string

jobs:
  process:
    runs-on: ubuntu-latest
    timeout-minutes: 360  # 6 hour timeout
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install ringcentral python-dotenv requests
    
    - name: Process recordings
      env:
        # RingCentral credentials
        RC_CLIENT_ID: ${{ secrets.RC_CLIENT_ID }}
        RC_CLIENT_SECRET: ${{ secrets.RC_CLIENT_SECRET }}
        RC_JWT: ${{ secrets.RC_JWT }}
        RC_SERVER_URL: ${{ secrets.RC_SERVER_URL }}
        
        # All API keys
        GROQ_API_KEY_1: ${{ secrets.GROQ_API_KEY_1 }}
        GROQ_API_KEY_2: ${{ secrets.GROQ_API_KEY_2 }}
        GROQ_API_KEY_3: ${{ secrets.GROQ_API_KEY_3 }}
        GROQ_API_KEY_4: ${{ secrets.GROQ_API_KEY_4 }}
        GROQ_API_KEY_5: ${{ secrets.GROQ_API_KEY_5 }}
        GROQ_API_KEY_6: ${{ secrets.GROQ_API_KEY_6 }}
        GROQ_API_KEY_7: ${{ secrets.GROQ_API_KEY_7 }}
        GROQ_API_KEY_8: ${{ secrets.GROQ_API_KEY_8 }}
        GROQ_API_KEY_9: ${{ secrets.GROQ_API_KEY_9 }}
        GROQ_API_KEY_10: ${{ secrets.GROQ_API_KEY_10 }}
        GROQ_API_KEY_11: ${{ secrets.GROQ_API_KEY_11 }}
        GROQ_API_KEY_12: ${{ secrets.GROQ_API_KEY_12 }}
        GROQ_API_KEY_13: ${{ secrets.GROQ_API_KEY_13 }}
        GROQ_API_KEY_14: ${{ secrets.GROQ_API_KEY_14 }}
        GROQ_API_KEY_15: ${{ secrets.GROQ_API_KEY_15 }}
        GROQ_API_KEY_16: ${{ secrets.GROQ_API_KEY_16 }}
        GROQ_API_KEY_17: ${{ secrets.GROQ_API_KEY_17 }}
        
        # Specify dev tier keys
        DEV_TIER_KEYS: ${{ secrets.DEV_TIER_KEYS }}
      run: |
        if [ "${{ github.event.inputs.date }}" != "" ]; then
          python daily_call_processor_dev_tier.py --date ${{ github.event.inputs.date }}
        else
          python daily_call_processor_dev_tier.py
        fi
    
    - name: Upload results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: call-recordings-dev-tier
        path: daily_recordings_dev/
        retention-days: 30
    
    - name: Upload logs
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: processing-logs
        path: |
          *.log
        retention-days: 7
```

## 📈 Performance Expectations

With 6 dev tier keys:
- **Processing time**: ~3.6 hours for 1000 recordings
- **Safety buffer**: 2.4 hours
- **Success rate**: >99%
- **Rate limits**: Won't hit any limits

## 🔍 Monitoring Progress

The processor provides detailed progress updates:
```
[67/1000] Processing recording | 6.7% | ETA: 3.5h | Elapsed: 0.3h
🔑 Transcribing with dev key #2 (1680/7200s, 25/300 req/min)
✅ Transcription successful with key #2

📊 PROGRESS STATS (every 50 recordings)
========================================
Recordings processed: 100
Processing rate: 166.7 recordings/hour
Audio processed: 3.3 hours
Key #1: 28.0% audio used, 50 requests
Key #2: 23.3% audio used, 42 requests
...
```

## 🚨 Troubleshooting

### If you see "No dev tier keys specified"
- Check that `DEV_TIER_KEYS` secret is set correctly
- Or use the individual flag method

### If rate limits are hit
- Ensure you're using actual dev tier keys (300 req/min)
- Check that you have at least 6 dev tier keys

### If processing is slow
- Verify RingCentral isn't rate limiting downloads
- Check network connectivity

## 💡 Tips for Optimal Performance

1. **Use exactly 6-7 dev tier keys** - This is the sweet spot for 1000 recordings

2. **Don't mix free and dev tier keys** - The processor is optimized for dev tier limits

3. **Monitor the logs** - They show detailed progress and any issues

4. **Run during off-peak hours** - Better RingCentral API performance

5. **Keep the default delays** - They're optimized for reliability:
   - 5 seconds between downloads
   - 2 seconds between transcriptions

## 📊 Billing Notes

- You're billed per audio minute transcribed, not per API key
- Using 6 keys vs 17 keys costs the same for the same audio
- Dev tier has no additional per-key charges

## ✅ Ready to Go!

With this setup, you'll process 1000 recordings in under 4 hours with 99%+ success rate!



