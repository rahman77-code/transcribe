@echo off
echo Setting up environment variables...

REM RingCentral credentials
set RC_CLIENT_ID=VNKRmCCWukXcPadmaLZoMu
set RC_CLIENT_SECRET=37zo0FbARv5fcHIDHyh9485r2EA57ulqTdo1znecBZwQ
set RC_JWT=eyJraWQiOiI4NzYyZjU5OGQwNTk0NGRiODZiZjVjYTk3ODA0NzYwOCIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJhdWQiOiJodHRwczovL3BsYXRmb3JtLnJpbmdjZW50cmFsLmNvbS9yZXN0YXBpL29hdXRoL3Rva2VuIiwic3ViIjoiNjMzMjQ0MDQwMDgiLCJpc3MiOiJodHRwczovL3BsYXRmb3JtLnJpbmdjZW50cmFsLmNvbSIsImV4cCI6Mzg5NTE2Nzk4NCwiaWF0IjoxNzQ3Njg0MzM3LCJqdGkiOiJCbG1KZ1JVblNCU0Fld2NMNDhvdEZRIn0.Cx2UAGelOzaQkwcqt3c1Ijo_-5gDjO_i7cJfPEc6fJGRUxMwkhYwQGOG7-A9_wh2woaiEdVHMsoNyMgh9_0pk94_Hov8hjroMlN0d685bOYMciEsynWLvFZG74JHlyLj8a4uTmlk_EwVX3Eos8_mQNr4uc8sZhGzhLkGyBqwjBQsWdRY0niemFWvtep8qPvjp2KkEwEonH7vOFdodUB__7D-6YR6tn5OV_kjV2EzH8yBSGzF8y75acf9HcfRIMoTe7z2fF8XtYqdX0sn9c-b16yFc05atYrW5CEuctctGZMzR4AvizSZbDSg0OZn9IpL3Um0S8ALc00DTCaB9NfA6A
set RC_SERVER_URL=https://platform.ringcentral.com

REM Add your 6 Groq API keys here
echo.
echo Please add your 6 Groq API keys:
echo Example: set GROQ_API_KEY_1=gsk_your_first_key_here
echo.
set /p GROQ_API_KEY_1=Enter GROQ_API_KEY_1: 
set /p GROQ_API_KEY_2=Enter GROQ_API_KEY_2: 
set /p GROQ_API_KEY_3=Enter GROQ_API_KEY_3: 
set /p GROQ_API_KEY_4=Enter GROQ_API_KEY_4: 
set /p GROQ_API_KEY_5=Enter GROQ_API_KEY_5: 
set /p GROQ_API_KEY_6=Enter GROQ_API_KEY_6: 

echo.
echo ========================================
echo Running 300 RPM Optimized Processor
echo Using 6 API keys = 1,800 RPM capacity
echo Expected completion: ~30 seconds
echo ========================================
echo.

REM Optional: Set a specific date (YYYY-MM-DD format)
REM set TARGET_DATE=2025-08-20

python daily_call_processor_300rpm.py

echo.
echo ========================================
echo Test completed!
echo Check the daily_recordings folder for results
echo ========================================
pause
