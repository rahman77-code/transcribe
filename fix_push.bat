@echo off
echo Fixing the workflow push...

git add .
git commit -m "Add chunked transcription workflow that works"
git push --set-upstream origin main

echo.
echo Done! Now go to: https://github.com/rahman77-code/transcribe/actions
echo Look for: "Chunked Call Transcription (1000+ Recordings)"
echo.
pause
