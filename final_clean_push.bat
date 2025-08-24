@echo off
echo Removing problematic files and creating clean workflow...

REM Remove files that contain old secrets
git rm SETUP_DEV_TIER_KEYS.md
git rm GROQ_KEYS_TO_ADD.txt
git rm test_new_dev_keys.py

REM Keep only essential files
git add .github/workflows/chunked-transcription.yml
git add chunked_processor.py
git add daily_call_processor_dev_optimized.py
git add requirements.txt

git commit -m "Clean workflow - removed all secret-containing files"
git push --force origin main

echo.
echo Done! The workflow should now be available at:
echo https://github.com/rahman77-code/transcribe/actions
echo Look for: "Chunked Call Transcription (1000+ Recordings)"
echo.
pause
