"""Kairn's single-cell GitHub launcher. Uses only stdlib before setup."""
import json
import os
import re
import signal
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

RUNTIME_FILES = (
    "agent_prompt.py", "models_catalog.py", "state_store.py", "runtime_builder.py",
    "runtime_support.py", "prebuilt_support.py", "kaggle_runtime_template.py",
    "kaggle_gateway.py",
)


def fetch_runtime(repository, commit, destination):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Repositório inválido.")
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Use SHA completo do commit resolvido pelo launcher.")
    destination.mkdir(parents=True, exist_ok=True)
    for filename in RUNTIME_FILES:
        url = f"https://raw.githubusercontent.com/{repository}/{commit}/{filename}"
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                content = response.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Arquivo {filename} indisponível no GitHub (HTTP {exc.code}). Publique projeto completo no Kairn.") from exc
        compile(content, filename, "exec")
        target = destination / filename
        partial = target.with_suffix(".tmp")
        partial.write_bytes(content)
        partial.replace(target)


def run_managed(command, env=None):
    process = subprocess.Popen(command, env=env, start_new_session=True)
    try:
        code = process.wait()
        if code:
            raise RuntimeError(f"Kairn encerrou com código {code}. Veja diagnóstico acima.")
    finally:
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=15)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def prepare(directory, config):
    # Runs in a fresh interpreter: notebook reruns cannot reuse stale modules.
    sys.path.insert(0, str(directory))
    from models_catalog import MODELS
    from runtime_builder import RuntimeBuilder
    from state_store import AppState
    state = AppState(**{key: value for key, value in config.items() if key in AppState.__dataclass_fields__})
    if state.model not in MODELS:
        raise ValueError("Modelo desconhecido.")
    if state.backend not in {"auto", "official-layer", "official-tensor", "ik_llama", "wackmall"}:
        raise ValueError("Backend desconhecido.")
    builder = RuntimeBuilder(directory)
    source = builder.runtime_source(MODELS[state.model], state)
    exec(compile(builder.install_cell(), "<Kairn setup>", "exec"), {})
    runtime = directory / "runtime.py"
    runtime.write_text(source, "utf-8")
    runtime.chmod(0o600)


def launch(config, repository, commit):
    directory = Path("/kaggle/working/.kairn") / commit
    fetch_runtime(repository, commit, directory)
    config_path = directory / "config.json"
    config_path.write_text(json.dumps(config), "utf-8")
    config_path.chmod(0o600)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    print(f"Kairn {commit[:12]} · {config.get('backend', 'official-layer')}", flush=True)
    run_managed([sys.executable, "-u", __file__, "--prepare", str(directory), str(config_path)], env)
    env["KAGGLE_TUNNEL_MODE"] = config.get("tunnel_mode", "quick")
    env["KAGGLE_TUNNEL_URL"] = config.get("tunnel_url", "")
    if env["KAGGLE_TUNNEL_MODE"] == "named":
        from getpass import getpass
        if not env["KAGGLE_TUNNEL_URL"].startswith("https://"):
            raise ValueError("Informe URL HTTPS do túnel nomeado.")
        env["TUNNEL_TOKEN"] = env.get("TUNNEL_TOKEN") or getpass("Token Cloudflare (oculto): ")
    python = "/kaggle/working/.kaggle-runtime-venv/bin/python"
    try:
        run_managed([python, "-u", str(directory / "runtime.py")], env)
    except KeyboardInterrupt:
        print("Runtime, gateway e túnel encerrados. Modelo permanece em cache.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--prepare":
        prepare(Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text("utf-8")))
    else:
        launch(CONFIG, KAIRN_REPOSITORY, KAIRN_COMMIT)
