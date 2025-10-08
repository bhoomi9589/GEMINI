@echo off
echo ========================================
echo   Pushing to GitHub: GEMINI Repository
echo ========================================
echo.

cd /d %~dp0

echo [1/4] Checking Git status...
git status
echo.

echo [2/4] Adding all files...
git add .
echo.

echo [3/4] Committing changes...
set /p commit_message="Enter commit message (or press Enter for default): "
if "%commit_message%"=="" set commit_message=Update: Enhanced UI with video feed and session controls

git commit -m "%commit_message%"
echo.

echo [4/4] Pushing to GitHub...
git push origin main
if errorlevel 1 (
    echo.
    echo Push to 'main' failed. Trying 'master'...
    git push origin master
)
echo.

echo ========================================
echo   Push Complete!
echo ========================================
echo.
echo Next Steps:
echo 1. Go to: https://share.streamlit.io/
echo 2. Find your app: livecam123456789.streamlit.app
echo 3. Settings ^> Change main file to: app.py
echo 4. Add GEMINI_API_KEY to Secrets
echo 5. Reboot app
echo.
pause
