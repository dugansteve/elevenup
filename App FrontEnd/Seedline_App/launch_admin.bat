@echo off
title Seedline Admin Server
color 0A

echo.
echo  ========================================
echo   SEEDLINE ADMIN DASHBOARD V23
echo  ========================================
echo.

REM Get the directory where this batch file is located
cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python is not installed or not in PATH
    echo  Please install Python from https://python.org
    echo.
    pause
    exit /b 1
)

REM Check if admin_server.py exists
if not exist "admin_server.py" (
    echo  ERROR: admin_server.py not found in this folder
    echo  Make sure you extracted all files from the zip
    echo.
    pause
    exit /b 1
)

echo  Starting admin server...
echo  The dashboard will open automatically in your browser.
echo.
echo  Keep this window open while using the dashboard.
echo  Press Ctrl+C to stop the server when done.
echo.
echo  ========================================
echo.

REM Run the server (it will open the browser automatically)
python admin_server.py

echo.
echo  Server stopped.
pause
