# PowerShell script to set up Windows Task Scheduler for daily call processing

$taskName = "RingCentral Daily Call Processor"
$taskDescription = "Automatically fetches and transcribes daily RingCentral call recordings"
$scriptPath = Join-Path $PSScriptRoot "run_daily_processor.bat"
$workingDirectory = $PSScriptRoot

# Define the action (what to run)
$action = New-ScheduledTaskAction -Execute $scriptPath -WorkingDirectory $workingDirectory

# Define the trigger (when to run - daily at 1:00 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At 1:00AM

# Define settings
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable -MultipleInstances Parallel

# Register the scheduled task
try {
    Register-ScheduledTask -TaskName $taskName -Description $taskDescription -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest
    Write-Host "✅ Scheduled task '$taskName' created successfully!" -ForegroundColor Green
    Write-Host "The task will run daily at 1:00 AM" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To run the task immediately for testing:" -ForegroundColor Cyan
    Write-Host "Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "To view the task:" -ForegroundColor Cyan
    Write-Host "Get-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
    Write-Host ""
    Write-Host "To remove the task:" -ForegroundColor Cyan
    Write-Host "Unregister-ScheduledTask -TaskName '$taskName' -Confirm:`$false" -ForegroundColor White
} catch {
    Write-Host "❌ Error creating scheduled task: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Try running this script as Administrator" -ForegroundColor Yellow
}

