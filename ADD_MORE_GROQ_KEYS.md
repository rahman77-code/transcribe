# 🔑 How to Add More Groq API Keys

## Current Status
You have 11 Groq API keys configured. The script can handle up to 20 keys.

## To Add More Keys:

### 1. Update Your GitHub Secrets
Go to your repository settings and add:
- `GROQ_API_KEY_12`: `gsk_your_12th_key_here`
- `GROQ_API_KEY_13`: `gsk_your_13th_key_here`
- Continue up to `GROQ_API_KEY_20` if needed

### 2. Update the Python Script
The script automatically loads keys from GROQ_API_KEY_1 to GROQ_API_KEY_20.
No code changes needed!

### 3. Update Local .env (for testing)
Add to your `.env` file:
```
GROQ_API_KEY_12=your_12th_key_here
GROQ_API_KEY_13=your_13th_key_here
# ... and so on
```

## 📊 Capacity with More Keys:

| Keys | Processing Capacity | Notes |
|------|-------------------|-------|
| 11 keys | ~1,200 calls/day | Current setup |
| 15 keys | ~1,500 calls/day | Better rate limit distribution |
| 20 keys | ~2,000 calls/day | Maximum recommended |

## 🎯 Improved Rate Limit Handling

The updated script now includes:
1. **60-second cooldown** after rate limits
2. **5-minute blacklist** for rate-limited keys
3. **Smart key rotation** based on usage history
4. **Increased delays** between transcriptions (10s)

This should significantly reduce rate limit errors!
