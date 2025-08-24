@echo off
echo Updating workflow with manual date input...

git add .github/workflows/chunked-transcription.yml
git commit -m "Add manual date input to chunked transcription workflow"
git push origin main

echo.
echo Success! Updated workflow now has date input.
echo Go to: https://github.com/rahman77-code/transcribe/actions
echo The workflow will now ask for a date when you run it manually!
echo.
pause
