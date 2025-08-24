"""
Test the new credentials and setup
"""

import os
from datetime import datetime
from ringcentral import SDK
from dotenv import load_dotenv

# Load environment variables
load_dotenv('new_credentials.env')  # Load the new credentials

def test_setup():
    print("🔧 Testing New RingCentral Setup")
    print("=" * 60)
    
    # Show loaded credentials (partially hidden for security)
    client_id = os.getenv("RC_CLIENT_ID")
    client_secret = os.getenv("RC_CLIENT_SECRET")
    jwt_token = os.getenv("RC_JWT")
    
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret[:10]}...")
    print(f"JWT Token: {jwt_token[:50]}..." if jwt_token else "Not found")
    
    # Test authentication
    print("\n🔐 Testing Authentication...")
    
    try:
        sdk = SDK(client_id, client_secret, "https://platform.ringcentral.com")
        platform = sdk.platform()
        platform.login(jwt=jwt_token)
        
        print("✅ Authentication successful!")
        
        # Get extension info
        response = platform.get('/restapi/v1.0/account/~/extension/~')
        data = response.json_dict()
        
        print(f"\n📞 Extension Info:")
        print(f"   Extension ID: {data.get('id')}")
        print(f"   Extension Number: {data.get('extensionNumber')}")
        print(f"   Name: {data.get('name')}")
        
        # Try to get today's call count
        today = datetime.now().strftime('%Y-%m-%d')
        response = platform.get(f'/restapi/v1.0/account/~/call-log?dateFrom={today}&perPage=1')
        data = response.json_dict()
        
        total = data.get('paging', {}).get('totalElements', 0)
        print(f"\n📊 Today's calls so far: {total}")
        
        print("\n✅ All systems ready for daily automation!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease check:")
        print("1. Are the new credentials correct?")
        print("2. Is the JWT token valid?")
        print("3. Are all permissions enabled for the new app?")

if __name__ == "__main__":
    test_setup()

