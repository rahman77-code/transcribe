#!/usr/bin/env python3
"""
Test script to verify dev tier API keys before running the full processor
"""

import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_groq_key(api_key: str, key_number: int) -> dict:
    """Test a single Groq API key"""
    print(f"\n🔍 Testing key #{key_number}...")
    
    # Test with a simple text completion first
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
            # Get rate limit headers
            rpm_limit = response.headers.get('x-ratelimit-limit-requests', 'Unknown')
            rpm_remaining = response.headers.get('x-ratelimit-remaining-requests', 'Unknown')
            
            # Determine tier based on rate limit
            tier = "Unknown"
            if rpm_limit != "Unknown":
                rpm_limit_int = int(rpm_limit)
                if rpm_limit_int >= 14400:  # 14,400 requests per day = 10 rpm (free tier)
                    tier = "Free Tier"
                elif rpm_limit_int >= 432000:  # 432,000 requests per day = 300 rpm (dev tier)
                    tier = "Dev Tier ✅"
                else:
                    tier = f"Custom ({rpm_limit_int} requests/day)"
            
            return {
                "status": "Active",
                "tier": tier,
                "rate_limit": f"{rpm_limit} requests/day",
                "remaining": rpm_remaining
            }
        elif response.status_code == 401:
            return {"status": "Invalid", "error": "Authentication failed"}
        elif response.status_code == 429:
            return {"status": "Rate Limited", "error": "Already at rate limit"}
        else:
            return {"status": "Error", "error": f"Status {response.status_code}"}
            
    except Exception as e:
        return {"status": "Error", "error": str(e)}


def main():
    print("🚀 Dev Tier API Key Tester")
    print("=" * 50)
    
    # Load dev tier configuration
    dev_tier_numbers = os.getenv("DEV_TIER_KEYS", "")
    
    if dev_tier_numbers:
        key_numbers = [int(n.strip()) for n in dev_tier_numbers.split(",") if n.strip()]
        print(f"📋 Testing keys specified in DEV_TIER_KEYS: {key_numbers}")
    else:
        # Check all available keys up to 30
        print("⚠️  No DEV_TIER_KEYS specified, checking all available keys...")
        key_numbers = []
        for i in range(1, 31):
            if os.getenv(f"GROQ_API_KEY_{i}"):
                key_numbers.append(i)
        
        if not key_numbers:
            print("❌ No API keys found in environment!")
            return
        
        print(f"📋 Found keys in positions: {key_numbers}")
    
    # Test each key
    results = {}
    dev_tier_count = 0
    free_tier_count = 0
    
    for num in key_numbers:
        key = os.getenv(f"GROQ_API_KEY_{num}")
        if key:
            result = test_groq_key(key, num)
            results[num] = result
            
            if "Dev Tier" in result.get("tier", ""):
                dev_tier_count += 1
            elif "Free Tier" in result.get("tier", ""):
                free_tier_count += 1
        else:
            results[num] = {"status": "Not Found", "error": "Key not in environment"}
    
    # Display results
    print("\n📊 Test Results")
    print("=" * 50)
    
    for num, result in results.items():
        status_icon = "✅" if result["status"] == "Active" else "❌"
        print(f"\nKey #{num}: {status_icon} {result['status']}")
        
        if result["status"] == "Active":
            print(f"  Tier: {result['tier']}")
            print(f"  Rate Limit: {result['rate_limit']}")
        else:
            print(f"  Error: {result.get('error', 'Unknown')}")
    
    # Summary
    print("\n📈 Summary")
    print("=" * 50)
    print(f"Total keys tested: {len(results)}")
    print(f"Dev tier keys: {dev_tier_count}")
    print(f"Free tier keys: {free_tier_count}")
    print(f"Failed/Invalid keys: {len(results) - dev_tier_count - free_tier_count}")
    
    # Recommendations
    print("\n💡 Recommendations")
    print("=" * 50)
    
    if dev_tier_count >= 6:
        print("✅ You have enough dev tier keys to process 1000+ recordings!")
        print("   You can run: python daily_call_processor_dev_tier.py")
    elif dev_tier_count >= 5:
        print("⚠️  You have the minimum required dev tier keys (5).")
        print("   Consider upgrading 1-2 more keys for safety buffer.")
    else:
        print("❌ You don't have enough dev tier keys.")
        print(f"   Current: {dev_tier_count}, Required: 5-6")
        print("   Please upgrade more keys to dev tier.")
    
    # Show example configuration
    if dev_tier_count > 0:
        dev_keys = [num for num, result in results.items() 
                   if "Dev Tier" in result.get("tier", "")]
        print(f"\n📝 Add this to your GitHub Secrets:")
        print(f"   DEV_TIER_KEYS={','.join(map(str, dev_keys))}")


if __name__ == "__main__":
    main()
