@echo off
setlocal
cd /d "%~dp0"
echo Starting interview tree in Python mode (not EXE)...
call "%~dp0interview-tree-desktop\start.bat"
exit /b %ERRORLEVEL%
