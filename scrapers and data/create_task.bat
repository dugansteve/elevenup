@echo off
schtasks /create /tn "Seedline Daily Scrape" /tr "cmd /c \"C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\run_daily_scrape.bat\" --force" /sc daily /st 22:00 /f
if %ERRORLEVEL% equ 0 (
    echo.
    echo SUCCESS: Task created! Will run daily at 10:00 PM
    echo.
    schtasks /query /tn "Seedline Daily Scrape"
) else (
    echo.
    echo FAILED: Could not create task. Try running as Administrator.
)
pause
