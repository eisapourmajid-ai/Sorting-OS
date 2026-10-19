@echo off
setlocal
REM Build on the target Windows machine using a Windows-7-compatible Python/PyInstaller toolchain.
REM Exact Windows 7 compatibility must be validated on a real Windows 7 SP1 x64 installation.
cd /d "%~dp0"
python -m pip install --upgrade "pip<22" "setuptools<60" "pyinstaller==4.10"
pyinstaller --noconfirm --clean --onefile --windowed --name SORTING_OS main.py
if errorlevel 1 exit /b 1
echo Build output: dist\SORTING_OS.exe
