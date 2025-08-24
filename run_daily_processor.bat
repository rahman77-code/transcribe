@echo off
REM Daily RingCentral Call Processor - Windows Batch Script
REM This script runs the daily call processor

echo ========================================
echo Starting Daily Call Processor
echo Date: %date% Time: %time%
echo ========================================

REM Change to the script directory
cd /d %~dp0

REM Activate Python and run the script
python daily_call_processor.py

echo ========================================
echo Daily Call Processor Completed
echo Date: %date% Time: %time%
echo ========================================

REM Pause to see output (remove this line when running as scheduled task)
pause

