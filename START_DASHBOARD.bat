@echo off
title LeetCode Dashboard
color 0B
echo.
echo  ==========================================
echo    LeetCode Automation Dashboard
echo  ==========================================
echo.

:: Get local IP for phone access
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "127.0.0.1"') do (
    set IP=%%a
    goto :gotip
)
:gotip
set IP=%IP: =%

echo  Starting dashboard server...
echo.
echo  ─────────────────────────────────────────
echo   Open on your phone (same WiFi):
echo   http://%IP%:5050
echo  ─────────────────────────────────────────
echo.
echo  Or on this PC: http://localhost:5050
echo.

:: Open browser on this PC
timeout /t 2 /nobreak >nul
start "" http://localhost:5050

:: Start the server
python dashboard\server.py

pause
