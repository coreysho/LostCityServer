@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  Push everything under C:\LostCityServer to your own GitHub
REM  forks. Run this AFTER you've forked the three repos below.
REM  Safe to re-run - each step is idempotent (remote add/rename
REM  no-ops if already done).
REM ============================================================

echo.
echo ==================================================
echo  1/4  Orchestrator: C:\LostCityServer -^> coreysho/LostCityServer
echo ==================================================
cd /d C:\LostCityServer
git remote add origin https://github.com/coreysho/LostCityServer.git 2>nul
git fetch origin
echo.
echo Merging your fork's existing history with what's on disk here...
git merge origin/main --allow-unrelated-histories -m "Merge existing fork history"
if errorlevel 1 (
    echo.
    echo *** Merge conflict. Open the conflicting files listed above, fix them,
    echo *** then run: git add -A  ^&^&  git commit
    echo *** ...and re-run this script to continue with the other repos.
    pause
    exit /b 1
)
git push -u origin main
echo.
pause

echo.
echo ==================================================
echo  2/4  Content: C:\LostCityServer\content -^> coreysho/Content
echo ==================================================
cd /d C:\LostCityServer\content
git remote rename origin upstream 2>nul
git remote add origin https://github.com/coreysho/Content.git 2>nul
echo.
echo Local changes to be committed (should include the smithing fix,
echo scripts\_unpack\727\all.inv):
git status --short
echo.
pause
git add -A
git commit -m "Sync local server state (incl. smithing anvil interface fix)"
git push -u origin 377-wip
echo.
pause

echo.
echo ==================================================
echo  3/4  Engine: C:\LostCityServer\engine -^> coreysho/Engine-TS
echo ==================================================
cd /d C:\LostCityServer\engine
git remote rename origin upstream 2>nul
git remote add origin https://github.com/coreysho/Engine-TS.git 2>nul
echo.
echo Local changes to be committed (should be empty or near-empty -
echo .env, db.sqlite, and data/ are gitignored and won't be included):
git status --short
echo.
pause
git add -A
git commit -m "Sync local server state"
git push -u origin 377-wip
echo.
pause

echo.
echo ==================================================
echo  4/4  Java client: C:\LostCityServer\javaclient -^> coreysho/Client-Java
echo ==================================================
cd /d C:\LostCityServer\javaclient
git remote rename origin upstream 2>nul
git remote add origin https://github.com/coreysho/Client-Java.git 2>nul
echo.
git status --short
echo.
pause
git add -A
git commit -m "Sync local server state"
git push -u origin 377

echo.
echo ==================================================
echo  Done. Each repo now has an "origin" remote pointing at your
echo  fork and an "upstream" remote (engine/content/javaclient only)
echo  pointing back at LostCityRS, so you can still pull updates with
echo  "git fetch upstream" later.
echo ==================================================
pause
