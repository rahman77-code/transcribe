"""
Test that all Groq API keys are properly loaded
"""
import os
from dotenv import load_dotenv

load_dotenv()

print("🔑 Checking Groq API Keys...")
print("="*50)

keys_found = []

# Check numbered keys
for i in range(1, 11):
    key = os.getenv(f"GROQ_API_KEY_{i}")
    if key:
        masked = key[:10] + "..." + key[-4:]
        print(f"✅ GROQ_API_KEY_{i}: {masked}")
        keys_found.append(key)
    else:
        if i <= 6:  # Recommend 6 for 800 calls
            print(f"❌ GROQ_API_KEY_{i}: Not set (recommended for 800 calls)")
        else:
            print(f"⚠️  GROQ_API_KEY_{i}: Not set (optional)")

# Check single key
single_key = os.getenv("GROQ_API_KEY")
if single_key and single_key not in keys_found:
    print(f"✅ GROQ_API_KEY: {single_key[:10]}...{single_key[-4:]}")
    keys_found.append(single_key)

print("\n" + "="*50)
print(f"📊 Total API Keys Found: {len(keys_found)}")

if len(keys_found) >= 6:
    print("✅ Sufficient keys for 800 calls!")
elif len(keys_found) >= 3:
    print("⚠️  Can handle ~500 calls. Add more keys for 800.")
else:
    print("❌ Need more keys! Add at least 3-6 keys.")

print("\n💡 Capacity Estimate:")
print(f"- With {len(keys_found)} keys: ~{len(keys_found) * 140} calls safely")
print(f"- For 800 calls: Need 6 keys")
print("="*50)
