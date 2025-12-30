# Setup Seedline Weekly Validation Task
# Run this script once to create the scheduled task

$taskName = "Seedline Weekly Validation"
$batPath = "C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\run_weekly_validation.bat"

# Create action to run the batch file
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$batPath`""

# Create trigger for every Monday at 9:00 AM
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9:00AM

# Register the task (use -Force to overwrite if exists)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Force

Write-Host "Scheduled task '$taskName' created successfully!"
Write-Host "It will run every Monday at 9:00 AM"
