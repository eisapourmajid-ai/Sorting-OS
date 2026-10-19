@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3.8 main.py
  if not errorlevel 1 goto :eof
)
python main.py
