@echo off
cd /d "%~dp0"
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=pomodoro.ico --add-data "ringtone.mp3;." --name 番茄鐘 pomodoro.py
echo.
echo Build complete! Executable is in the dist\ folder.
pause
