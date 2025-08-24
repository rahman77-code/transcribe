#!/usr/bin/env python3
"""
Quick test for a single Groq API key to verify tier
"""

import requests
import sys

def test_key(api_key):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        daily_limit = int(response.headers.get('x-ratelimit-limit-requests', '0'))
        requests_per_minute = daily_limit / (24 * 60)
        
        print(f"Daily limit: {daily_limit:,} requests")
        print(f"Rate: ~{requests_per_minute:.0f} requests/minute")
        
        if requests_per_minute >= 300:
            print("✅ DEV TIER KEY! Ready for 1000+ recordings!")
        else:
            print("⚠️ Still showing free tier limits")
            print("\nPossible reasons:")
            print("- Key was created before tier upgrade")
            print("- Tier change hasn't propagated yet (wait 5-10 min)")
            print("- Try creating a brand new key")
    else:
        print(f"❌ Error: {response.status_code}")

if __name__ == "__main__":
    key = input("Paste your NEW API key: ").strip()
    if key:
        test_key(key)



