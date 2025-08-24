import os
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from ringcentral import SDK
from transcribe_audio import transcribe_audio, save_transcription
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class RingCentralJWTRecordingFetcher:
    def __init__(self, client_id, client_secret, server, jwt_token):
        """
        Initialize RingCentral SDK with JWT authentication
        
        Args:
            client_id (str): RingCentral app client ID
            client_secret (str): RingCentral app client secret
            server (str): RingCentral server URL
            jwt_token (str): JWT token for authentication
        """
        self.sdk = SDK(client_id, client_secret, server)
        self.platform = self.sdk.platform()
        self.jwt_token = jwt_token
        
    def authenticate(self):
        """Authenticate with RingCentral API using JWT"""
        try:
            self.platform.login(jwt=self.jwt_token)
            print("✅ Successfully authenticated with RingCentral using JWT")
            return True
        except Exception as e:
            print(f"❌ JWT Authentication failed: {e}")
            print("\n📋 To fix this:")
            print("1. Make sure JWT auth is enabled in your app")
            print("2. Generate JWT credentials from the RingCentral Developer Console")
            print("3. Add the JWT token to your .env file")
            return False
    
    def fetch_call_logs(self, date_str):
        """
        Fetch call logs for a specific date
        
        Args:
            date_str (str): Date in format 'YYYY-MM-DD'
        
        Returns:
            list: Call log records
        """
        try:
            # Parse the date and create date range
            date = datetime.strptime(date_str, '%Y-%m-%d')
            date_from = date.strftime('%Y-%m-%dT00:00:00.000Z')
            date_to = (date + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00.000Z')
            
            print(f"📅 Fetching call logs for {date_str}...")
            
            # Make API request
            response = self.platform.get(
                '/restapi/v1.0/account/~/extension/~/call-log?'
                f'dateFrom={date_from}&dateTo={date_to}&recordingType=All&perPage=1000'
            )
            
            # Get JSON data from response
            data = response.json_dict()
            
            # Extract records
            records = data.get('records', [])
            
            print(f"📊 Found {len(records)} call log entries")
            return records
            
        except Exception as e:
            print(f"❌ Error fetching call logs: {e}")
            return []
    
    def filter_recordings_by_duration(self, call_logs, min_duration_seconds=15):
        """
        Filter call logs that have recordings longer than specified duration
        
        Args:
            call_logs (list): Call log records (as dictionaries)
            min_duration_seconds (int): Minimum duration in seconds
        
        Returns:
            list: Filtered call logs with recordings
        """
        filtered_logs = []
        
        for log in call_logs:
            # Check if there's a recording and duration
            if 'recording' in log and log.get('duration', 0) > min_duration_seconds:
                filtered_logs.append(log)
        
        print(f"🎯 Found {len(filtered_logs)} recordings longer than {min_duration_seconds} seconds")
        return filtered_logs
    
    def download_recording(self, recording_info, output_dir='recordings'):
        """
        Download a recording file
        
        Args:
            recording_info (dict): Recording information from call log
            output_dir (str): Directory to save recordings
        
        Returns:
            str: Path to downloaded file or None if failed
        """
        try:
            # Create output directory if it doesn't exist
            Path(output_dir).mkdir(exist_ok=True)
            
            # Get recording metadata
            recording_id = recording_info.get('id')
            content_uri = recording_info.get('contentUri')
            
            if not content_uri:
                print("❌ No content URI found for recording")
                return None
            
            # Download the recording
            print(f"⬇️  Downloading recording {recording_id}...")
            response = self.platform.get(content_uri)
            
            # Determine file extension from content type
            content_type = response.headers.get('Content-Type', 'audio/mpeg')
            extension = '.mp3' if 'mpeg' in content_type else '.wav'
            
            # Save the file
            filename = f"recording_{recording_id}{extension}"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Downloaded: {filename}")
            return filepath
            
        except Exception as e:
            print(f"❌ Error downloading recording: {e}")
            return None
    
    def process_recordings(self, date_str, min_duration=15, transcribe=False, groq_api_key=None):
        """
        Main method to fetch, filter, download, and optionally transcribe recordings
        
        Args:
            date_str (str): Date in format 'YYYY-MM-DD'
            min_duration (int): Minimum duration in seconds
            transcribe (bool): Whether to transcribe recordings
            groq_api_key (str): Groq API key for transcription
        
        Returns:
            list: List of processed recordings with metadata
        """
        if not self.authenticate():
            return []
        
        # Fetch call logs
        call_logs = self.fetch_call_logs(date_str)
        
        # Filter recordings by duration
        filtered_logs = self.filter_recordings_by_duration(call_logs, min_duration)
        
        if not filtered_logs:
            print("📭 No recordings found matching criteria")
            return []
        
        # Process each recording
        processed_recordings = []
        
        for log in filtered_logs:
            recording_info = log.get('recording', {})
            
            # Extract metadata
            metadata = {
                'id': recording_info.get('id'),
                'duration': log.get('duration'),
                'start_time': log.get('startTime'),
                'direction': log.get('direction'),
                'from': log.get('from', {}).get('phoneNumber'),
                'to': log.get('to', {}).get('phoneNumber'),
                'type': log.get('type')
            }
            
            # Download recording
            filepath = self.download_recording(recording_info)
            
            if filepath:
                metadata['filepath'] = filepath
                
                # Optionally transcribe
                if transcribe and groq_api_key:
                    try:
                        print(f"🎤 Transcribing {os.path.basename(filepath)}...")
                        result = transcribe_audio(filepath, groq_api_key)
                        transcription_text = result.get('text', '')
                        
                        if transcription_text:
                            # Save transcription
                            transcription_file = save_transcription(transcription_text, filepath)
                            metadata['transcription'] = transcription_text
                            metadata['transcription_file'] = transcription_file
                            print(f"✅ Transcribed and saved to: {transcription_file}")
                        
                    except Exception as e:
                        print(f"⚠️  Transcription failed: {e}")
                
                processed_recordings.append(metadata)
        
        # Save metadata summary
        summary_file = f"recordings_summary_{date_str}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(processed_recordings, f, indent=2)
        
        print(f"\n📄 Summary saved to: {summary_file}")
        print(f"✅ Processed {len(processed_recordings)} recordings")
        
        return processed_recordings


def main():
    # RingCentral credentials
    config = {
        "clientId": "0gAEMMaAIb9aVRHMOSW5se",
        "clientSecret": "5TQ84XRt1eNfG90l558cie9TWqoVHQTcZfRT7zHJXZA2",
        "server": "https://platform.ringcentral.com"
    }
    
    # Get JWT token from environment
    JWT_TOKEN = os.getenv("RINGCENTRAL_JWT_TOKEN", "")
    
    # Groq API key for transcription
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # Set GROQ_API_KEY in your environment
    
    if not JWT_TOKEN:
        print("❌ Error: Please set RINGCENTRAL_JWT_TOKEN environment variable")
        print("\n📋 How to get your JWT token:")
        print("1. In RingCentral Developer Console, enable JWT auth for your app")
        print("2. After saving, look for 'JWT Credentials' or 'Add JWT' button")
        print("3. Generate and download the JWT credentials")
        print("4. The JWT token will be in the downloaded file")
        print("5. Add to your .env file:")
        print("   RINGCENTRAL_JWT_TOKEN=your_jwt_token_here")
        return
    
    # Create fetcher instance
    fetcher = RingCentralJWTRecordingFetcher(
        client_id=config["clientId"],
        client_secret=config["clientSecret"],
        server=config["server"],
        jwt_token=JWT_TOKEN
    )
    
    # Process recordings for August 12, 2025
    date_to_fetch = "2025-08-12"
    min_duration_seconds = 30
    
    print(f"🔍 Fetching RingCentral recordings for {date_to_fetch}")
    print(f"⏱️  Minimum duration: {min_duration_seconds} seconds")
    print(f"🎤 Transcription: Enabled\n")
    
    # Process recordings (fetch, filter, download, and transcribe)
    processed = fetcher.process_recordings(
        date_str=date_to_fetch,
        min_duration=min_duration_seconds,
        transcribe=True,
        groq_api_key=GROQ_API_KEY
    )
    
    # Display summary
    if processed:
        print("\n📊 PROCESSING SUMMARY:")
        print("=" * 50)
        for i, recording in enumerate(processed, 1):
            print(f"\n{i}. Recording ID: {recording['id']}")
            print(f"   Duration: {recording['duration']} seconds")
            print(f"   Direction: {recording['direction']}")
            print(f"   From: {recording['from']} → To: {recording['to']}")
            print(f"   File: {recording.get('filepath', 'N/A')}")
            if 'transcription' in recording:
                print(f"   Transcription: {recording['transcription'][:100]}...")


if __name__ == "__main__":
    main()
