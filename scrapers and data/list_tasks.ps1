Get-ScheduledTask | Where-Object { $_.TaskPath -like '*Seedline*' } | Format-Table TaskPath, TaskName, State -AutoSize
