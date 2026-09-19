#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -c 'import PyQt6,httpx' >/dev/null 2>&1 || .venv/bin/python -m pip install -r requirements.txt
exec .venv/bin/python main.py
