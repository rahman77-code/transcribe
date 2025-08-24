"""
Diagnose RingCentral account structure and find the right endpoint
"""

import os
from ringcentral import SDK
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

def diagnose_account():
    # RingCentral credentials
    config = {
        "clientId": "0gAEMMaAIb9aVRHMOSW5se",
        "clientSecret": "5TQ84XRt1eNfG90l558cie9TWqoVHQTcZfRT7zHJXZA2",
        "server": "https://platform.ringcentral.com"
    }
    
    JWT_TOKEN = os.getenv("RINGCENTRAL_JWT_TOKEN")
    
    # Initialize SDK
    sdk = SDK(config["clientId"], config["clientSecret"], config["server"])
    platform = sdk.platform()
    
    # Authenticate
    try:
        platform.login(jwt=JWT_TOKEN)
        print("✅ Successfully authenticated with new JWT token\n")
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return
    
    # Test 1: Check account structure
    print("1️⃣ Checking account structure:")
    try:
        response = platform.get('/restapi/v1.0/account/~')
        data = response.json_dict()
        
        print(f"   Account ID: {data.get('id')}")
        print(f"   Main Number: {data.get('mainNumber')}")
        print(f"   Status: {data.get('status')}")
        
        service_info = data.get('serviceInfo', {})
        print(f"   Service Plan: {service_info.get('servicePlan', {}).get('name', 'Unknown')}")
        
        # Check if multi-site
        if 'multiSiteEnabled' in service_info:
            print(f"   Multi-site: {service_info.get('multiSiteEnabled')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Try company-wide call log
    print("\n2️⃣ Testing company-wide call log:")
    try:
        response = platform.get('/restapi/v1.0/account/~/call-log?perPage=5&view=Detailed')
        data = response.json_dict()
        
        records = data.get('records', [])
        total = data.get('paging', {}).get('totalElements', 0)
        
        print(f"   Total company-wide records: {total}")
        print(f"   Records returned: {len(records)}")
        
        if records:
            print("\n   Sample record:")
            record = records[0]
            print(f"   - Time: {record.get('startTime')}")
            print(f"   - Extension: {record.get('extension', {}).get('extensionNumber', 'Unknown')}")
            print(f"   - Has recording: {'recording' in record}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: List all extensions
    print("\n3️⃣ Listing extensions:")
    try:
        response = platform.get('/restapi/v1.0/account/~/extension?perPage=10')
        data = response.json_dict()
        
        extensions = data.get('records', [])
        print(f"   Total extensions: {len(extensions)}")
        
        for ext in extensions[:5]:
            ext_number = ext.get('extensionNumber', 'Unknown')
            ext_name = ext.get('name', 'Unknown')
            ext_type = ext.get('type', 'Unknown')
            ext_status = ext.get('status', 'Unknown')
            print(f"   - Ext {ext_number}: {ext_name} ({ext_type}) - {ext_status}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: Try specific date with company endpoint
    print("\n4️⃣ Testing company call log for Aug 12, 2025:")
    try:
        # Use simple date format
        date_from = "2025-08-12"
        date_to = "2025-08-13"
        
        url = f'/restapi/v1.0/account/~/call-log?dateFrom={date_from}&dateTo={date_to}&perPage=100'
        print(f"   URL: {url}")
        
        response = platform.get(url)
        data = response.json_dict()
        
        records = data.get('records', [])
        print(f"   Records found: {len(records)}")
        
        if records:
            recordings = [r for r in records if 'recording' in r]
            print(f"   Records with recordings: {len(recordings)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 5: Try using time parameter
    print("\n5️⃣ Testing with showBlocked parameter:")
    try:
        url = '/restapi/v1.0/account/~/extension/~/call-log?perPage=10&showBlocked=true'
        response = platform.get(url)
        data = response.json_dict()
        
        records = data.get('records', [])
        print(f"   Records with showBlocked: {len(records)}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 6: Check if it's sandbox vs production
    print("\n6️⃣ Environment check:")
    print(f"   Server: {config['server']}")
    print("   This is the PRODUCTION server")
    print("\n   💡 Note: If your account is in sandbox, you need to use:")
    print("      https://platform.devtest.ringcentral.com")

if __name__ == "__main__":
    diagnose_account()
