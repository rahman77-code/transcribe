"""
Test the safe processor configuration
Run this before deploying to GitHub to ensure everything works
"""
import os
from datetime import datetime, timedelta
from daily_call_processor_safe import SafeDailyCallProcessor
import sys

def test_configuration():
    """Test that all required environment variables are set"""
    print("🔍 Testing configuration...\n")
    
    required_vars = {
        'RC_CLIENT_ID': 'RingCentral Client ID',
        'RC_CLIENT_SECRET': 'RingCentral Client Secret', 
        'RC_JWT': 'RingCentral JWT Token',
        'GROQ_API_KEY_1': 'First Groq API Key'
    }
    
    optional_vars = {
        'GROQ_API_KEY_2': 'Second Groq API Key',
        'GROQ_API_KEY_3': 'Third Groq API Key',
        'HUBSPOT_ACCESS_TOKEN': 'HubSpot Access Token'
    }
    
    all_good = True
    
    # Check required vars
    print("Required Environment Variables:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            masked_value = value[:10] + "..." + value[-4:] if len(value) > 20 else value
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"❌ {var}: NOT SET - {desc}")
            all_good = False
    
    print("\nOptional Environment Variables:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            masked_value = value[:10] + "..." + value[-4:] if len(value) > 20 else value
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"⚠️  {var}: Not set (optional)")
    
    return all_good

def test_authentication():
    """Test RingCentral authentication"""
    print("\n🔐 Testing RingCentral authentication...")
    
    try:
        processor = SafeDailyCallProcessor()
        platform = processor.authenticate()
        
        if platform:
            print("✅ Authentication successful!")
            return True
        else:
            print("❌ Authentication failed!")
            return False
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False

def estimate_processing_time():
    """Estimate how long processing will take"""
    print("\n⏱️  Processing Time Estimates:")
    
    processor = SafeDailyCallProcessor()
    
    # Show delay settings
    print(f"\nSafety Delays:")
    print(f"- Download delay: {processor.download_delay} seconds between recordings")
    print(f"- Transcription delay: {processor.transcription_delay} seconds between transcriptions")
    print(f"- Total per recording: {processor.download_delay + processor.transcription_delay} seconds")
    
    # Calculate for different volumes
    print(f"\nTime estimates by volume:")
    for count in [100, 200, 500, 1000]:
        total_seconds = count * (processor.download_delay + processor.transcription_delay)
        hours = total_seconds / 3600
        print(f"- {count} recordings: ~{hours:.1f} hours")
    
    # API key capacity
    print(f"\nAPI Key Capacity:")
    print(f"- Keys available: {len(processor.groq_api_keys)}")
    print(f"- Max audio per key per hour: {processor.max_seconds_per_key_per_hour/60:.0f} minutes")
    print(f"- Total capacity per hour: {len(processor.groq_api_keys) * processor.max_seconds_per_key_per_hour/60:.0f} minutes")

def main():
    print("="*60)
    print("🧪 SAFE Daily Call Processor - Configuration Test")
    print("="*60)
    
    # Test configuration
    config_ok = test_configuration()
    
    if not config_ok:
        print("\n❌ Configuration incomplete. Please set all required environment variables.")
        sys.exit(1)
    
    # Test authentication
    auth_ok = test_authentication()
    
    if not auth_ok:
        print("\n❌ Authentication failed. Check your RingCentral credentials.")
        sys.exit(1)
    
    # Show estimates
    estimate_processing_time()
    
    print("\n" + "="*60)
    print("✅ All tests passed! Ready for deployment to GitHub Actions.")
    print("\n📋 Next steps:")
    print("1. Push your code to GitHub")
    print("2. Add secrets to GitHub repository settings")
    print("3. Enable GitHub Actions")
    print("4. The workflow will run automatically every night!")
    print("="*60)

if __name__ == "__main__":
    main()
