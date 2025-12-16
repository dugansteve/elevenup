@echo off
REM ============================================================================
REM UPDATE REACT RANKINGS - Auto-detects latest versions
REM ============================================================================
REM This script:
REM 1. Finds the newest team_ranker_v*.py file
REM 2. Finds the newest cleanup_database_v*.py file  
REM 3. Runs the ranker (which uses cleanup internally)
REM 4. Copies the JSON to the React app
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
REM FIND LATEST TEAM RANKER (using PowerShell for reliable sorting)
REM ============================================================================
echo Looking for latest team_ranker...

REM Use PowerShell to find the latest version file
REM This properly handles v9 vs v39 by extracting numeric version
for /f "delims=" %%f in ('powershell -NoProfile -Command "$files = Get-ChildItem 'team_ranker_v*.py' -ErrorAction SilentlyContinue; if ($files) { $files | ForEach-Object { $ver = $_.BaseName -replace 'team_ranker_v',''; $num = [int]($ver -replace '[a-z].*$',''); [PSCustomObject]@{File=$_.Name; Num=$num; Ver=$ver} } | Sort-Object Num,Ver -Descending | Select-Object -First 1 -ExpandProperty File }"') do (
    set "LATEST_RANKER=%%f"
)

if "%LATEST_RANKER%"=="" (
    echo ERROR: No team_ranker_v*.py file found!
    echo Make sure you're running this from the correct directory.
    pause
    exit /b 1
)

echo Found: %LATEST_RANKER%
echo.

REM ============================================================================
REM FIND LATEST CLEANUP DATABASE
REM ============================================================================
echo Looking for latest cleanup_database...

for /f "delims=" %%f in ('powershell -NoProfile -Command "$files = Get-ChildItem 'cleanup_database_v*.py' -ErrorAction SilentlyContinue; if ($files) { $files | ForEach-Object { $ver = $_.BaseName -replace 'cleanup_database_v',''; $num = [int]($ver -replace '[a-z].*$',''); [PSCustomObject]@{File=$_.Name; Num=$num; Ver=$ver} } | Sort-Object Num,Ver -Descending | Select-Object -First 1 -ExpandProperty File }"') do (
    set "LATEST_CLEANUP=%%f"
)

if "%LATEST_CLEANUP%"=="" (
    echo WARNING: No cleanup_database_v*.py file found
    echo The ranker will run without cleanup capabilities.
) else (
    echo Found: %LATEST_CLEANUP%
)
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
