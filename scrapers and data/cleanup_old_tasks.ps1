# Cleanup old scheduled tasks - force remove
Write-Host "Removing old daily/weekly tasks..." -ForegroundColor Yellow

# Get all tasks in Seedline folder
$allTasks = Get-ScheduledTask -TaskPath "\Seedline\" -ErrorAction SilentlyContinue

# Keep only the new smart schedule tasks
$keepTasks = @("Seedline Saturday Scrape", "Seedline Sunday Scrape", "Seedline Monday Follow-up", "Seedline Tuesday Cleanup")

foreach ($task in $allTasks) {
    if ($task.TaskName -notin $keepTasks) {
        Write-Host "Removing: $($task.TaskName)" -ForegroundColor Red
        $task | Unregister-ScheduledTask -Confirm:$false
    } else {
        Write-Host "Keeping: $($task.TaskName)" -ForegroundColor Green
    }
}

Write-Host "`nFinal tasks:" -ForegroundColor Yellow
Get-ScheduledTask -TaskPath "\Seedline\" | Select-Object TaskName, State | Format-Table
