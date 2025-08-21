# Audio Transcription with Groq Whisper API & RingCentral Integration

This tool provides two main functionalities:
1. Transcribe audio files using Groq's Whisper API
2. Fetch and transcribe RingCentral call recordings

## Setup

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. (Optional) Set your Groq API key as an environment variable:
   ```bash
   # On Windows PowerShell:
   $env:GROQ_API_KEY="your_api_key_here"
   
   # On Windows Command Prompt:
   set GROQ_API_KEY=your_api_key_here
   ```

## Usage

Simply run the script:
```bash
python transcribe_audio.py
```

The script will:
1. Read the MP3 file in the current directory
2. Send it to Groq's Whisper API for transcription
3. Save the transcription to a text file
4. Display the transcription in the console

## Output

- **Text file**: `[original_filename]_transcription.txt` - Contains the transcribed text
- **JSON file**: `transcription_response.json` - Contains the full API response for debugging

## Supported Audio Formats

- MP3, MP4, MPEG, MPGA, M4A, WAV, WEBM, FLAC, OGG

## File Size Limits

- Free tier: 25 MB maximum
- Developer tier: 100 MB maximum

## Notes

- The script is currently configured to transcribe in English. You can modify the `language` parameter in the script to change this.
- For better performance with large files, consider downsampling to 16 kHz mono using ffmpeg.

---

## RingCentral Integration

### Setup for RingCentral

1. **Set your RingCentral credentials as environment variables:**
   ```bash
   # On Windows PowerShell:
   $env:RINGCENTRAL_USERNAME="your_phone_number"
   $env:RINGCENTRAL_PASSWORD="your_password"
   $env:RINGCENTRAL_EXTENSION=""  # Optional, leave empty if no extension
   ```

2. **Configure API credentials:**
   The RingCentral API credentials are already configured in the script:
   - Client ID: `0gAEMMaAIb9aVRHMOSW5se`
   - Client Secret: `5TQ84XRt1eNfG90l558cie9TWqoVHQTcZfRT7zHJXZA2`

### Fetch and Transcribe RingCentral Recordings

Run the RingCentral recording fetcher:
```bash
python ringcentral_recordings.py
```

This script will:
1. Authenticate with RingCentral using your credentials
2. Fetch call logs for August 13, 2025 (or modify the date in the script)
3. Filter recordings longer than 15 seconds
4. Download the recordings to a `recordings/` folder
5. Automatically transcribe each recording using Groq's Whisper API
6. Save transcriptions as text files
7. Create a summary JSON file with all metadata

### Features

- **Date filtering**: Fetches recordings for a specific date
- **Duration filtering**: Only processes recordings longer than 15 seconds
- **Automatic download**: Downloads all matching recordings
- **Automatic transcription**: Transcribes each recording using Groq API
- **Metadata tracking**: Saves call information (duration, phone numbers, direction, etc.)
- **Summary report**: Creates a JSON file with all processed recordings

### Output Files

- `recordings/`: Directory containing downloaded audio files
- `recording_[ID]_transcription.txt`: Individual transcription files
- `recordings_summary_YYYY-MM-DD.json`: Summary of all processed recordings
- `transcription_response.json`: Latest API response (for debugging)

### Important Notes

- **Date consideration**: August 13, 2025 is a future date, so there won't be any recordings yet
- **API limits**: RingCentral typically retains call logs for 90 days
- **Rate limits**: Be mindful of API rate limits when fetching many recordings
- **Authentication**: Your RingCentral username is typically your phone number
