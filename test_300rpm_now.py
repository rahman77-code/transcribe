"""
Quick test script to verify 300 RPM processing works
Run this to test with your 6 API keys
"""
import os
import sys

# Your 6 Groq API keys - add them here
GROQ_KEYS = [
    "YOUR_KEY_1_HERE",  # Replace with your actual key
    "YOUR_KEY_2_HERE",  # Replace with your actual key
    "YOUR_KEY_3_HERE",  # Replace with your actual key
    "YOUR_KEY_4_HERE",  # Replace with your actual key
    "YOUR_KEY_5_HERE",  # Replace with your actual key
    "YOUR_KEY_6_HERE",  # Replace with your actual key
]

# Set environment variables
os.environ["RC_CLIENT_ID"] = "VNKRmCCWukXcPadmaLZoMu"
os.environ["RC_CLIENT_SECRET"] = "37zo0FbARv5fcHIDHyh9485r2EA57ulqTdo1znecBZwQ"
os.environ["RC_JWT"] = "eyJraWQiOiI4NzYyZjU5OGQwNTk0NGRiODZiZjVjYTk3ODA0NzYwOCIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJhdWQiOiJodHRwczovL3BsYXRmb3JtLnJpbmdjZW50cmFsLmNvbS9yZXN0YXBpL29hdXRoL3Rva2VuIiwic3ViIjoiNjMzMjQ0MDQwMDgiLCJpc3MiOiJodHRwczovL3BsYXRmb3JtLnJpbmdjZW50cmFsLmNvbSIsImV4cCI6Mzg5NTE2Nzk4NCwiaWF0IjoxNzQ3Njg0MzM3LCJqdGkiOiJCbG1KZ1JVblNCU0Fld2NMNDhvdEZRIn0.Cx2UAGelOzaQkwcqt3c1Ijo_-5gDjO_i7cJfPEc6fJGRUxMwkhYwQGOG7-A9_wh2woaiEdVHMsoNyMgh9_0pk94_Hov8hjroMlN0d685bOYMciEsynWLvFZG74JHlyLj8a4uTmlk_EwVX3Eos8_mQNr4uc8sZhGzhLkGyBqwjBQsWdRY0niemFWvtep8qPvjp2KkEwEonH7vOFdodUB__7D-6YR6tn5OV_kjV2EzH8yBSGzF8y75acf9HcfRIMoTe7z2fF8XtYqdX0sn9c-b16yFc05atYrW5CEuctctGZMzR4AvizSZbDSg0OZn9IpL3Um0S8ALc00DTCaB9NfA6A"
os.environ["RC_SERVER_URL"] = "https://platform.ringcentral.com"

# Set Groq API keys
for i, key in enumerate(GROQ_KEYS, 1):
    if key != "YOUR_KEY_" + str(i) + "_HERE":
        os.environ[f"GROQ_API_KEY_{i}"] = key

# Check if keys are set
keys_set = sum(1 for k in GROQ_KEYS if "YOUR_KEY" not in k)
if keys_set == 0:
    print("❌ ERROR: Please add your Groq API keys to this file first!")
    print("Edit test_300rpm_now.py and replace YOUR_KEY_X_HERE with your actual keys")
    sys.exit(1)

print(f"✅ {keys_set} Groq API keys configured")
print(f"⚡ Total capacity: {keys_set} × 300 = {keys_set * 300} RPM")
print(f"📊 Expected time for 700 calls: ~{700 / (keys_set * 300) * 60:.0f} seconds\n")

# Import and run the processor
try:
    from daily_call_processor_300rpm import OptimizedCallProcessor
    processor = OptimizedCallProcessor()
    
    # Use yesterday's date by default
    from datetime import datetime, timedelta, timezone
    central_tz = timezone(timedelta(hours=-6))
    yesterday = datetime.now(central_tz) - timedelta(days=1)
    target_date = yesterday.strftime("%Y-%m-%d")
    
    print(f"🎯 Processing recordings for: {target_date}")
    processor.run(target_date)
    
except ImportError:
    print("❌ ERROR: daily_call_processor_300rpm.py not found!")
    print("Make sure you're in the correct directory")
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
