@echo off
REM Radiant Node GUI Launcher (Windows)

cd /d "%~dp0"
python radiant_node_web.py
if errorlevel 1 (
    echo.
    echo Error: Python 3 is required to run this application.
    echo Please install Python 3 from https://www.python.org/downloads/
    pause
)
