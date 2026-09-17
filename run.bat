@echo off
setlocal
cd /d "%~dp0"
if not exist ".kaggle-studio" mkdir ".kaggle-studio"

if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 -m venv ".venv"
  ) else (
    where python >nul 2>&1
    if errorlevel 1 goto :no_python
    python -m venv ".venv"
  )
  if errorlevel 1 goto :failed
)

".venv\Scripts\python.exe" -c "import httpx; from PyQt6.QtWebEngineWidgets import QWebEngineView" >nul 2>&1
if errorlevel 1 (
  echo Instalando dependencias...
  ".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
  if errorlevel 1 goto :failed
)

echo Iniciando Kaggle Studio...
".venv\Scripts\python.exe" "main.py" 2>".kaggle-studio\startup-error.log"
if errorlevel 1 goto :app_failed
exit /b 0

:no_python
echo Python 3 nao encontrado. Instale Python 3.12 e tente novamente.
pause
exit /b 1

:app_failed
echo Falha ao abrir. Log: %CD%\.kaggle-studio\startup-error.log
type ".kaggle-studio\startup-error.log"
pause
exit /b 1

:failed
echo Falha ao preparar Kaggle Studio.
pause
exit /b 1
