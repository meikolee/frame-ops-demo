@echo off
setlocal
cd /d "%~dp0"

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm not found. Install Node.js 20+.
  pause
  exit /b 1
)

if not exist "node_modules\" (
  echo First run: npm install ...
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
)

echo Starting API (:8787) and Web (:3088) ...
start "FRAME API" cmd /k "cd /d "%~dp0" && npm run dev:api"
timeout /t 2 /nobreak >nul
start "FRAME Web" cmd /k "cd /d "%~dp0" && npm run dev:web"

echo.
echo Opened two terminal windows.
echo   API health: http://localhost:8787/api/health
echo   Home ZH:    http://localhost:3088/zh
echo   Guide ZH:   http://localhost:3088/zh/guide
echo.
pause
exit /b 0
