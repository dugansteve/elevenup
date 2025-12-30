@echo off
REM Weekly Seedline Data Quality Validation with Email Report
REM Runs every Monday via Windows Task Scheduler

cd /d "C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data"

echo Running Seedline weekly validation at %date% %time% >> validation_log.txt

REM Run via PowerShell to properly load User environment variable
powershell -ExecutionPolicy Bypass -File "C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data\send_validation_email.ps1"

echo Validation complete at %date% %time% >> validation_log.txt
echo ---------------------------------------- >> validation_log.txt
