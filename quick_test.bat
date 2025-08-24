@echo off
echo ========================================
echo 300 RPM Test - Quick Start
echo ========================================
echo.
echo Setting up environment...

REM RingCentral credentials
set RC_CLIENT_ID=VNKRmCCWukXcPadmaLZoMu
set RC_CLIENT_SECRET=37zo0FbARv5fcHIDHyh9485r2EA57ulqTdo1znecBZwQ
set RC_JWT=eyJraWQiOiI4NzYyZjU5OGQwNTk0NGRiODZiZjVjYTk3ODA0NzYwOCIsInR5cCI6IkpXVCIsImFsZyI6IlJTMjU2In0.eyJhdWQiOiJodHRwczovL3BsYXRmb3JtLnJpbmdjZW50cmFsLmNvbS9yZXN0YXBpL29hdXRoL3Rva2VuIiwic3ViIjoiNjMzMjQ0MDQwMDgiLCJpc3MiOiJodHRwczovL3BsYXRmb3JtLnJpbmdjZW50cmFsLmNvbSIsImV4cCI6Mzg5NTE2Nzk4NCwiaWF0IjoxNzQ3Njg0MzM3LCJqdGkiOiJCbG1KZ1JVblNCU0Fld2NMNDhvdEZRIn0.Cx2UAGelOzaQkwcqt3c1Ijo_-5gDjO_i7cJfPEc6fJGRUxMwkhYwQGOG7-A9_wh2woaiEdVHMsoNyMgh9_0pk94_Hov8hjroMlN0d685bOYMciEsynWLvFZG74JHlyLj8a4uTmlk_EwVX3Eos8_mQNr4uc8sZhGzhLkGyBqwjBQsWdRY0niemFWvtep8qPvjp2KkEwEonH7vOFdodUB__7D-6YR6tn5OV_kjV2EzH8yBSGzF8y75acf9HcfRIMoTe7z2fF8XtYqdX0sn9c-b16yFc05atYrW5CEuctctGZMzR4AvizSZbDSg0OZn9IpL3Um0S8ALc00DTCaB9NfA6A
set RC_SERVER_URL=https://platform.ringcentral.com

REM Add your Groq API keys here (you provided 6 earlier)
REM Example: set GROQ_API_KEY_1=gsk_your_key_here

REM IMPORTANT: Add your 6 API keys below
set GROQ_API_KEY_1=YOUR_KEY_1_HERE
set GROQ_API_KEY_2=YOUR_KEY_2_HERE
set GROQ_API_KEY_3=YOUR_KEY_3_HERE
set GROQ_API_KEY_4=YOUR_KEY_4_HERE
set GROQ_API_KEY_5=YOUR_KEY_5_HERE
set GROQ_API_KEY_6=YOUR_KEY_6_HERE

echo.
echo Configuration:
echo - 6 Groq API keys configured
echo - 300 RPM per key = 1,800 total RPM
echo - Processing yesterday's recordings
echo.
echo Starting in 3 seconds...
timeout /t 3 /nobreak > nul

python daily_call_processor_300rpm.py

echo.
echo ========================================
echo Test completed!
echo Check the results in:
echo - daily_recordings\[date]\ folder
echo - daily_call_processor_300rpm.log
echo ========================================
pause
