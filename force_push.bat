@echo off
echo Force pushing the new chunked workflow...

git push --force-with-lease origin main

echo.
echo Done! Now check: https://github.com/rahman77-code/transcribe/actions
echo Look for: "Chunked Call Transcription (1000+ Recordings)"
echo.
pause
