@echo off
setlocal
cd /d "%~dp0interview-tree-desktop"

where powershell >nul 2>nul
if errorlevel 1 (
  echo [ERROR] powershell not found.
  pause
  exit /b 1
)

echo Building FrameInterviewTree.exe ...
echo Close any running FrameInterviewTree.exe first.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0interview-tree-desktop\build_exe.ps1"
set ERR=%ERRORLEVEL%
echo.
if not "%ERR%"=="0" (
  echo [ERROR] build failed with code %ERR%
  pause
  exit /b %ERR%
)

echo Build finished.
echo - interview-tree-desktop\dist\FrameInterviewTree.exe
echo - FrameInterviewTree.exe  (repo root copy, if overwrite succeeded)
pause
exit /b 0
