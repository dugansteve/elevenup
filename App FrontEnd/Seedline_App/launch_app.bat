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
echo The app will open at: http://localhost:5173
echo Press Ctrl+C to stop the server.
echo.

REM Wait 3 seconds then open browser
start /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:5173"

REM Start the dev server
call npm run dev

pause
