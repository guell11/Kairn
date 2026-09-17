from __future__ import annotations
import importlib.util, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def has(module:str)->bool:
    try:return importlib.util.find_spec(module) is not None
    except (ImportError,ModuleNotFoundError):return False
checks=[('Python >= 3.10',sys.version_info>=(3,10)),('ui/index.html',(ROOT/'ui'/'index.html').exists()),('runtime template',(ROOT/'kaggle_runtime_template.py').exists()),('universal gateway',(ROOT/'kaggle_gateway.py').exists()),('PyQt6',has('PyQt6')),('PyQt6-WebEngine',has('PyQt6') and has('PyQt6.QtWebEngineWidgets')),('httpx',has('httpx'))]
print('Kaggle Studio doctor\n')
for name,ok in checks:print(('OK' if ok else 'FAIL'),name)
print('\nCLIs detectadas')
for name in ('codex','claude','opencode','zcode','zcodex'):print(('OK' if shutil.which(name) else '--'),name,shutil.which(name) or '')
# Project structure is fatal; optional desktop deps are installed by setup/run scripts.
sys.exit(0 if all(ok for _,ok in checks[:4]) else 1)
