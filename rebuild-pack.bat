@echo off
REM Deletes the stale engine cache so it rebuilds from the latest content
REM (including the Regicide files pulled down from GitHub). Make sure the
REM server is NOT running before you run this.
echo This will delete the cached pack data at:
echo   C:\LostCityServer\engine\data\pack
echo Make sure the server console is closed first.
echo.
pause
rd /s /q "C:\LostCityServer\engine\data\pack"
echo.
echo Done. Pack folder deleted - it will rebuild automatically next time
echo you start the server (this may take a bit longer than usual on that
echo first startup).
pause
