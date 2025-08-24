@echo off
echo Fixing the hanging issue in chunked processor...

git add chunked_processor.py
git commit -m "Fix hanging issue - use simple sequential processing"
git push origin main

echo.
echo Fixed! The chunked processor will now exit cleanly after completion.
echo Re-run your workflow: https://github.com/rahman77-code/transcribe/actions
echo.
pause
