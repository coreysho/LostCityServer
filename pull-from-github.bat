@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  Pull the latest from your GitHub forks into C:\LostCityServer
REM  (e.g. changes pushed from your gaming PC). Safe to re-run.
REM  Checks for local uncommitted changes before touching anything,
REM  so it won't silently clobber work done on this machine.
REM ============================================================

echo.
echo ==================================================
echo  1/4  Orchestrator: coreysho/LostCityServer -^> C:\LostCityServer
echo ==================================================
cd /d C:\LostCityServer
echo Local uncommitted changes here (should be empty - if not, stop and
echo tell Claude before continuing, so nothing gets lost):
git status --short
echo.
pause
git fetch origin
git merge origin/main -m "Merge latest from GitHub"
echo.
pause

echo.
echo ==================================================
echo  2/4  Content: coreysho/Content -^> C:\LostCityServer\content
echo ==================================================
cd /d C:\LostCityServer\content
echo Local uncommitted changes here:
git status --short
echo.
pause
git fetch origin
git merge origin/377-wip -m "Merge latest from GitHub"
echo.
pause

echo.
echo ==================================================
echo  3/4  Engine: coreysho/Engine-TS -^> C:\LostCityServer\engine
echo ==================================================
cd /d C:\LostCityServer\engine
echo Local uncommitted changes here:
git status --short
echo.
pause
git fetch origin
git merge origin/377-wip -m "Merge latest from GitHub"
echo.
pause

echo.
echo ==================================================
echo  4/4  Java client: coreysho/Client-Java -^> C:\LostCityServer\javaclient
echo ==================================================
cd /d C:\LostCityServer\javaclient
echo Local uncommitted changes here:
git status --short
echo.
pause
git fetch origin
git merge origin/377 -m "Merge latest from GitHub"

echo.
echo ==================================================
echo  Done pulling. If content or engine changed, delete the compiled
echo  cache before you next start the server, or it'll keep using the
echo  old data:
echo.
echo    rmdir /s /q C:\LostCityServer\engine\data\pack
echo.
echo  Then start the server as usual (node start.js -^> Continue startup).
echo ==================================================
pause
