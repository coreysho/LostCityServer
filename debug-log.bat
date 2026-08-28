@echo off
cd /d "%~dp0"
(
  echo === where git ===
  where git
  echo === where npm ===
  where npm
  echo === node --version ===
  node --version
  echo === npm --version ===
  npm --version
  echo === npm install ===
  call npm install
  echo NPM_INSTALL_EXIT=%errorlevel%
) > debug-log.txt 2>&1
