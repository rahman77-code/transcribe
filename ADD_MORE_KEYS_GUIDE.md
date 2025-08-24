# 🔑 Adding More Groq API Keys for 800+ Calls

## 📊 How Many Keys Do You Need?

| Daily Calls | Groq Keys Needed | Processing Time |
|-------------|------------------|-----------------|
| 500-600     | 3-4 keys        | ~14 hours      |
| 700-800     | 5-6 keys        | ~22 hours      |
| 900-1000    | 7-8 keys        | ~23 hours      |

## ✅ For 800 Calls: Use 6 Groq API Keys

### Step 1: Update Your .env File

Add your additional keys like this:

```env
# Your existing keys
GROQ_API_KEY_1=your_groq_api_key_1_here
GROQ_API_KEY_2=your_groq_api_key_2_here  
GROQ_API_KEY_3=your_groq_api_key_3_here

# Add your new keys here
GROQ_API_KEY_4=your_fourth_key_here
GROQ_API_KEY_5=your_fifth_key_here
GROQ_API_KEY_6=your_sixth_key_here
```

### Step 2: Add to GitHub Secrets

Go to your GitHub repository:
1. Settings → Secrets and variables → Actions
2. Add each new key:
   - Name: `GROQ_API_KEY_4`
   - Value: `your_fourth_key_here`
   - Repeat for keys 5 and 6

### Step 3: Update the Workflow

The workflow automatically detects all keys! No changes needed.

## 🚀 Optimized Settings for 800 Calls

The `daily_call_processor_800.py` script uses:
- **40 second download delay** (150 downloads/hour)
- **60 second transcription delay** (60 transcriptions/hour)
- **Smart key rotation** to maximize usage
- **Automatic key reset** after 1 hour

## 📈 What Happens During Processing

```
6:00 PM - Start processing
↓
Hour 1-4: Keys 1-3 used heavily
Hour 5-8: Keys 4-6 take over
Hour 9-12: Keys 1-3 reset and available again
Hour 13-16: Keys 4-6 reset and continue
Hour 17-22: All keys working in rotation
↓
4:00 PM Next Day - Complete!
```

## 🎯 Getting More Groq API Keys

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up with different email addresses
3. Each account gets a free API key
4. Or upgrade to paid tier for higher limits

## 💡 Pro Tips

### For Even Higher Volume (1000+ calls)
- Use 8-10 API keys
- Consider reducing delays to 35s/50s
- Or split processing across 2 GitHub workflows

### Monitor Key Usage
The logs show which keys are being used:
```
🔑 Using API key #1 (3200/6500s used)
🔑 Using API key #2 (2800/6500s used)
```

### If You Hit Limits
The script automatically:
- Waits for keys to reset
- Rotates to available keys
- Continues where it left off

## 🔧 Test Your Setup

Run this to verify all keys are loaded:
```bash
python test_keys.py
```

## 📝 Example .env for 800 Calls

```env
# RingCentral
RC_CLIENT_ID=VNKRmCCWukXcPadmaLZoMu
RC_CLIENT_SECRET=37zo0FbARv5fcHIDHyh9485r2EA57ulqTdo1znecBZwQ
RC_JWT=eyJraWQiOiI4NzYy...

# 6 Groq Keys for 800 calls
GROQ_API_KEY_1=your_groq_api_key_1_here
GROQ_API_KEY_2=your_groq_api_key_2_here
GROQ_API_KEY_3=your_groq_api_key_3_here
GROQ_API_KEY_4=your_groq_api_key_4_here
GROQ_API_KEY_5=your_groq_api_key_5_here
GROQ_API_KEY_6=your_groq_api_key_6_here

# HubSpot
HUBSPOT_ACCESS_TOKEN=your_hubspot_access_token_here
```
