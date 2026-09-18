"""Kairn's single-cell GitHub launcher. Uses only stdlib before setup."""
import json
import hashlib
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
    "kaggle_gateway.py", "localization.py",
)


def message(language, portuguese, english):
    return english if language == "en" else portuguese


def fetch_runtime(repository, commit, destination, language="pt-BR", manifest=None):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError(message(language, "Repositório inválido.", "Invalid repository."))
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError(message(language, "Use SHA completo do commit resolvido pelo launcher.", "Use the full commit SHA resolved by the launcher."))
    destination.mkdir(parents=True, exist_ok=True)
    for filename in RUNTIME_FILES:
        url = f"https://raw.githubusercontent.com/{repository}/{commit}/{filename}"
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                content = response.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(message(language,
                f"Arquivo {filename} indisponível no GitHub (HTTP {exc.code}). Publique projeto completo no Kairn.",
                f"File {filename} unavailable on GitHub (HTTP {exc.code}). Publish the complete project to Kairn.")) from exc
        if manifest is not None and hashlib.sha256(content).hexdigest() != manifest.get("files", {}).get(filename):
            raise RuntimeError(message(language,
                f"Arquivos publicados incompatíveis: {filename}. Gere runtime-manifest.json e publique projeto completo.",
                f"Published files do not match: {filename}. Regenerate runtime-manifest.json and publish the complete project."))
        compile(content, filename, "exec")
        target = destination / filename
        partial = target.with_suffix(".tmp")
        partial.write_bytes(content)
        partial.replace(target)


def run_managed(command, env=None, language="pt-BR"):
    process = subprocess.Popen(command, env=env, start_new_session=True)
    try:
        code = process.wait()
        if code:
            raise RuntimeError(message(language, f"Kairn encerrou com código {code}. Veja diagnóstico acima.", f"Kairn exited with code {code}. See the diagnostics above."))
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
        raise ValueError(message(state.language,
            f"Modelo {state.model!r} ausente nesta versão ({directory.name[:12]}). Publique catálogo/runtime atualizados no Kairn e execute célula novamente.",
            f"Model {state.model!r} missing from this version ({directory.name[:12]}). Publish the updated Kairn catalog/runtime and rerun the cell."))
    state.backend = MODELS[state.model].get("required_backend") or state.backend
    if state.backend not in {"auto", "official-layer", "official-tensor", "ik_llama", "wackmall", "prism-ml"}:
        raise ValueError(message(state.language, "Backend desconhecido.", "Unknown backend."))
    builder = RuntimeBuilder(directory)
    source = builder.runtime_source(MODELS[state.model], state)
    exec(compile(builder.install_cell(state.language), "<Kairn setup>", "exec"), {})
    runtime = directory / "runtime.py"
    runtime.write_text(source, "utf-8")
    runtime.chmod(0o600)


def launch(config, repository, commit, manifest=None):
    language = config.get("language", "pt-BR")
    directory = Path("/kaggle/working/.kairn") / commit
    fetch_runtime(repository, commit, directory, language, manifest)
    config_path = directory / "config.json"
    config_path.write_text(json.dumps(config), "utf-8")
    config_path.chmod(0o600)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    print(f"Kairn {commit[:12]} · {config.get('backend', 'official-layer')}", flush=True)
    run_managed([sys.executable, "-u", __file__, "--prepare", str(directory), str(config_path)], env, language)
    env["KAGGLE_TUNNEL_MODE"] = config.get("tunnel_mode", "quick")
    env["KAGGLE_TUNNEL_URL"] = config.get("tunnel_url", "")
    if env["KAGGLE_TUNNEL_MODE"] == "named":
        from getpass import getpass
        if not env["KAGGLE_TUNNEL_URL"].startswith("https://"):
            raise ValueError(message(language, "Informe URL HTTPS do túnel nomeado.", "Enter the named tunnel HTTPS URL."))
        env["TUNNEL_TOKEN"] = env.get("TUNNEL_TOKEN") or getpass(message(language, "Token Cloudflare (oculto): ", "Cloudflare token (hidden): "))
    python = "/kaggle/working/.kaggle-runtime-venv/bin/python"
    try:
        run_managed([python, "-u", str(directory / "runtime.py")], env, language)
    except KeyboardInterrupt:
        print(message(language, "Runtime, gateway e túnel encerrados. Modelo permanece em cache.", "Runtime, gateway and tunnel stopped. Model remains cached."))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--prepare":
        prepare(Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text("utf-8")))
    else:
        launch(CONFIG, KAIRN_REPOSITORY, KAIRN_COMMIT, globals().get("KAIRN_MANIFEST"))
