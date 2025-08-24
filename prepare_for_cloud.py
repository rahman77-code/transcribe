"""
Prepare the project for cloud deployment
"""
import os
import json
import shutil

def create_gitignore():
    """Create .gitignore for cloud deployment"""
    gitignore_content = """# Environment variables
.env
*.env
env.txt
env_*.txt

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# Logs
*.log
daily_processor_scheduled.log

# Local recordings (don't upload to cloud)
daily_recordings/
recordings/
*.mp3
*.wav
*.m4a

# Transcriptions (keep in cloud storage instead)
*_transcription.txt

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
"""
    with open('.gitignore', 'w') as f:
        f.write(gitignore_content)
    print("✅ Created .gitignore")

def create_procfile():
    """Create Procfile for Heroku"""
    with open('Procfile', 'w') as f:
        f.write("worker: python daily_call_processor_multi_key.py\n")
    print("✅ Created Procfile for Heroku")

def create_runtime_txt():
    """Specify Python version for cloud platforms"""
    with open('runtime.txt', 'w') as f:
        f.write("python-3.10.12\n")
    print("✅ Created runtime.txt")

def create_app_json():
    """Create app.json for Heroku Deploy Button"""
    app_config = {
        "name": "RingCentral Call Processor",
        "description": "Automatically download and transcribe RingCentral call recordings daily",
        "keywords": ["ringcentral", "transcription", "automation"],
        "env": {
            "RC_CLIENT_ID": {
                "description": "Your RingCentral Client ID",
                "required": True
            },
            "RC_CLIENT_SECRET": {
                "description": "Your RingCentral Client Secret",
                "required": True
            },
            "RC_JWT": {
                "description": "Your RingCentral JWT Token",
                "required": True
            },
            "GROQ_API_KEY_1": {
                "description": "First Groq API Key",
                "required": True
            },
            "GROQ_API_KEY_2": {
                "description": "Second Groq API Key",
                "required": False
            },
            "GROQ_API_KEY_3": {
                "description": "Third Groq API Key",
                "required": False
            },
            "HUBSPOT_ACCESS_TOKEN": {
                "description": "HubSpot Access Token (optional)",
                "required": False
            }
        },
        "formation": {
            "worker": {
                "quantity": 1,
                "size": "standard-1x"
            }
        },
        "addons": [
            {
                "plan": "scheduler:standard"
            }
        ]
    }
    
    with open('app.json', 'w') as f:
        json.dump(app_config, f, indent=2)
    print("✅ Created app.json for Heroku")

def create_dockerignore():
    """Create .dockerignore for container deployments"""
    with open('.dockerignore', 'w') as f:
        f.write(""".env
*.env
daily_recordings/
*.mp3
*.log
__pycache__/
.git/
.github/
""")
    print("✅ Created .dockerignore")

def create_simple_cloud_runner():
    """Create a simple script for cloud platforms"""
    cloud_script = '''#!/usr/bin/env python3
"""
Cloud-optimized runner for the daily call processor
Handles both scheduled runs and one-time executions
"""
import os
import sys
from datetime import datetime, timedelta
from daily_call_processor_multi_key import DailyCallProcessorMultiKey

def main():
    # Check if we should run as scheduler or one-time
    run_mode = os.environ.get('RUN_MODE', 'once')
    
    processor = DailyCallProcessorMultiKey()
    
    if run_mode == 'scheduler':
        print("Starting in scheduler mode...")
        processor.run_scheduled()
    else:
        # Run once for yesterday's calls
        yesterday = datetime.now().date() - timedelta(days=1)
        print(f"Processing calls for {yesterday}")
        processor.process_daily_calls(yesterday)

if __name__ == "__main__":
    main()
'''
    
    with open('cloud_runner.py', 'w') as f:
        f.write(cloud_script)
    print("✅ Created cloud_runner.py")

def main():
    print("🚀 Preparing project for cloud deployment...\n")
    
    create_gitignore()
    create_procfile()
    create_runtime_txt()
    create_app_json()
    create_dockerignore()
    create_simple_cloud_runner()
    
    print("\n✨ Project is ready for cloud deployment!")
    print("\n📋 Quick deployment options:")
    print("\n1. GitHub Actions (FREE - Recommended):")
    print("   - Push this code to GitHub")
    print("   - Go to Settings > Secrets > Actions")
    print("   - Add your API keys as secrets")
    print("   - The workflow will run daily automatically")
    
    print("\n2. Railway (Easy & Fast):")
    print("   - Run: railway login")
    print("   - Run: railway init")
    print("   - Run: railway up")
    
    print("\n3. Heroku (Free tier):")
    print("   - Run: heroku create your-app-name")
    print("   - Run: git push heroku main")
    print("   - Add scheduler addon in Heroku dashboard")

if __name__ == "__main__":
    main()
