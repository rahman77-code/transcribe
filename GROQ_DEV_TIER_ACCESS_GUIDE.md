# 🔑 How to Access Dev Tier API Keys on Groq Cloud

## The Problem
You've accepted an invite to a dev tier organization, but your API keys are still showing free tier limits. This happens because:
- API keys created under your personal account remain free tier
- You need to create API keys under the ORGANIZATION account that has dev tier

## 🚀 Step-by-Step Solution

### 1. Access the Organization Account

1. Go to [console.groq.com](https://console.groq.com)
2. Log in with your credentials
3. **IMPORTANT**: Look for the account/organization switcher (usually top-right corner)
   - It might show your personal email/username
   - Click on it to see a dropdown
   - Select the ORGANIZATION that invited you (it should have a different name)

### 2. Verify You're in the Right Account

Once switched to the organization:
- Check the URL - it might show the organization name
- Look for "Organization" or "Team" indicators
- The billing/subscription page should show "Developer Tier" or "Dev Tier"

### 3. Create API Keys Under the Organization

1. Navigate to **API Keys** section
2. Click **"Create API Key"** or **"+ New API Key"**
3. Give it a descriptive name (e.g., "Dev Tier Key 1")
4. **IMPORTANT**: Make sure you're still in the organization context
5. Copy the key immediately (you won't see it again)

### 4. Verify the Keys Are Dev Tier

Test your new key:
```bash
curl https://api.groq.com/openai/v1/chat/completions \
  -H "Authorization: Bearer YOUR_NEW_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3-8b-8192",
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }' \
  -i
```

Look for the rate limit headers in the response:
- `x-ratelimit-limit-requests`: Should show a much higher number for dev tier
- Dev tier = ~432,000 requests/day (300/min)
- Free tier = ~28,800 requests/day (20/min)

## 🔍 Common Issues

### Can't Find Organization Switcher?
- Some UI designs have it in:
  - Top-right corner (profile dropdown)
  - Left sidebar
  - Under Settings → Organizations

### Still Showing Personal Account?
- Log out completely
- Use the invitation link again
- Make sure you accept any pending invitations

### No "Create API Key" Option?
- You might not have the right permissions
- Contact the organization admin to grant API key creation permissions

## 📝 What Your Dev Tier Keys Should Look Like

When properly created under a dev tier organization:
- Rate limit: 300 requests/minute
- Audio transcription: Same 7,200 seconds/hour per key
- Much faster processing capability

## 🚨 Important Notes

1. **Don't Mix Keys**: Keep organization keys separate from personal keys
2. **Billing**: The organization pays for usage, not you
3. **Permissions**: You might need specific permissions to create keys

## 💡 Quick Check

Run this Python script with a new key:
```python
import requests

api_key = "YOUR_NEW_KEY_HERE"
url = "https://api.groq.com/openai/v1/chat/completions"

response = requests.post(url, 
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10
    })

if response.status_code == 200:
    limit = response.headers.get('x-ratelimit-limit-requests', 'Unknown')
    print(f"Daily request limit: {limit}")
    
    if int(limit) > 400000:
        print("✅ This is a DEV TIER key!")
    else:
        print("⚠️ This appears to be a free tier key")
```

## Need More Help?

1. Check if you have any pending invitations in your email
2. Contact the person who invited you to the organization
3. They might need to grant you API key creation permissions
4. Or they might need to create the keys for you



