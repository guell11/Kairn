# Kaggle: Internet ON, GPU T4 x2. Execute somente esta célula.
import json, runpy, urllib.request, urllib.error
from pathlib import Path

REPOSITORY = "guell11/Kairn"
REF = "main"  # Pode ser tag ou SHA de versão publicada.
CONFIG = {'model': 'gemopus', 'context': 16384, 'parallel': 2, 'output': 8192, 'mtp_tokens': 2, 'temperature': 0.6, 'top_k': 40, 'top_p': 0.95, 'min_p': 0.05, 'backend': 'official-layer', 'reasoning_budget': 3072, 'accelerator': 't4x2', 'parallel_auto': True, 'tunnel_mode': 'quick', 'tunnel_url': ''}

try:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/commits/{REF}",
        headers={"User-Agent": "Kairn-Kaggle"})
    with urllib.request.urlopen(request, timeout=30) as response:
        commit = json.load(response)["sha"]
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{commit}/kaggle/bootstrap.py"
    with urllib.request.urlopen(url, timeout=60) as response:
        source = response.read()
except urllib.error.HTTPError as error:
    raise RuntimeError(f"Kairn indisponível no GitHub (HTTP {error.code}). Publique projeto completo e confira REF.") from error

compile(source, "bootstrap.py", "exec")
folder = Path("/kaggle/working/.kairn") / commit
folder.mkdir(parents=True, exist_ok=True)
bootstrap = folder / "bootstrap.py"
bootstrap.write_bytes(source)
runpy.run_path(str(bootstrap), run_name="__main__", init_globals={
    "CONFIG": CONFIG, "KAIRN_REPOSITORY": REPOSITORY, "KAIRN_COMMIT": commit})
