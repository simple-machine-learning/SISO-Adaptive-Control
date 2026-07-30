@echo off
setlocal
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 pause
endlocal
