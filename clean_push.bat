@echo off
echo Pushing cleaned files with new workflow...

git add -A
git commit --amend -m "Add chunked transcription workflow - all secrets cleaned"
git push --force origin main

echo.
echo Success! Now go to: https://github.com/rahman77-code/transcribe/actions
echo Look for: "Chunked Call Transcription (1000+ Recordings)"
echo.
pause
