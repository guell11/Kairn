from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from agent_prompt import managed_agent_instructions

MANAGED_BEGIN = "# >>> kaggle-studio managed >>>"
MANAGED_END = "# <<< kaggle-studio managed <<<"
PROMPT_BEGIN = "<!-- >>> kaggle-studio managed >>> -->"
PROMPT_END = "<!-- <<< kaggle-studio managed <<< -->"
CODEX_PROVIDER = "kaggle_studio"
CODEX_PROFILE = "kaggle-studio"
CODEX_TOKEN_FILE = ".kaggle-studio-token"
CODEX_TOKEN_READER = "kaggle-studio-token.py"
CODEX_PROFILE_FILE = "kaggle-studio.config.toml"
CLAUDE_TOKEN_FILE = ".kaggle-studio-claude-token"
CLAUDE_TOKEN_READER = "kaggle-studio-api-key.py"
OPENCODE_TOKEN_FILE = ".kaggle-studio-opencode-token"

# Gateway surface.  Keep client setup tied to the public gateway contract,
# rather than to whichever upstream server happens to run in Kaggle.
API_PATHS = {
    "chat_completions": "/v1/chat/completions",
    "responses": "/v1/responses",
    "messages": "/v1/messages",
    "health": "/health",
    "metrics": "/metrics",
}
TOOL_COMMANDS = {
    "codex": ("codex",),
    "claude": ("claude",),
    "opencode": ("opencode",),
    "zcode": ("zcode", "zcodex"),
}


@dataclass(frozen=True)
class Endpoint:
    base_url: str
    api_key: str
    model: str
    context: int = 16384
    output: int = 8192

    @property
    def root_url(self) -> str:
        return self.api_url.removesuffix("/v1")

    @property
    def api_url(self) -> str:
        value = self.base_url.strip().rstrip("/")
        return value if value.endswith("/v1") else value + "/v1"

    def url_for(self, capability: str) -> str:
        try:
            path = API_PATHS[capability]
        except KeyError as exc:
            raise ValueError(f"Capacidade desconhecida: {capability}") from exc
        return self.root_url + path


@dataclass
class Result:
    tool: str
    ok: bool
    path: str
    message: str
    backup: str = ""

    def dict(self) -> dict:
        return self.__dict__.copy()


def find_tool(tool: str) -> str | None:
    """Resolve only supported installed clients, including Windows scripts."""
    for command in TOOL_COMMANDS.get(tool, ()):
        found = shutil.which(command)
        if found:
            return found
        if os.name == "nt":
            for suffix in (".exe", ".cmd", ".bat", ".ps1"):
                found = shutil.which(command + suffix)
                if found:
                    return found
    return None


def launch_argv(executable: str, args: list[str] | tuple[str, ...] = ()) -> list[str]:
    """Build an argv safe for native executables and Windows wrapper files."""
    command = [executable, *args]
    if os.name != "nt":
        return command
    suffix = Path(executable).suffix.lower()
    if suffix == ".ps1":
        return [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            *command,
        ]
    if suffix in {".cmd", ".bat"}:
        return ["cmd.exe", "/d", "/s", "/c", "call " + subprocess.list2cmdline(command)]
    return command


def _backup(path: Path) -> str:
    if not path.exists():
        return ""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(path.name + f".kaggle-studio-{stamp}.bak")
    counter = 1
    while dest.exists():
        dest = path.with_name(path.name + f".kaggle-studio-{stamp}-{counter}.bak")
        counter += 1
    shutil.copy2(path, dest)
    return str(dest)


def _write(path: Path, text: str, *, secret: bool = False, backup: bool = True) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    old = None
    if path.exists():
        try:
            old = path.read_text("utf-8")
        except OSError:
            old = None
    if old == text:
        if secret:
            _restrict(path)
        return ""
    bak = _backup(path) if backup and path.exists() else ""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, "utf-8")
    os.replace(tmp, path)
    if secret:
        _restrict(path)
    return bak


def _restrict(path: Path) -> None:
    if os.name == "nt":
        # chmod is not an ACL operation on NTFS.  Remove inherited grants and
        # leave only the current interactive account read/write access.
        username = os.environ.get("USERNAME")
        domain = os.environ.get("USERDOMAIN")
        account = f"{domain}\\{username}" if domain and username else username
        if not account:
            return
        try:
            subprocess.run(
                [
                    "icacls",
                    str(path),
                    "/inheritance:r",
                    "/grant:r",
                    f"{account}:(R,W)",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        return
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def _json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _existing_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Arquivo de configuração inválido: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Arquivo de configuração deve conter objeto JSON: {path}")
    return data


def _jsonc(path: Path) -> dict:
    try:
        raw = path.read_text("utf-8")
    except OSError:
        return {}
    # Conservative JSONC reader. We keep a backup before normalising it to JSON.
    raw = re.sub(r"/\*.*?\*/", "", raw, flags=re.S)
    raw = re.sub(r"(^|\s)//.*$", r"\1", raw, flags=re.M)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except ValueError:
        return {}


def _existing_jsonc(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        raw = path.read_text("utf-8")
    except OSError as exc:
        raise ValueError(f"Não foi possível ler configuração: {path}") from exc
    data = _jsonc(path)
    if not data and raw.strip() not in {"", "{}"}:
        raise ValueError(f"Arquivo de configuração inválido: {path}")
    return data


def _credential_reader(home: Path, token_name: str, reader_name: str) -> tuple[Path, Path]:
    token = home / token_name
    reader = home / reader_name
    source = (
        "from pathlib import Path\n"
        "import sys\n"
        f"value = Path({str(token)!r}).read_text(encoding='utf-8').strip()\n"
        "if not value:\n"
        "    raise SystemExit(1)\n"
        "sys.stdout.write(value)\n"
    )
    _write(reader, source, secret=True, backup=False)
    return token, reader


def _upsert_managed_text(source: str, payload: str) -> str:
    block = f"{PROMPT_BEGIN}\n{payload.rstrip()}\n{PROMPT_END}"
    pattern = re.compile(re.escape(PROMPT_BEGIN) + r".*?" + re.escape(PROMPT_END), re.S)
    if pattern.search(source):
        return pattern.sub(block, source).rstrip() + "\n"
    prefix = source.rstrip()
    return (prefix + ("\n\n" if prefix else "") + block + "\n")


def _remove_managed_text(source: str) -> str:
    pattern = re.compile(
        r"(?:\n|^)" + re.escape(PROMPT_BEGIN) + r".*?" + re.escape(PROMPT_END) + r"\n?",
        re.S,
    )
    remaining = pattern.sub("", source).rstrip()
    return remaining + ("\n" if remaining else "")


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)


def _update_root_toml(source: str, values: dict[str, object]) -> str:
    newline = "\r\n" if "\r\n" in source else "\n"
    lines = source.splitlines()
    root_end = next((i for i, line in enumerate(lines) if re.match(r"^\s*\[", line)), len(lines))
    seen: set[str] = set()
    for index in range(root_end):
        match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=", lines[index])
        if not match or match.group(1) not in values:
            continue
        key = match.group(1)
        lines[index] = f"{key} = {_toml_value(values[key])}"
        seen.add(key)
    missing = [f"{key} = {_toml_value(value)}" for key, value in values.items() if key not in seen]
    if missing:
        lines[root_end:root_end] = missing + ([""] if root_end == 0 else [])
    return newline.join(lines).rstrip() + newline


def _remove_toml_section(source: str, header: str) -> str:
    lines = source.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == header), -1)
    if start < 0:
        return source
    end = start + 1
    while end < len(lines) and not re.match(r"^\s*\[", lines[end]):
        end += 1
    del lines[start:end]
    return "\n".join(lines).rstrip() + "\n"


def _update_toml_section(
    source: str,
    header: str,
    values: dict[str, object],
    *,
    remove_keys: tuple[str, ...] = (),
) -> str:
    newline = "\r\n" if "\r\n" in source else "\n"
    lines = source.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == header), -1)
    canonical = [f"{key} = {_toml_value(value)}" for key, value in values.items()]
    if start < 0:
        out = source.rstrip()
        return f"{out}{newline + newline if out else ''}{header}{newline}{newline.join(canonical)}{newline}"
    end = start + 1
    while end < len(lines) and not re.match(r"^\s*\[", lines[end]):
        end += 1
    managed_keys = set(values) | set(remove_keys)
    preserved = []
    for line in lines[start + 1 : end]:
        match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=", line)
        if not match or match.group(1) not in managed_keys:
            preserved.append(line)
    lines[start + 1 : end] = canonical + preserved
    return newline.join(lines).rstrip() + newline


def _codex_token_reader(home: Path) -> tuple[Path, Path]:
    codex_home = home / ".codex"
    token_file = codex_home / CODEX_TOKEN_FILE
    reader = codex_home / CODEX_TOKEN_READER
    reader_source = f"""from pathlib import Path\nimport sys\nvalue = Path({str(token_file)!r}).read_text(encoding='utf-8').strip()\nif not value:\n    raise SystemExit(1)\nsys.stdout.write(value)\n"""
    _write(reader, reader_source, secret=True, backup=False)
    return token_file, reader


def configure_codex(ep: Endpoint, home: Path | None = None) -> Result:
    home = Path(home or Path.home())
    config = home / ".codex" / "config.toml"
    old = config.read_text("utf-8") if config.exists() else ""
    token_file, reader = _codex_token_reader(home)
    _write(token_file, ep.api_key.strip() + "\n", secret=True, backup=False)

    # Command-backed auth is supported by current Codex and lets Codex work even
    # when opened outside this app. It also avoids putting the bearer token in TOML.
    # Profile-v2 owns model selection.  Do not replace a user's default
    # model in config.toml merely because they launch this profile once.
    next_config = old
    # Current Codex profile-v2 loads profiles from <name>.config.toml. Remove
    # the legacy inline table because `codex --profile` now rejects that shape.
    next_config = _remove_toml_section(next_config, f"[profiles.{CODEX_PROFILE}]")
    next_config = _update_toml_section(
        next_config,
        f"[model_providers.{CODEX_PROVIDER}]",
        {
            "name": "Kaggle Studio",
            "base_url": ep.api_url,
            "wire_api": "responses",
            "request_max_retries": 4,
            "stream_max_retries": 5,
            "stream_idle_timeout_ms": 900000,
        },
        remove_keys=("env_key", "experimental_bearer_token", "requires_openai_auth"),
    )
    next_config = _update_toml_section(
        next_config,
        f"[model_providers.{CODEX_PROVIDER}.auth]",
        {
            "command": sys.executable,
            "args": [str(reader)],
            "refresh_interval_ms": 0,
            "timeout_ms": 5000,
        },
    )
    bak = _write(config, next_config)

    profile = home / ".codex" / CODEX_PROFILE_FILE
    profile_source = (
        f"model = {_toml_value(ep.model)}\n"
        f"model_provider = {_toml_value(CODEX_PROVIDER)}\n"
        f"model_context_window = {ep.context}\n"
    )
    profile_backup = _write(profile, profile_source)

    return Result(
        "codex",
        True,
        f"{config} + {profile}",
        "Codex apontado para Responses API com profile-v2; token protegido é lido por auth.command.",
        bak or profile_backup,
    )


def configure_claude(ep: Endpoint, home: Path | None = None) -> Result:
    home = Path(home or Path.home())
    config = home / ".claude" / "settings.json"
    data = _existing_json(config)
    token, reader = _credential_reader(home / ".claude", CLAUDE_TOKEN_FILE, CLAUDE_TOKEN_READER)
    _write(token, ep.api_key.strip() + "\n", secret=True, backup=False)
    env = data.setdefault("env", {})
    if not isinstance(env, dict):
        env = {}
        data["env"] = env
    env.update(
        {
            "ANTHROPIC_BASE_URL": ep.root_url,
            "ANTHROPIC_MODEL": ep.model,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": ep.model,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": ep.model,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": ep.model,
        }
    )
    data["apiKeyHelper"] = subprocess.list2cmdline([sys.executable, str(reader)])
    bak = _write(config, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    prompt = home / ".claude" / "CLAUDE.md"
    _write(prompt, _upsert_managed_text(prompt.read_text("utf-8") if prompt.exists() else "", managed_agent_instructions()))
    return Result(
        "claude",
        True,
        str(config),
        "Claude Code configurado para /v1/messages; apiKeyHelper lê token protegido local.",
        bak,
    )


def configure_opencode(ep: Endpoint, home: Path | None = None) -> Result:
    home = Path(home or Path.home())
    candidates = [home / ".config" / "opencode" / "opencode.jsonc", home / ".config" / "opencode" / "opencode.json"]
    config = next((item for item in candidates if item.exists()), candidates[0])
    data = _existing_jsonc(config)
    token = home / OPENCODE_TOKEN_FILE
    _write(token, ep.api_key.strip() + "\n", secret=True, backup=False)
    data.setdefault("$schema", "https://opencode.ai/config.json")
    providers = data.setdefault("provider", {})
    if not isinstance(providers, dict):
        providers = {}
        data["provider"] = providers
    existing = providers.get("kaggle-studio", {}) if isinstance(providers.get("kaggle-studio"), dict) else {}
    models = existing.get("models", {}) if isinstance(existing.get("models"), dict) else {}
    models[ep.model] = {
        "name": ep.model,
        "limit": {"context": ep.context, "output": ep.output},
    }
    providers["kaggle-studio"] = {
        **existing,
        "npm": "@ai-sdk/openai-compatible",
        "name": "Kaggle Studio",
        "options": {
            **(existing.get("options", {}) if isinstance(existing.get("options"), dict) else {}),
            "baseURL": ep.api_url,
            "apiKey": "{file:~/.kaggle-studio-opencode-token}",
            "timeout": 900000,
        },
        "models": models,
    }
    data["model"] = f"kaggle-studio/{ep.model}"
    data["small_model"] = f"kaggle-studio/{ep.model}"
    bak = _write(config, json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    prompt = config.parent / "AGENTS.md"
    _write(prompt, _upsert_managed_text(prompt.read_text("utf-8") if prompt.exists() else "", managed_agent_instructions()))
    return Result(
        "opencode",
        True,
        str(config),
        "OpenCode recebeu provider OpenAI-compatible, modelo principal/lite e instruções AGENTS.md.",
        bak,
    )


def configure_zcode(ep: Endpoint, home: Path | None = None) -> Result:
    home = Path(home or Path.home())
    desktop = home / ".zcode" / "v2" / "config.json"
    cli = home / ".zcode" / "cli" / "config.json"
    provider = {
        "kind": "openai",
        "name": "Kaggle Studio",
        "enabled": True,
        "options": {"baseURL": ep.api_url, "apiKeyRequired": True},
        "models": {
            ep.model: {
                "name": ep.model,
                "limit": {"context": ep.context, "output": ep.output},
                "modalities": {"input": ["text"], "output": ["text"]},
            }
        },
    }
    # Desktop needs its credential in the v2 provider. The headless CLI can
    # read ZCODE_API_KEY from the environment, so avoid duplicating the secret.
    desktop_provider = json.loads(json.dumps(provider))
    desktop_provider["options"]["apiKey"] = ep.api_key

    desktop_data = _json(desktop)
    desktop_providers = desktop_data.setdefault("provider", {})
    if not isinstance(desktop_providers, dict):
        desktop_providers = {}
        desktop_data["provider"] = desktop_providers
    desktop_providers["kaggle-studio"] = desktop_provider
    desktop_backup = _write(desktop, json.dumps(desktop_data, ensure_ascii=False, indent=2) + "\n", secret=True)

    cli_data = _json(cli)
    cli_providers = cli_data.setdefault("provider", {})
    if not isinstance(cli_providers, dict):
        cli_providers = {}
        cli_data["provider"] = cli_providers
    cli_providers["kaggle-studio"] = provider
    cli_data["model"] = {"main": f"kaggle-studio/{ep.model}", "lite": f"kaggle-studio/{ep.model}"}
    cli_backup = _write(cli, json.dumps(cli_data, ensure_ascii=False, indent=2) + "\n", secret=True)

    return Result(
        "zcode",
        True,
        f"{desktop} + {cli}",
        "ZCode Desktop e app-server configurados. Desktop guarda chave em arquivo protegido; CLI recebe ZCODE_API_KEY no ambiente.",
        desktop_backup or cli_backup,
    )


def _remove_prompt_block(path: Path) -> str:
    if not path.exists():
        return ""
    return _write(path, _remove_managed_text(path.read_text("utf-8")))


def _disconnect_codex(home: Path) -> Result:
    config = home / ".codex" / "config.toml"
    source = config.read_text("utf-8") if config.exists() else ""
    source = _remove_toml_section(source, f"[model_providers.{CODEX_PROVIDER}.auth]")
    source = _remove_toml_section(source, f"[model_providers.{CODEX_PROVIDER}]")
    backup = _write(config, source) if config.exists() else ""

    profile = home / ".codex" / CODEX_PROFILE_FILE
    if profile.exists() and f'model_provider = "{CODEX_PROVIDER}"' in profile.read_text("utf-8"):
        profile_backup = _backup(profile)
        profile.unlink()
        backup = backup or profile_backup

    # This is a generated credential, not a user config.  Never back it up.
    token = home / ".codex" / CODEX_TOKEN_FILE
    if token.exists():
        token.unlink()
    reader = home / ".codex" / CODEX_TOKEN_READER
    if reader.exists():
        reader.unlink()
    return Result("codex", True, str(config), "Configuração Codex removida.", backup)


def _disconnect_claude(home: Path) -> Result:
    config = home / ".claude" / "settings.json"
    data = _existing_json(config)
    env = data.get("env")
    if isinstance(env, dict):
        for key in (
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_MODEL",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        ):
            env.pop(key, None)
        if not env:
            data.pop("env", None)
    helper = subprocess.list2cmdline([sys.executable, str(home / ".claude" / CLAUDE_TOKEN_READER)])
    if data.get("apiKeyHelper") == helper:
        data.pop("apiKeyHelper", None)
    backup = _write(config, json.dumps(data, ensure_ascii=False, indent=2) + "\n") if config.exists() else ""
    prompt_backup = _remove_prompt_block(home / ".claude" / "CLAUDE.md")
    for path in (home / ".claude" / CLAUDE_TOKEN_FILE, home / ".claude" / CLAUDE_TOKEN_READER):
        if path.exists():
            path.unlink()
    return Result("claude", True, str(config), "Configuração Claude removida.", backup or prompt_backup)


def _disconnect_opencode(home: Path) -> Result:
    candidates = [home / ".config" / "opencode" / "opencode.jsonc", home / ".config" / "opencode" / "opencode.json"]
    config = next((item for item in candidates if item.exists()), candidates[0])
    data = _existing_jsonc(config)
    providers = data.get("provider")
    if isinstance(providers, dict):
        providers.pop("kaggle-studio", None)
        if not providers:
            data.pop("provider", None)
    for key in ("model", "small_model"):
        if str(data.get(key, "")).startswith("kaggle-studio/"):
            data.pop(key, None)
    backup = _write(config, json.dumps(data, ensure_ascii=False, indent=2) + "\n") if config.exists() else ""
    prompt_backup = _remove_prompt_block(config.parent / "AGENTS.md")
    token = home / OPENCODE_TOKEN_FILE
    if token.exists():
        token.unlink()
    return Result("opencode", True, str(config), "Configuração OpenCode removida.", backup or prompt_backup)


def _disconnect_zcode(home: Path) -> Result:
    paths = [home / ".zcode" / "v2" / "config.json", home / ".zcode" / "cli" / "config.json"]
    backup = ""
    for config in paths:
        if not config.exists():
            continue
        data = _json(config)
        providers = data.get("provider")
        if isinstance(providers, dict):
            providers.pop("kaggle-studio", None)
            if not providers:
                data.pop("provider", None)
        model = data.get("model")
        if isinstance(model, dict) and all(str(value).startswith("kaggle-studio/") for value in model.values()):
            data.pop("model", None)
        current_backup = _write(
            config, json.dumps(data, ensure_ascii=False, indent=2) + "\n", secret=True
        )
        backup = backup or current_backup
    return Result("zcode", True, " + ".join(map(str, paths)), "Configuração ZCode removida.", backup)


def disconnect_one(tool: str, home: Path | None = None) -> Result:
    home = Path(home or Path.home())
    fn = {
        "codex": _disconnect_codex,
        "claude": _disconnect_claude,
        "opencode": _disconnect_opencode,
        "zcode": _disconnect_zcode,
    }.get(tool)
    if fn is None:
        return Result(tool, False, "", f"Integração desconhecida: {tool}")
    try:
        return fn(home)
    except Exception as exc:
        return Result(tool, False, "", f"Falha ao desconectar {tool}: {str(exc)[:180]}")


def disconnect_all(home: Path | None = None) -> list[Result]:
    return [disconnect_one(tool, home) for tool in TOOL_COMMANDS]


def restore_backup(path: Path, backup: Path, *, secret: bool = False) -> str:
    """Restore a specific backup, retaining a backup of the current file."""
    path = Path(path)
    backup = Path(backup)
    if not backup.is_file():
        raise FileNotFoundError(backup)
    return _write(path, backup.read_text("utf-8"), secret=secret)


def configure_one(tool: str, ep: Endpoint, home: Path | None = None) -> Result:
    fn = {
        "codex": configure_codex,
        "claude": configure_claude,
        "opencode": configure_opencode,
        "zcode": configure_zcode,
    }.get(tool)
    if fn is None:
        return Result(tool, False, "", f"Integração desconhecida: {tool}")
    if not find_tool(tool):
        return Result(tool, False, "", f"{tool} não instalado no PATH; nada foi alterado")
    try:
        return fn(ep, home)
    except Exception as exc:
        return Result(tool, False, "", f"Falha ao configurar {tool}: {str(exc)[:180]}")


def configure_all(ep: Endpoint, home: Path | None = None) -> list[Result]:
    return [configure_one(tool, ep, home) for tool in TOOL_COMMANDS]


def launch_env(ep: Endpoint) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "KAGGLE_STUDIO_API_KEY": ep.api_key,
            "OPENAI_API_KEY": ep.api_key,
            "OPENAI_BASE_URL": ep.api_url,
            "OPENAI_API_BASE": ep.api_url,
            "ANTHROPIC_AUTH_TOKEN": ep.api_key,
            "ANTHROPIC_API_KEY": ep.api_key,
            "ANTHROPIC_BASE_URL": ep.root_url,
            "ANTHROPIC_MODEL": ep.model,
            "ZCODE_API_KEY": ep.api_key,
            "ZCODE_BASE_URL": ep.api_url,
        }
    )
    return env


def is_configured(tool: str, home: Path | None = None) -> bool:
    home = Path(home or Path.home())
    try:
        if tool == "codex":
            source = (home / ".codex" / "config.toml").read_text("utf-8")
            profile = (home / ".codex" / CODEX_PROFILE_FILE).read_text("utf-8")
            token = home / ".codex" / CODEX_TOKEN_FILE
            return (
                f"[model_providers.{CODEX_PROVIDER}]" in source
                and f"[model_providers.{CODEX_PROVIDER}.auth]" in source
                and f"[profiles.{CODEX_PROFILE}]" not in source
                and token.exists()
                and f'model_provider = "{CODEX_PROVIDER}"' in profile
            )
        if tool == "claude":
            data = _json(home / ".claude" / "settings.json")
            helper = subprocess.list2cmdline([sys.executable, str(home / ".claude" / CLAUDE_TOKEN_READER)])
            return (
                data.get("env", {}).get("ANTHROPIC_BASE_URL") is not None
                and data.get("apiKeyHelper") == helper
                and (home / ".claude" / CLAUDE_TOKEN_FILE).exists()
            )
        if tool == "opencode":
            for path in (home / ".config" / "opencode" / "opencode.jsonc", home / ".config" / "opencode" / "opencode.json"):
                if path.exists() and "kaggle-studio" in _jsonc(path).get("provider", {}):
                    provider = _jsonc(path).get("provider", {}).get("kaggle-studio", {})
                    return (
                        provider.get("options", {}).get("apiKey") == "{file:~/.kaggle-studio-opencode-token}"
                        and (home / OPENCODE_TOKEN_FILE).exists()
                    )
            return False
        if tool == "zcode":
            desktop = "kaggle-studio" in _json(home / ".zcode" / "v2" / "config.json").get("provider", {})
            cli = _json(home / ".zcode" / "cli" / "config.json")
            return desktop and "kaggle-studio" in cli.get("provider", {}) and str(cli.get("model", {}).get("main", "")).startswith("kaggle-studio/")
    except OSError:
        return False
    return False
