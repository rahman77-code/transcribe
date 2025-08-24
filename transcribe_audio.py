import os
import requests
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def transcribe_audio(audio_file_path, api_key):
    """
    Transcribe an audio file using Groq's Whisper API
    
    Args:
        audio_file_path (str): Path to the audio file
        api_key (str): Groq API key
    
    Returns:
        dict: Transcription result
    """
    # Check if file exists
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
    
    # Check file size (25 MB limit for free tier)
    file_size = os.path.getsize(audio_file_path) / (1024 * 1024)  # Convert to MB
    if file_size > 25:
        print(f"Warning: File size ({file_size:.2f} MB) exceeds 25 MB free tier limit")
    
    # API endpoint
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    # Headers
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    # Open and prepare the file
    with open(audio_file_path, "rb") as audio_file:
        files = {
            "file": (os.path.basename(audio_file_path), audio_file, "audio/mpeg"),
        }
        
        # Request data
        data = {
            "model": "whisper-large-v3",
            "response_format": "json",
            "language": "en",  # You can change this or make it auto-detect
        }
        
        print(f"Transcribing: {os.path.basename(audio_file_path)}")
        print(f"File size: {file_size:.2f} MB")
        print("Sending request to Groq API...")
        
        # Make the request
        response = requests.post(url, headers=headers, files=files, data=data)
    
    # Handle response
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        raise Exception(f"API Error: {response.status_code} - {response.text}")

def save_transcription(transcription_text, audio_file_path):
    """
    Save transcription to a text file
    
    Args:
        transcription_text (str): The transcribed text
        audio_file_path (str): Original audio file path (used for naming)
    """
    # Create output filename based on input filename
    audio_path = Path(audio_file_path)
    output_filename = audio_path.stem + "_transcription.txt"
    
    # Save with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(f"Transcription of: {audio_path.name}\n")
        f.write(f"Transcribed on: {timestamp}\n")
        f.write(f"{'=' * 50}\n\n")
        f.write(transcription_text)
    
    return output_filename

def main():
    # Configuration
    AUDIO_FILE = "20250812-112153_431_(281)972-7249_Outgoing_Auto_3182792817008.mp3"
    
    # Get API key from environment or use the provided one
    API_KEY = os.getenv("GROQ_API_KEY")  # Set GROQ_API_KEY in your environment
    
    try:
        # Transcribe the audio
        result = transcribe_audio(AUDIO_FILE, API_KEY)
        
        # Extract transcription text
        transcription_text = result.get("text", "")
        
        if transcription_text:
            # Save to file
            output_file = save_transcription(transcription_text, AUDIO_FILE)
            
            # Display results
            print("\n✅ Transcription successful!")
            print(f"📄 Saved to: {output_file}")
            print("\n" + "=" * 50)
            print("TRANSCRIPTION:")
            print("=" * 50)
            print(transcription_text)
            print("=" * 50)
            
            # Also save the full response for debugging
            with open("transcription_response.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"\n📊 Full response saved to: transcription_response.json")
        else:
            print("❌ No transcription text received")
            
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error during transcription: {e}")

if __name__ == "__main__":
    main()
