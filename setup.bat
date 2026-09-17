@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (py -3 -m venv .venv 2>nul || python -m venv .venv)
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\doctor.py
endlocal
