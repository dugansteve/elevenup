@echo off
REM ============================================================================
REM UPDATE REACT RANKINGS - Uses final versions
REM ============================================================================
REM This script:
REM 1. Runs team_ranker_final.py
REM 2. Copies the JSON to the React app
REM ============================================================================

setlocal enabledelayedexpansion

echo.
echo ============================================================================
echo   SEEDLINE RANKINGS UPDATE
echo ============================================================================
echo.

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Working directory: %CD%
echo.

REM ============================================================================
REM CHECK FOR TEAM RANKER
REM ============================================================================
set "LATEST_RANKER=team_ranker_final.py"

if not exist "%LATEST_RANKER%" (
    echo ERROR: team_ranker_final.py not found!
    echo Make sure you're running this from the correct directory.
    pause
    exit /b 1
)

echo Using: %LATEST_RANKER%
echo.

REM ============================================================================
REM RUN THE RANKER
REM ============================================================================
echo ============================================================================
echo   RUNNING: %LATEST_RANKER%
echo ============================================================================
echo.

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run the ranker with cleanup
python "%LATEST_RANKER%" --cleanup

if errorlevel 1 (
    echo.
    echo ERROR: Ranker failed!
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo   COMPLETE!
echo ============================================================================
echo.
echo Rankings updated successfully.
echo The JSON file has been copied to your React app.
echo.
echo To see the changes:
echo   1. Refresh your browser if the app is running
echo   2. Or run: npm run dev (in the Seedline_App folder)
echo.

pause
