@echo off
echo Adding new workflow...
git add .github/workflows/chunked-transcription.yml
git commit -m "Add working chunked transcription workflow"
git push
echo.
echo Done! Check https://github.com/rahman77-code/transcribe/actions
echo Look for "Chunked Call Transcription (1000+ Recordings)"
pause
