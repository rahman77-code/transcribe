@echo off
echo Creating fresh repository with only essential files...

REM Remove git history
rmdir /s /q .git

REM Initialize fresh repository
git init
git branch -M main

REM Add only essential files
git add .github/workflows/chunked-transcription.yml
git add chunked_processor.py
git add daily_call_processor_dev_optimized.py
git add requirements.txt
git add README.md

git commit -m "Initial commit - chunked transcription workflow"
git remote add origin https://github.com/rahman77-code/transcribe.git
git push --force -u origin main

echo.
echo Success! Clean repository pushed.
echo Go to: https://github.com/rahman77-code/transcribe/actions
echo Look for: "Chunked Call Transcription (1000+ Recordings)"
echo.
pause
