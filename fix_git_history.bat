@echo off
echo Fixing git history to remove API keys...
cd /d "C:\Users\airkooled\Desktop\recording"

echo.
echo Resetting to the last good commit...
git reset --hard HEAD~2

echo.
echo Re-applying changes WITHOUT the files containing keys...
git add daily_call_processor_fixed.py
git add .gitignore
git add ADD_MORE_GROQ_KEYS.md
git add SCALE_TO_50_KEYS.md
git add test_groq_api.py

echo.
echo Committing clean changes...
git commit -m "Skip recordings shorter than 20 seconds + Support up to 50 API keys + Dynamic speed adjustment"

echo.
echo Force pushing to override history...
git push --force origin main

echo.
echo ========================================
echo DONE! History cleaned and pushed!
echo ========================================
echo.
echo Your API keys are in: GROQ_KEYS_TO_ADD.txt
echo.
pause
