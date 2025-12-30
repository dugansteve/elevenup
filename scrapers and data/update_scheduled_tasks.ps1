# Update Scheduled Tasks for Smart Seedline Scraping
# ===================================================
#
# Smart schedule based on when games actually happen:
# - Saturday 10 PM: Full scrape (game day)
# - Sunday 10 PM: Full scrape (game day)
# - Monday 7 AM: Follow-up for Sunday games missing results
# - Tuesday 7 AM: Final weekend cleanup (only if missing results)
#
# Wed-Fri: No scheduled tasks (no games typically)
# The scheduler itself checks for missing results and skips if none

$ScriptsPath = "C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data"
$BatFile = "$ScriptsPath\run_daily_scrape.bat"

Write-Host "Updating Seedline scheduled tasks (Smart Schedule)..." -ForegroundColor Cyan
Write-Host ""

# Common settings with retry logic
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RestartInterval (New-TimeSpan -Hours 1) `
    -RestartCount 3 `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Remove old tasks
$oldTasks = @(
    "Seedline Daily Scrape - Evening",
    "Seedline Daily Scrape - Morning",
    "Seedline Weekly Deep Scan"
)
foreach ($task in $oldTasks) {
    try {
        Unregister-ScheduledTask -TaskName $task -TaskPath "\Seedline\" -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "  Removed old task: $task" -ForegroundColor Gray
    } catch { }
}

# Saturday evening (full scrape - game day)
$satAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatFile`"" `
    -WorkingDirectory $ScriptsPath

$satTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At "22:00"

try {
    Register-ScheduledTask `
        -TaskName "Seedline Saturday Scrape" `
        -TaskPath "\Seedline\" `
        -Action $satAction `
        -Trigger $satTrigger `
        -Settings $settings `
        -Description "Saturday game day scrape. Runs all scrapers."
    Write-Host "  Created: Saturday Scrape (10 PM)" -ForegroundColor Green
} catch {
    Write-Host "  Error: $_" -ForegroundColor Red
}

# Sunday evening (full scrape - game day)
$sunTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "22:00"

try {
    Register-ScheduledTask `
        -TaskName "Seedline Sunday Scrape" `
        -TaskPath "\Seedline\" `
        -Action $satAction `
        -Trigger $sunTrigger `
        -Settings $settings `
        -Description "Sunday game day scrape. Runs all scrapers."
    Write-Host "  Created: Sunday Scrape (10 PM)" -ForegroundColor Green
} catch {
    Write-Host "  Error: $_" -ForegroundColor Red
}

# Monday morning follow-up (only if missing results)
$monAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$BatFile`" --missing-only" `
    -WorkingDirectory $ScriptsPath

$monTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "07:00"

try {
    Register-ScheduledTask `
        -TaskName "Seedline Monday Follow-up" `
        -TaskPath "\Seedline\" `
        -Action $monAction `
        -Trigger $monTrigger `
        -Settings $settings `
        -Description "Monday follow-up for Sunday games. Only runs if results missing."
    Write-Host "  Created: Monday Follow-up (7 AM)" -ForegroundColor Green
} catch {
    Write-Host "  Error: $_" -ForegroundColor Red
}

# Tuesday final cleanup (only if missing results)
$tueTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday -At "07:00"

try {
    Register-ScheduledTask `
        -TaskName "Seedline Tuesday Cleanup" `
        -TaskPath "\Seedline\" `
        -Action $monAction `
        -Trigger $tueTrigger `
        -Settings $settings `
        -Description "Tuesday final weekend cleanup. Only runs if results missing."
    Write-Host "  Created: Tuesday Cleanup (7 AM)" -ForegroundColor Green
} catch {
    Write-Host "  Error: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Smart Schedule Summary:" -ForegroundColor Yellow
Write-Host "  Saturday 10 PM  - Full scrape (game day)" -ForegroundColor White
Write-Host "  Sunday 10 PM    - Full scrape (game day)" -ForegroundColor White
Write-Host "  Monday 7 AM     - Follow-up (only if missing)" -ForegroundColor White
Write-Host "  Tuesday 7 AM    - Final cleanup (only if missing)" -ForegroundColor White
Write-Host "  Wed-Fri         - No scheduled tasks" -ForegroundColor Gray
Write-Host ""
Write-Host "All tasks have:" -ForegroundColor Cyan
Write-Host "  - StartWhenAvailable: Runs ASAP if computer was off" -ForegroundColor Gray
Write-Host "  - RestartInterval: Retries every hour on failure" -ForegroundColor Gray
Write-Host "  - RestartCount: Up to 3 retries" -ForegroundColor Gray
Write-Host ""
Write-Host "Done!" -ForegroundColor Green
