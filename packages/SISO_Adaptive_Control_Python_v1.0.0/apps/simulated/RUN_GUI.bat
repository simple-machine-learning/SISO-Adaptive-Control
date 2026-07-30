@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0..\..\common;%PYTHONPATH%"
py HONU_MRAC_GUI_PySide6.py
if errorlevel 1 pause
endlocal
