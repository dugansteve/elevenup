# ============================================================
# Setup Daily Seedline Scraper + Ranker Scheduled Task
# ============================================================
# Run this script as Administrator to create the scheduled task
#
# Usage:
#   Right-click PowerShell -> Run as Administrator
#   .\setup_daily_task.ps1
#
# To remove the task later:
#   Unregister-ScheduledTask -TaskName "Seedline Daily Scrape" -Confirm:$false
# ============================================================

$TaskName = "Seedline Daily Scrape"
$TaskDescription = "Runs Seedline scrapers, database cleanup, and team ranker daily at 10 PM"

# Path to the batch file
$BatchFile = "C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\run_daily_scrape.bat"

# Check if batch file exists
if (-not (Test-Path $BatchFile)) {
    Write-Error "Batch file not found: $BatchFile"
    exit 1
}

# Check if task already exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Task '$TaskName' already exists. Removing old task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create the action (run the batch file)
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BatchFile`" --force" -WorkingDirectory (Split-Path $BatchFile)

# Create the trigger (daily at 10 PM)
$Trigger = New-ScheduledTaskTrigger -Daily -At "10:00PM"

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 3)

# Create principal (run whether user is logged on or not)
# Note: This requires the task to be registered with credentials
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited

try {
    # Register the task
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $TaskDescription `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "SUCCESS: Scheduled task created!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Name:    $TaskName"
    Write-Host "Schedule:     Daily at 10:00 PM"
    Write-Host "Batch File:   $BatchFile"
    Write-Host ""
    Write-Host "The task will run:" -ForegroundColor Cyan
    Write-Host "  1. League scrapers (ECNL, GA, ASPIRE, NPL, etc.)"
    Write-Host "  2. Database cleanup"
    Write-Host "  3. Team ranker (generates rankings_history.json data point)"
    Write-Host ""
    Write-Host "To view/modify: Open Task Scheduler -> Seedline Daily Scrape"
    Write-Host "To run now:     schtasks /run /tn `"$TaskName`""
    Write-Host "To delete:      Unregister-ScheduledTask -TaskName `"$TaskName`""
    Write-Host ""

} catch {
    Write-Error "Failed to create scheduled task: $_"
    Write-Host ""
    Write-Host "If you see 'Access Denied', try running PowerShell as Administrator" -ForegroundColor Yellow
    exit 1
}
