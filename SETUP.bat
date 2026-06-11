@echo off
title LeetCode Automation Setup
color 0A
echo.
echo  ==========================================
echo    LeetCode Daily Automation - Setup
echo  ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found! Please install Python 3.8+
    pause
    exit /b 1
)
echo  [OK] Python found

:: Install requirements
echo  [..] Installing dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo  [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo  [OK] Dependencies installed

:: Open config for editing
echo.
echo  ==========================================
echo   IMPORTANT: Edit config.json before running!
echo  ==========================================
echo.
echo   1. Open config.json
echo   2. Set your LeetCode username + password
echo   3. Set your Gmail + App Password
echo   4. Set receiver email address
echo.
start notepad config.json
echo  [..] config.json opened in Notepad
echo.
echo  After saving config.json, press any key to:
echo   - Register Windows Scheduled Task (runs at 8AM daily)
echo   - Run the automation NOW for first test
echo.
pause

:: Register scheduled task (run as admin for full support)
echo  [..] Registering Windows Scheduled Task...
python setup_scheduler.py

echo.
echo  [..] Running automation now for first time...
echo  (This will solve 5 problems and send you an email)
echo.
python main.py

echo.
echo  ==========================================
echo   Setup Complete!
echo  ==========================================
echo.
echo   - Automation runs daily at 8:00 AM
echo   - Logs: logs\automation.log
echo   - To change time: edit config.json (run_time)
echo   - To unregister: python setup_scheduler.py --unregister
echo.
pause
