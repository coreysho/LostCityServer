@echo off
title RS2 Dev Client Console
echo ============================================
echo  RS2 Dev Client
echo  Logs every menu action, chat message, and
echo  login/logout to this window and to
echo  dev-client.log (next to this script).
echo ============================================
echo.

if not exist "build\libs\rs2client-dev.jar" (
    echo build\libs\rs2client-dev.jar not found - run gradlew.bat build first.
    pause
    exit /b 1
)

java -jar build\libs\rs2client-dev.jar

echo.
echo Client exited. Press any key to close this window.
pause >nul
