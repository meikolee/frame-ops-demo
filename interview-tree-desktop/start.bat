@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] python not found. Install Python 3.10+ and add it to PATH.
  pause
  exit /b 1
)

echo Checking tkinter ...
python -c "import tkinter" 2>nul
if errorlevel 1 (
  echo [ERROR] tkinter missing. Reinstall official Python from python.org and enable tcl/tk.
  pause
  exit /b 1
)

echo Checking dependencies...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed.
  pause
  exit /b 1
)

echo Starting interview tree desktop (python app.py) ...
python app.py
set ERR=%ERRORLEVEL%
if not "%ERR%"=="0" (
  echo [ERROR] app exited with code %ERR%
  pause
  exit /b %ERR%
)
exit /b 0
