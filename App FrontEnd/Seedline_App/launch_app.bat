@echo off
title Seedline App Launcher
color 0A

echo ========================================
echo     Seedline App Launcher
echo ========================================
echo.

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing dependencies...
    echo This may take a minute on first run.
    echo.
    call npm install
    if errorlevel 1 (
        echo.
        echo ERROR: npm install failed!
        echo Make sure Node.js is installed.
        echo Download from: https://nodejs.org/
        pause
        exit /b 1
    )
)

echo.
echo Starting Seedline App...
echo.
echo NOTE: For login to work, the admin server must be running.
echo       Run launch_admin.bat in a separate window first.
echo.
echo Press Ctrl+C to stop the server.
echo.

REM Start the dev server with --open flag (opens browser at correct port)
call npm run dev -- --open

pause
