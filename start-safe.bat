@echo off
cd /d "%~dp0"
node start.js
echo.
echo ============ node start.js exited with code %errorlevel% ============
pause
