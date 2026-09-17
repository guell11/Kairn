$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) { py -3 -m venv .venv }
try { & .venv\Scripts\python.exe -c "import PyQt6,httpx" } catch { & .venv\Scripts\python.exe -m pip install -r requirements.txt }
& .venv\Scripts\python.exe main.py
