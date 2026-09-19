# Kaggle: Internet ON, GPU T4 x2. Execute somente esta célula.
import hashlib, json, runpy, urllib.request, urllib.error
from pathlib import Path

REPOSITORY = "guell11/Kairn"
REF = "main"  # Pode ser tag ou SHA de versão publicada.
CONFIG = {'language': 'pt-BR', 'model': 'gemopus', 'context': 16384, 'parallel': 2, 'output': 8192, 'mtp_tokens': 2, 'speculation': 'auto', 'temperature': 0.6, 'top_k': 40, 'top_p': 0.95, 'min_p': 0.05, 'backend': 'official-layer', 'reasoning_budget': 3072, 'accelerator': 't4x2', 'parallel_auto': True, 'tunnel_mode': 'quick', 'tunnel_url': ''}
EXPECTED_MODEL_SHA256 = '2037b8c978db6c8b947d10e34a70f410dde6301919c6040624fdda50647f7940'

def source_sha256(payload):
    payload = payload.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(payload).hexdigest()

def incompatible(detail):
    english = CONFIG.get("language") == "en"
    message = ("Kairn on GitHub is older than this launcher. Publish the complete updated project (including runtime-manifest.json), then rerun this cell. "
               if english else "Kairn no GitHub está anterior a esta célula. Publique projeto completo atualizado (incluindo runtime-manifest.json) e execute célula novamente. ")
    raise RuntimeError(message + detail)

try:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/commits/{REF}",
        headers={"User-Agent": "Kairn-Kaggle"})
    with urllib.request.urlopen(request, timeout=30) as response:
        commit = json.load(response)["sha"]
    manifest_url = f"https://raw.githubusercontent.com/{REPOSITORY}/{commit}/runtime-manifest.json"
    try:
        with urllib.request.urlopen(manifest_url, timeout=30) as response:
            manifest = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            incompatible(f"Commit: {commit[:12]}")
        raise
    entry = manifest.get("models", {}).get(CONFIG["model"], {})
    if (manifest.get("schema") != 2 or entry.get("sha256") != EXPECTED_MODEL_SHA256
            or CONFIG["backend"] not in manifest.get("backends", [])):
        incompatible(f"Commit: {commit[:12]}; model: {CONFIG['model']}")
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{commit}/kaggle/bootstrap.py"
    with urllib.request.urlopen(url, timeout=60) as response:
        source = response.read()
except urllib.error.HTTPError as error:
    raise RuntimeError(f"Kairn indisponível no GitHub (HTTP {error.code}). Publique projeto completo e confira REF.") from error

if source_sha256(source) != manifest.get("files", {}).get("kaggle/bootstrap.py"):
    incompatible("bootstrap.py checksum mismatch")
compile(source, "bootstrap.py", "exec")
folder = Path("/kaggle/working/.kairn") / commit
folder.mkdir(parents=True, exist_ok=True)
bootstrap = folder / "bootstrap.py"
bootstrap.write_bytes(source)
runpy.run_path(str(bootstrap), run_name="__main__", init_globals={
    "CONFIG": CONFIG, "KAIRN_REPOSITORY": REPOSITORY, "KAIRN_COMMIT": commit, "KAIRN_MANIFEST": manifest})
