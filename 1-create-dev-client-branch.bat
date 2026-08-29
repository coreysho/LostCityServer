@echo off
REM Creates (or switches to, if it already exists) a "dev-client" branch in your
REM Client-Java checkout, branched off your current 377 branch. Doesn't touch 377
REM at all - it stays exactly as-is. Run this, then tell Claude you've run it so
REM the modified files can be dropped in on top of this branch.
cd /d C:\LostCityServer\javaclient
git status --short
echo.
echo (the above should be empty - if it's not, stop and tell Claude what it shows)
echo.
pause
git checkout dev-client 2>nul || git checkout -b dev-client
echo.
echo Now on branch:
git branch --show-current
echo.
echo Done - tell Claude you're on the dev-client branch.
pause
