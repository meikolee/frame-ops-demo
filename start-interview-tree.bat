@echo off
setlocal
cd /d "%~dp0"

if exist "%~dp0FrameInterviewTree.exe" (
  echo Starting FrameInterviewTree.exe ...
  start "FRAME Interview Tree" /D "%~dp0" "FrameInterviewTree.exe"
  exit /b 0
)

if exist "%~dp0interview-tree-desktop\dist\FrameInterviewTree.exe" (
  echo Starting dist\FrameInterviewTree.exe ...
  start "FRAME Interview Tree" /D "%~dp0interview-tree-desktop\dist" "FrameInterviewTree.exe"
  exit /b 0
)

echo EXE not found. Falling back to Python mode...
call "%~dp0interview-tree-desktop\start.bat"
exit /b %ERRORLEVEL%
