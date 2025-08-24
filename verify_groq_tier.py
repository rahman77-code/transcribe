#!/usr/bin/env python3
"""
Verify if a Groq API key is dev tier or free tier
"""

import requests
import json
import sys


def check_api_key_tier(api_key):
    """Check the tier of a Groq API key"""
    print(f"\n🔍 Checking API key: {api_key[:20]}...")
    
    # Test with chat endpoint to get rate limit info
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        print(f"Status Code: {response.status_code}")
        
        # Print all rate limit headers
        print("\n📊 Rate Limit Headers:")
        for header, value in response.headers.items():
            if 'ratelimit' in header.lower():
                print(f"  {header}: {value}")
        
        if response.status_code == 200:
            # Get daily request limit
            daily_limit = response.headers.get('x-ratelimit-limit-requests', 'Unknown')
            remaining = response.headers.get('x-ratelimit-remaining-requests', 'Unknown')
            
            if daily_limit != "Unknown":
                daily_limit_int = int(daily_limit)
                
                # Calculate requests per minute
                requests_per_minute = daily_limit_int / (24 * 60)
                
                print(f"\n📈 Analysis:")
                print(f"  Daily limit: {daily_limit} requests")
                print(f"  Remaining today: {remaining} requests")
                print(f"  Calculated rate: ~{requests_per_minute:.0f} requests/minute")
                
                # Determine tier
                if requests_per_minute >= 300:
                    print(f"\n✅ This is a DEV TIER key! (300+ req/min)")
                    return "dev"
                elif requests_per_minute >= 20:
                    print(f"\n⚠️  This is a FREE TIER key (20 req/min)")
                    return "free"
                else:
                    print(f"\n❓ Unknown tier ({requests_per_minute:.0f} req/min)")
                    return "unknown"
            
        elif response.status_code == 401:
            print("\n❌ Invalid API key - Authentication failed")
            return "invalid"
        elif response.status_code == 429:
            print("\n⚠️  Rate limit already exceeded")
            return "rate_limited"
        else:
            print(f"\n❌ Error: {response.text}")
            return "error"
            
    except Exception as e:
        print(f"\n❌ Error checking key: {e}")
        return "error"


def test_audio_endpoint(api_key):
    """Test the audio transcription endpoint"""
    print(f"\n🎤 Testing audio transcription endpoint...")
    
    # We'll test with a tiny audio file request to see the response
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    # Create a minimal valid audio file (tiny WAV header)
    # This is just to test the endpoint, not actually transcribe
    wav_header = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    
    files = {
        'file': ('test.wav', wav_header, 'audio/wav')
    }
    data = {
        'model': 'whisper-large-v3-turbo',
        'response_format': 'json'
    }
    
    try:
        response = requests.post(url, headers=headers, files=files, data=data)
        
        print(f"Audio endpoint status: {response.status_code}")
        
        # Check audio-specific rate limits if available
        for header, value in response.headers.items():
            if 'ratelimit' in header.lower():
                print(f"  {header}: {value}")
                
    except Exception as e:
        print(f"Audio endpoint test error: {e}")


def main():
    print("🚀 Groq API Key Tier Checker")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        # API key provided as argument
        api_key = sys.argv[1]
    else:
        # Ask for API key
        api_key = input("\nEnter your Groq API key: ").strip()
    
    if not api_key:
        print("❌ No API key provided")
        return
    
    # Check the key tier
    tier = check_api_key_tier(api_key)
    
    # Test audio endpoint
    if tier in ["dev", "free"]:
        test_audio_endpoint(api_key)
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 SUMMARY")
    print("=" * 50)
    
    if tier == "dev":
        print("✅ You have a DEV TIER key!")
        print("   - 300 requests/minute")
        print("   - Can process 1000+ recordings in 3.6 hours")
        print("   - Ready for high-volume transcription!")
    elif tier == "free":
        print("⚠️  You have a FREE TIER key")
        print("   - 20 requests/minute") 
        print("   - Can process ~600-700 recordings in 6 hours")
        print("   - Consider upgrading or using multiple keys")
    else:
        print("❌ Could not determine key tier")
        print("   Please check your API key and try again")
    
    print("\n💡 Tips:")
    print("- If you expected dev tier, make sure you're creating keys")
    print("  under the ORGANIZATION account, not your personal account")
    print("- Check console.groq.com and switch to the organization context")


if __name__ == "__main__":
    main()



