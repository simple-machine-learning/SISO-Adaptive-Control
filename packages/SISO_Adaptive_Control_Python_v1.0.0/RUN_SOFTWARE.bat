@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0common;%PYTHONPATH%"
py launcher.py
if errorlevel 1 pause
endlocal
