@echo off
REM Start Vmix Monitor GUI (No pause, window closes after exit)
cd /d "%~dp0"
start "" pythonw vmix_monitor_gui.py
