"""
Helper script to update JWT token in .env file
"""

import os
import re

def update_jwt_token():
    print("🔑 JWT Token Updater")
    print("=" * 60)
    print("\nThis script will help you update your JWT token in the .env file")
    print("\n📋 Steps you should have completed:")
    print("1. ✓ Added all Call Recording permissions to your app")
    print("2. ✓ Deleted the old JWT token in RingCentral Developer Console")
    print("3. ✓ Generated a new JWT token with updated permissions")
    print("4. ✓ Copied the new JWT token")
    
    print("\n" + "=" * 60)
    print("Paste your new JWT token below (it should start with 'eyJ'):")
    print("Press Enter twice when done.")
    print("=" * 60 + "\n")
    
    # Read multi-line input (JWT tokens can be long)
    lines = []
    while True:
        line = input()
        if line:
            lines.append(line)
        else:
            if lines:  # If we have content and get empty line, stop
                break
    
    new_token = ''.join(lines).strip()
    
    # Validate token format
    if not new_token.startswith('eyJ'):
        print("\n❌ Error: JWT tokens should start with 'eyJ'")
        print("   Please make sure you copied the entire token.")
        return False
    
    print(f"\n✅ Token received (length: {len(new_token)} characters)")
    
    # Read current .env file
    try:
        with open('.env', 'r') as f:
            env_content = f.read()
    except FileNotFoundError:
        print("❌ Error: .env file not found!")
        return False
    
    # Find and replace JWT token
    pattern = r'RINGCENTRAL_JWT_TOKEN=.*'
    replacement = f'RINGCENTRAL_JWT_TOKEN={new_token}'
    
    if 'RINGCENTRAL_JWT_TOKEN=' in env_content:
        new_content = re.sub(pattern, replacement, env_content)
        print("✅ Found existing JWT token in .env file")
    else:
        # Add it if not present
        new_content = env_content.rstrip() + f'\n\n# RingCentral JWT Token\n{replacement}\n'
        print("✅ Adding JWT token to .env file")
    
    # Backup old .env
    backup_name = '.env.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(backup_name, 'w') as f:
        f.write(env_content)
    print(f"📄 Backup saved: {backup_name}")
    
    # Write new .env
    with open('.env', 'w') as f:
        f.write(new_content)
    
    print("\n✅ Successfully updated .env file with new JWT token!")
    print("\n🚀 Next steps:")
    print("1. Run: python fetch_recordings_final.py 2025-08-12 30")
    print("2. Your recordings should now be accessible!")
    
    return True

if __name__ == "__main__":
    from datetime import datetime
    update_jwt_token()
