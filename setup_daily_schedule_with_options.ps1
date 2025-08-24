# PowerShell script to set up daily call recording processor with scheduling options
# Run as Administrator for best results

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "RingCentral Daily Processor Setup" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator. Some features may not work." -ForegroundColor Yellow
    Write-Host "For best results, run PowerShell as Administrator." -ForegroundColor Yellow
    Write-Host ""
}

# Get the current directory
$scriptPath = Get-Location
$pythonScript = Join-Path $scriptPath "daily_call_processor_multi_key.py"
$batchFile = Join-Path $scriptPath "run_daily_processor.bat"
$logFile = Join-Path $scriptPath "daily_processor_scheduled.log"

# Check if Python script exists
if (-not (Test-Path $pythonScript)) {
    Write-Host "ERROR: daily_call_processor_multi_key.py not found!" -ForegroundColor Red
    Write-Host "Make sure you're in the correct directory." -ForegroundColor Red
    exit 1
}

# Create batch file if it doesn't exist
if (-not (Test-Path $batchFile)) {
    $batchContent = @"
@echo off
cd /d "$scriptPath"
echo Starting Daily Call Processor at %date% %time% >> "$logFile"
python "$pythonScript"
echo Completed at %date% %time% >> "$logFile"
echo ================================== >> "$logFile"
"@
    Set-Content -Path $batchFile -Value $batchContent
    Write-Host "Created batch file: $batchFile" -ForegroundColor Green
}

Write-Host ""
Write-Host "WHEN DO YOU WANT THE SCRIPT TO RUN?" -ForegroundColor Yellow
Write-Host "1. Daily at 2:00 AM (Process previous day's calls)" -ForegroundColor White
Write-Host "2. Daily at a custom time" -ForegroundColor White
Write-Host "3. Every time I start my computer" -ForegroundColor White
Write-Host "4. Every hour (for testing)" -ForegroundColor White
Write-Host "5. Don't schedule - I'll run it manually" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Enter your choice (1-5)"

# Remove existing task if it exists
$existingTask = Get-ScheduledTask -TaskName "RingCentralDailyProcessor" -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Removing existing scheduled task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName "RingCentralDailyProcessor" -Confirm:$false
}

switch ($choice) {
    "1" {
        # Daily at 2 AM
        $trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
        $taskName = "RingCentralDailyProcessor"
        $description = "Processes RingCentral call recordings daily at 2:00 AM"
    }
    "2" {
        # Custom time
        $timeInput = Read-Host "Enter time in 24-hour format (e.g., 14:30 for 2:30 PM)"
        try {
            $customTime = [DateTime]::ParseExact($timeInput, "HH:mm", $null)
            $trigger = New-ScheduledTaskTrigger -Daily -At $customTime
            $taskName = "RingCentralDailyProcessor"
            $description = "Processes RingCentral call recordings daily at $timeInput"
        } catch {
            Write-Host "Invalid time format. Using default 2:00 AM" -ForegroundColor Red
            $trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM
            $description = "Processes RingCentral call recordings daily at 2:00 AM"
        }
    }
    "3" {
        # At startup
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $taskName = "RingCentralDailyProcessor"
        $description = "Processes RingCentral call recordings at system startup"
        Write-Host ""
        Write-Host "NOTE: With startup option, the script will process yesterday's calls" -ForegroundColor Yellow
        Write-Host "each time you turn on your computer." -ForegroundColor Yellow
    }
    "4" {
        # Every hour (for testing)
        $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 365)
        $taskName = "RingCentralDailyProcessor"
        $description = "Processes RingCentral call recordings every hour (testing mode)"
        Write-Host ""
        Write-Host "WARNING: This will run every hour! Only use for testing." -ForegroundColor Yellow
    }
    "5" {
        # Manual only
        Write-Host ""
        Write-Host "No schedule created. To run manually, use:" -ForegroundColor Green
        Write-Host "python daily_call_processor_multi_key.py" -ForegroundColor White
        Write-Host ""
        Write-Host "Your .env file has been updated with 3 Groq API keys." -ForegroundColor Green
        exit 0
    }
    default {
        Write-Host "Invalid choice. Exiting." -ForegroundColor Red
        exit 1
    }
}

# Create scheduled task
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batchFile`"" -WorkingDirectory $scriptPath

# Task settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Principal (who runs the task)
if ($isAdmin) {
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
} else {
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
}

# Register the task
try {
    $task = Register-ScheduledTask `
        -TaskName $taskName `
        -Description $description `
        -Trigger $trigger `
        -Action $action `
        -Settings $settings `
        -Principal $principal `
        -Force

    Write-Host ""
    Write-Host "SUCCESS! Scheduled task created." -ForegroundColor Green
    Write-Host "Task Name: $taskName" -ForegroundColor White
    Write-Host "Description: $description" -ForegroundColor White
    
    # Show next run time
    $nextRun = (Get-ScheduledTask -TaskName $taskName | Get-ScheduledTaskInfo).NextRunTime
    if ($nextRun) {
        Write-Host "Next scheduled run: $nextRun" -ForegroundColor Cyan
    }

    Write-Host ""
    Write-Host "IMPORTANT NOTES:" -ForegroundColor Yellow
    Write-Host "- Your computer must be ON for the task to run" -ForegroundColor White
    Write-Host "- The script will use your 3 Groq API keys automatically" -ForegroundColor White
    Write-Host "- Recordings will be saved to: $scriptPath\daily_recordings\" -ForegroundColor White
    Write-Host "- Logs will be saved to: $logFile" -ForegroundColor White
    
    Write-Host ""
    $testNow = Read-Host "Do you want to test the script now? (Y/N)"
    if ($testNow -eq "Y" -or $testNow -eq "y") {
        Write-Host "Running test..." -ForegroundColor Green
        Start-Process -FilePath "python" -ArgumentList $pythonScript -NoNewWindow -Wait
    }

} catch {
    Write-Host "ERROR: Failed to create scheduled task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "Try running PowerShell as Administrator" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
