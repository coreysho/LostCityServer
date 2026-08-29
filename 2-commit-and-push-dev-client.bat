@echo off
REM Run this AFTER Claude has delivered the modified files onto the dev-client
REM branch. Commits them, pushes the dev-client branch to your fork, then
REM switches you back to 377 so your normal/main checkout is untouched.
cd /d C:\LostCityServer\javaclient
echo Changed files (should be ViewBox.java, PixMap.java, GameShell.java, Client.java):
git status --short
echo.
pause
git add -A
git commit -m "Dev build: resizable/scaled window + FPS/coords overlay"
git push -u origin dev-client
echo.
echo Switching back to your normal 377 branch...
git checkout 377
echo.
echo Done. dev-client is pushed to your fork but NOT merged into 377 -
echo your normal checkout is back to stock. To play with the resizable
echo build later: cd C:\LostCityServer\javaclient ^&^& git checkout dev-client
echo (then rebuild/relaunch the java client). "git checkout 377" switches back.
pause
