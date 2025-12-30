@echo off
REM ============================================================
REM Daily Scheduled Scraper Runner
REM ============================================================
REM This batch file runs the scheduled scraper for league games
REM Schedule this to run daily at end of day (e.g., 10 PM or 11 PM)
REM
REM Usage:
REM   run_daily_scrape.bat           - Run full scheduled scrape
REM   run_daily_scrape.bat --dry-run - Preview what would be scraped
REM ============================================================

echo.
echo ============================================================
echo DAILY SCHEDULED SCRAPE - %DATE% %TIME%
echo ============================================================
echo.

REM Set working directory to Dropbox folder
cd /d "C:\Users\dugan\Smart Human Dynamics Dropbox\Steve Dugan\Seedline\scrapers and data"

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run the scheduled scraper with any passed arguments
python scheduled_scraper.py %*

REM Check exit code
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Scraper exited with code %ERRORLEVEL%
    echo Check scraper_schedule.log for details
)

echo.
echo ============================================================
echo Running SAFE database cleanup...
echo ============================================================
echo.

REM Run safe cleanup (non-destructive fixes only)
python database_cleanup_safe.py

echo.
echo ============================================================
echo Running Data Validation...
echo ============================================================
echo.

REM Check for data mismatches and fix them
python validate_data.py --fix

echo.
echo ============================================================
echo Checking State Data Coverage...
echo ============================================================
echo.

REM Check state coverage and auto-fix if below thresholds
python state_coverage_check.py

echo.
echo ============================================================
echo Populating Address Data from Club Addresses...
echo ============================================================
echo.

REM Copy club address data to teams (city, state, street, zip)
REM This ensures new teams get address data from their club
python populate_addresses_from_clubs.py

echo.
echo ============================================================
echo Running Team Ranker to update rankings...
echo ============================================================
echo.

REM Run the team ranker to generate new rankings and history data point
python "Run Rankings\team_ranker_final.py" --no-cleanup

if %ERRORLEVEL% neq 0 (
    echo.
    echo WARNING: Ranker exited with code %ERRORLEVEL%
)

echo.
echo ============================================================
echo Exporting Conference Games for Simulation...
echo ============================================================
echo.

REM Export conference games data for the React simulation feature
python export_conference_games.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo WARNING: Conference games export exited with code %ERRORLEVEL%
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo WARNING: Cleanup exited with code %ERRORLEVEL%
    echo Check cleanup_log.txt for details
)

echo.
echo ============================================================
echo Scrape completed at %TIME%
echo ============================================================
echo.

REM Keep window open if run manually (not from Task Scheduler)
if "%1"=="" pause
