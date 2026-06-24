@echo off
cd /d "%~dp0"
pip install pyinstaller
pyinstaller pomodoro.spec
echo.
echo Build complete! Executable is in the dist\ folder.
pause
