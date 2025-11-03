@echo off
REM Launcher script for Seasonal Baking Tracker (Windows)

cd /d "%~dp0"
venv\Scripts\python.exe run.py
pause
