#!/usr/bin/env python3
"""
Simple test script to check if Groq API is working
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Test with first API key
api_key = os.getenv("GROQ_API_KEY_1") or os.getenv("GROQ_API_KEY")

if not api_key:
    print("❌ No Groq API key found in environment!")
    exit(1)

print("🧪 Testing Groq API...")
print(f"📍 Using API key: {api_key[:8]}...{api_key[-4:]}")

# Test 1: Simple text completion
print("\n📝 Test 1: Text Completion")
url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
data = {
    "messages": [{"role": "user", "content": "Say hello"}],
    "model": "mixtral-8x7b-32768",
    "max_tokens": 10
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=10)
    print(f"Response Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Text completion works!")
        print(f"Response: {response.json()['choices'][0]['message']['content']}")
    else:
        print(f"❌ Error: {response.text}")
except Exception as e:
    print(f"❌ Connection error: {e}")

# Test 2: Check audio transcription endpoint
print("\n🎤 Test 2: Audio Transcription Endpoint")
url = "https://api.groq.com/openai/v1/audio/transcriptions"

# Create a tiny test audio file (1 second of silence)
import wave
import struct

test_audio = "test_audio.wav"
with wave.open(test_audio, 'w') as wav_file:
    wav_file.setnchannels(1)  # mono
    wav_file.setsampwidth(2)   # 2 bytes per sample
    wav_file.setframerate(16000)  # 16kHz
    # Write 1 second of silence
    for _ in range(16000):
        wav_file.writeframes(struct.pack('<h', 0))

print(f"Created test audio file: {test_audio}")

# Try to transcribe it
try:
    with open(test_audio, 'rb') as audio_file:
        files = {
            'file': (test_audio, audio_file, 'audio/wav')
        }
        data = {
            'model': 'whisper-large-v3-turbo',
            'response_format': 'json'
        }
        headers = {
            'Authorization': f'Bearer {api_key}'
        }
        
        response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Audio transcription endpoint works!")
            result = response.json()
            print(f"Transcription: '{result.get('text', '')}'")
        elif response.status_code == 500:
            print("❌ HTTP 500 - Groq server error!")
            print(f"Response: {response.text}")
            print("\n⚠️ This indicates Groq's servers are having issues.")
            print("Please try again later or contact Groq support.")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
except Exception as e:
    print(f"❌ Error: {e}")
finally:
    # Clean up test file
    if os.path.exists(test_audio):
        os.remove(test_audio)
        print(f"Cleaned up {test_audio}")

print("\n✅ Test complete!")
