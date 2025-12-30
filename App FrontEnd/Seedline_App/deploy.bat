@echo off
echo ========================================
echo   Deploying Seedline to Firebase
echo ========================================
echo.

echo Step 1: Cleaning dist folder...
if exist dist (
    rmdir /s /q dist 2>nul
    if exist dist (
        echo Dist folder locked, waiting 2 seconds...
        timeout /t 2 /nobreak >nul
        rmdir /s /q dist 2>nul
    )
    if exist dist (
        echo Still locked, trying PowerShell...
        powershell -Command "Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue"
    )
)

echo Step 2: Building app...
call npm run build
if errorlevel 1 (
    echo.
    echo Build failed! Try closing any file explorer windows
    echo or wait a moment for Dropbox to finish syncing.
    pause
    exit /b 1
)

echo.
echo Step 3: Deploying to Firebase...
call firebase deploy --only hosting

echo.
echo ========================================
echo   Deploy complete!
echo   View at: https://seedline-app.web.app
echo ========================================
pause
