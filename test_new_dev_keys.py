#!/usr/bin/env python3
"""
Quick test script for your new dev tier keys
"""

import requests
import time

# Your dev tier keys (replace with your actual keys)
DEV_KEYS = [
    "gsk_YOUR_FIRST_GROQ_API_KEY_HERE",
    "gsk_YOUR_SECOND_GROQ_API_KEY_HERE", 
    "gsk_YOUR_THIRD_GROQ_API_KEY_HERE",
    "gsk_YOUR_FOURTH_GROQ_API_KEY_HERE",
    "gsk_YOUR_FIFTH_GROQ_API_KEY_HERE",
    "gsk_YOUR_SIXTH_GROQ_API_KEY_HERE"
]


def test_key(api_key, index):
    """Test a single API key"""
    print(f"\n🔍 Testing key #{index + 1}...")
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": "Say 'test'"}],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        
        if response.status_code == 200:
            # Check rate limit headers
            rpm_limit = response.headers.get('x-ratelimit-limit-requests', 'Unknown')
            rpm_remaining = response.headers.get('x-ratelimit-remaining-requests', 'Unknown')
            
            # Determine tier
            if rpm_limit != "Unknown":
                try:
                    # Convert daily limit to per-minute limit
                    daily_limit = int(rpm_limit)
                    per_minute = daily_limit / (24 * 60)
                    
                    if per_minute >= 300:
                        tier = "✅ DEV TIER (300 req/min)"
                    elif per_minute >= 20:
                        tier = "⚠️ Free Tier (20 req/min)"
                    else:
                        tier = f"Unknown ({per_minute:.0f} req/min)"
                except:
                    tier = "Unknown"
            else:
                tier = "Unknown"
            
            print(f"  Status: ✅ Active")
            print(f"  Tier: {tier}")
            print(f"  Daily limit: {rpm_limit} requests")
            print(f"  Remaining today: {rpm_remaining}")
            return True, tier
            
        else:
            print(f"  Status: ❌ Error {response.status_code}")
            print(f"  Message: {response.text[:100]}...")
            return False, "Error"
            
    except Exception as e:
        print(f"  Status: ❌ Failed")
        print(f"  Error: {str(e)}")
        return False, "Failed"


def main():
    print("🚀 Testing Your New Dev Tier Keys")
    print("=" * 50)
    
    all_dev_tier = True
    working_keys = 0
    
    for i, key in enumerate(DEV_KEYS):
        success, tier = test_key(key, i)
        
        if success:
            working_keys += 1
            if "DEV TIER" not in tier:
                all_dev_tier = False
        
        # Small delay between tests
        if i < len(DEV_KEYS) - 1:
            time.sleep(1)
    
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"Total keys tested: {len(DEV_KEYS)}")
    print(f"Working keys: {working_keys}")
    print(f"All dev tier: {'✅ YES' if all_dev_tier and working_keys == len(DEV_KEYS) else '❌ NO'}")
    
    if working_keys == len(DEV_KEYS) and all_dev_tier:
        print("\n✅ Perfect! All 6 keys are working dev tier keys!")
        print("🎯 You can process 1000+ recordings in ~3.6 hours!")
        print("\n📝 Next steps:")
        print("1. Add these keys to GitHub Secrets (see ADD_NEW_DEV_KEYS.md)")
        print("2. Set DEV_TIER_KEYS=1,2,3,4,5,6 in GitHub Secrets")
        print("3. Run the workflow!")
    else:
        print("\n⚠️ Some keys may have issues. Please check the output above.")
    
    print("\n⚠️ SECURITY WARNING: Delete this test file after use!")
    
    # Offer to delete this file
    response = input("\n🗑️ Delete this test file now for security? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        import os
        try:
            os.remove(__file__)
            print("✅ File deleted successfully!")
        except Exception as e:
            print(f"❌ Could not delete file: {e}")
            print("Please delete test_new_dev_keys.py manually!")


if __name__ == "__main__":
    main()
