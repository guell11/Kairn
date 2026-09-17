from __future__ import annotations

import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import httpx
from PyQt6.QtCore import QObject, QTimer, QUrl, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QMainWindow, QSplitter, QFileDialog
from connection import normalize_url, probe_endpoint

from integrations import (
    Endpoint,
    configure_all,
    configure_one,
    disconnect_all,
    disconnect_one,
    find_tool,
    is_configured,
    launch_argv,
    launch_env,
)
from models_catalog import MODELS, public_catalog
from runtime_builder import RuntimeBuilder
from state_store import ACCELERATOR_PROFILE, SETUP_STAGES, AppState, StateStore

ROOT = Path(__file__).resolve().parent
KAGGLE_URL = "https://www.kaggle.com/code/new"
VERSION = "4.2.0"

OPTION_LIMITS = {
    "context": (2048, 131072, int),
    "parallel": (1, 8, int),
    "output": (256, 32768, int),
    "mtp_tokens": (0, 8, int),
    "temperature": (0.0, 2.0, float),
    "top_k": (0, 200, int),
    "top_p": (0.0, 1.0, float),
    "min_p": (0.0, 1.0, float),
    "reasoning_budget": (0, 32768, int),
}
VALID_BACKENDS = {"auto", "ik_llama", "official-layer", "official-tensor", "wackmall"}


class BrowserPage(QWebEnginePage):
    def createWindow(self, _kind):
        return self


class ProbeWorker(QThread):
    result = pyqtSignal(dict)

    def __init__(self, url, key, parent=None):
        super().__init__(parent)
        self.url, self.key = url, key

    def run(self):
        try:
            result = probe_endpoint(self.url, self.key)
        except Exception:
            result = {"online": False, "message": "Falha no diagnóstico. Confira URL e tente novamente."}
        self.result.emit(result)


class Bridge(QObject):
    toast = pyqtSignal(str, bool)
    stateChanged = pyqtSignal(str)
    metricsChanged = pyqtSignal(str)

    def __init__(self, window: "Window"):
        super().__init__()
        self.window = window

    @pyqtSlot(result=str)
    def bootstrap(self) -> str:
        return json.dumps(
            {
                "state": self.window.public_state(),
                "models": public_catalog(),
                "tools": self.window.tool_status(),
                "version": VERSION,
            },
            ensure_ascii=False,
        )

    @pyqtSlot(str)
    def selectModel(self, key: str) -> None:
        if key not in MODELS:
            self.toast.emit("Modelo desconhecido", False)
            return
        model = MODELS[key]
        state = self.window.state
        state.model = key
        state.context = model["context"]
        state.output = model["output"]
        if state.parallel_auto:
            state.parallel = self.window.recommended_slots()
        # Preserve explicitly chosen backend when switching model.
        self.window.persist()
        self.window.emit_state()

    @pyqtSlot(str)
    def updateOptions(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except ValueError:
            self.toast.emit("Configuração inválida", False)
            return
        if not isinstance(data, dict):
            self.toast.emit("Configuração inválida", False)
            return

        for key, (minimum, maximum, cast) in OPTION_LIMITS.items():
            if key not in data:
                continue
            try:
                value = cast(data[key])
            except (TypeError, ValueError):
                continue
            setattr(self.window.state, key, max(minimum, min(maximum, value)))

        backend = str(data.get("backend", self.window.state.backend))
        if backend in VALID_BACKENDS:
            self.window.state.backend = backend
        if data.get("tunnel_mode") in {"quick", "named"}:
            self.window.state.tunnel_mode = data["tunnel_mode"]
        if "tunnel_url" in data:
            self.window.state.tunnel_url = str(data["tunnel_url"]).strip()

        if self.window.state.parallel_auto:
            self.window.state.parallel = self.window.recommended_slots()

        # Legacy UI payloads always include ``parallel``. Do not infer manual
        # mode from that field; the new UI opts out through setAutomaticSlots.

        self.window.persist()
        self.window.emit_state()

    @pyqtSlot(bool)
    def setAutomaticSlots(self, enabled: bool) -> None:
        self.window.state.parallel_auto = enabled
        if enabled:
            self.window.state.parallel = self.window.recommended_slots()
        self.window.persist()
        self.window.emit_state()

    @pyqtSlot(str)
    def setSetupStage(self, stage: str) -> None:
        if not self.window.set_stage(stage):
            self.toast.emit("Etapa de configuração inválida", False)
            return
        self.window.persist()
        self.window.emit_state()

    @pyqtSlot(str, str)
    def connectApi(self, base_url: str, api_key: str) -> None:
        if self.window.probe_busy:
            return
        self.window.set_endpoint(base_url, api_key)
        self.window.start_probe(connect=True)

    @pyqtSlot(str, result=str)
    def code(self, kind: str) -> str:
        try:
            return self.window.generated_code(kind)
        except Exception as exc:
            self.toast.emit(str(exc), False)
            return ""

    @pyqtSlot(str, result=bool)
    def copy(self, kind: str) -> bool:
        text = self.code(kind)
        if text:
            QApplication.clipboard().setText(text)
            self.toast.emit("Copiado para a área de transferência", True)
            return True
        return False

    @pyqtSlot()
    def exportNotebook(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self.window, "Salvar notebook Kaggle", "kaggle-studio.ipynb", "Notebook (*.ipynb)")
        if not path:
            return
        try:
            Path(path).write_text(self.window.builder.notebook(MODELS[self.window.state.model], self.window.state), "utf-8")
            self.toast.emit("Notebook salvo. Importe no Kaggle e execute duas células.", True)
        except Exception as exc:
            self.toast.emit(f"Falha ao exportar: {exc}", False)

    @pyqtSlot()
    def testApi(self) -> None:
        self.window.start_probe()

    @pyqtSlot(str)
    def configureTool(self, tool: str) -> None:
        result = self.window.configure_tool(tool)
        self.toast.emit(result["message"], result["ok"])
        self.stateChanged.emit(json.dumps({
            "state": self.window.public_state(),
            "tools": self.window.tool_status(),
        }, ensure_ascii=False))

    @pyqtSlot()
    def configureAll(self) -> None:
        results = self.window.configure_all()
        count = sum(1 for result in results if result["ok"])
        self.toast.emit(
            f"{count}/{len(results)} integrações configuradas",
            bool(results) and count == len(results),
        )
        if results and count == len(results):
            self.window.set_stage("ready")
            self.window.persist()
        self.stateChanged.emit(json.dumps({
            "state": self.window.public_state(),
            "tools": self.window.tool_status(),
        }, ensure_ascii=False))

    @pyqtSlot(str)
    def disconnectTool(self, tool: str) -> None:
        result = disconnect_one(tool).dict()
        self.toast.emit(result["message"], result["ok"])
        self.stateChanged.emit(
            json.dumps({"tools": self.window.tool_status()}, ensure_ascii=False)
        )

    @pyqtSlot()
    def disconnectAll(self) -> None:
        results = [result.dict() for result in disconnect_all()]
        ok = sum(1 for result in results if result["ok"])
        self.toast.emit(f"{ok}/{len(results)} integrações desconectadas", ok == len(results))
        self.stateChanged.emit(
            json.dumps({"tools": self.window.tool_status()}, ensure_ascii=False)
        )

    @pyqtSlot(str)
    def launch(self, tool: str) -> None:
        ok, message = self.window.launch_tool(tool)
        self.toast.emit(message, ok)

    @pyqtSlot()
    def openKaggle(self) -> None:
        self.window.open_kaggle()

    @pyqtSlot()
    def hideKaggle(self) -> None:
        self.window.hide_kaggle()

    @pyqtSlot(str)
    def navigate(self, target: str) -> None:
        if target == "kaggle":
            self.window.open_kaggle()
        elif target == "studio":
            self.window.hide_kaggle()
        elif target == "reset-kaggle":
            self.window.reset_kaggle()
        else:
            self.toast.emit("Destino de navegação inválido", False)

    @pyqtSlot(result=str)
    def restore(self) -> str:
        return json.dumps(self.window.restore_snapshot(), ensure_ascii=False)

    @pyqtSlot(result=str)
    def diagnostics(self) -> str:
        return json.dumps(self.window.diagnostics(), ensure_ascii=False)

    @pyqtSlot(result=str)
    def metrics(self) -> str:
        return json.dumps(self.window.metrics(), ensure_ascii=False)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kaggle Studio")
        self.resize(1500, 940)
        self.processes: list[subprocess.Popen] = []
        self.api_key = ""
        self.probe_busy = False
        self.connection_verified = False
        self.remote_model = ""
        self.last_metrics = {"online": False, "message": "API não conectada"}
        self.probe_worker = None

        self.store = StateStore(ROOT / ".kaggle-studio" / "state.json")
        self.state = self.store.load()
        if self.state.base_url and not re.match(r"^https?://", self.state.base_url):
            self.state.base_url = ""
        self.runtime_key = "ks_" + secrets.token_urlsafe(24)
        if self.state.model not in MODELS:
            self.state.model = "gemopus"
        if self.state.backend not in VALID_BACKENDS:
            self.state.backend = "official-layer"
        if self.state.parallel_auto:
            self.state.parallel = self.recommended_slots()

        self.builder = RuntimeBuilder(ROOT)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.splitter)

        profile = QWebEngineProfile("KaggleStudio", self)
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        profile.setPersistentStoragePath(str(ROOT / ".browser"))
        profile.setCachePath(str(ROOT / ".browser" / "cache"))

        self.browser = QWebEngineView()
        self.browser.setPage(BrowserPage(profile, self.browser))
        self.browser.setUrl(QUrl(KAGGLE_URL))

        self.ui = QWebEngineView()
        self.ui.setMinimumWidth(560)
        self.bridge = Bridge(self)
        self.channel = QWebChannel(self.ui.page())
        self.channel.registerObject("studio", self.bridge)
        self.ui.page().setWebChannel(self.channel)
        self.ui.setUrl(QUrl.fromLocalFile(str(ROOT / "ui" / "index.html")))

        self.splitter.addWidget(self.browser)
        self.splitter.addWidget(self.ui)
        self.browser.hide()
        self.splitter.setSizes([0, 1500])
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(1, False)

        self.timer = QTimer(self)
        self.timer.setInterval(60_000)
        self.timer.timeout.connect(self.start_probe)
        self.timer.start()

    def persist(self) -> None:
        self.store.save(self.state)

    def public_state(self) -> dict:
        state = self.state.public()
        state["hasApiKey"] = bool(self.api_key)
        state["connectionVerified"] = self.connection_verified
        state["agentsAvailable"] = self.connection_verified and self.last_metrics.get("agents_available", False)
        state["connectionBusy"] = self.probe_busy
        state["modelInfo"] = MODELS[self.state.model]
        state["sessionWatch"] = bool(self.state.base_url and self.api_key)
        state["serverContext"] = self.state.context * self.state.parallel
        state["recommendedSlots"] = self.recommended_slots()
        state["resumeStage"] = self.resume_stage()
        return state

    def recommended_slots(self) -> int:
        """Safe concurrency preset for the supported dual-T4 runtime."""
        model = MODELS.get(self.state.model, {})
        model_limit = int(model.get("parallel", AppState().parallel))
        context_limit = max(1, 32768 // max(2048, int(self.state.context)))
        return max(1, min(2, model_limit, context_limit))

    def set_stage(self, stage: str) -> bool:
        if stage not in SETUP_STAGES:
            return False
        self.state.stage = stage
        return True

    def resume_stage(self) -> str:
        # API keys are intentionally memory-only. A reopened app must resume at
        # connection even if it had configured local clients in an earlier run.
        if not self.api_key and self.state.stage in {"agents", "ready"}:
            return "connect"
        return self.state.stage

    def restore_snapshot(self) -> dict:
        return {
            "state": self.public_state(),
            "models": public_catalog(),
            "tools": self.tool_status(),
            "navigation": {
                "kaggleVisible": self.browser.isVisible(),
                "kaggleUrl": self.browser.url().toString(),
            },
            "version": VERSION,
        }

    def diagnostics(self) -> dict:
        metrics = self.metrics()
        return {
            "stage": self.resume_stage(),
            "accelerator": self.state.accelerator,
            "slots": {
                "automatic": self.state.parallel_auto,
                "configured": self.state.parallel,
                "recommended": self.recommended_slots(),
            },
            "kaggle": {
                "visible": self.browser.isVisible(),
                "url": self.browser.url().toString(),
            },
            "gateway": metrics,
        }

    def emit_state(self) -> None:
        self.bridge.stateChanged.emit(
            json.dumps({"state": self.public_state()}, ensure_ascii=False)
        )

    def set_endpoint(self, url: str, key: str) -> None:
        self.connection_verified = False
        self.remote_model = ""
        try:
            url = normalize_url(url)
        except ValueError:
            self.state.base_url = ""
            self.api_key = ""
            self.persist()
            return
        if url and not url.endswith("/v1"):
            url += "/v1"
        self.state.base_url = url
        self.api_key = key.strip()
        if self.api_key:
            self.runtime_key = self.api_key
        self.persist()

    def start_probe(self, connect=False):
        if self.probe_busy:
            return
        self.probe_busy = True
        self.emit_state()
        worker = ProbeWorker(self.state.base_url, self.api_key, self)
        self.probe_worker = worker
        worker.result.connect(lambda result: self.finish_probe(result, connect))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def finish_probe(self, result, connect=False):
        self.probe_busy = False
        self.last_metrics = result
        self.connection_verified = bool(result.get("online"))
        self.remote_model = result.get("model", "")
        if connect and self.connection_verified and result.get("agents_available"):
            self.set_stage("agents")
            self.persist()
        if connect:
            self.bridge.toast.emit(result["message"], self.connection_verified)
        self.emit_state()
        self.bridge.metricsChanged.emit(json.dumps(result, ensure_ascii=False))

    def generated_code(self, kind: str) -> str:
        if kind == "github":
            return self.builder.github_cell(MODELS[self.state.model], self.state)
        if kind == "install":
            return self.builder.install_cell()
        if kind == "runtime":
            return self.builder.runtime_cell(
                MODELS[self.state.model],
                self.state,
                self.api_key or self.runtime_key,
            )
        if kind == "smoke":
            if not self.state.base_url or not self.api_key:
                return "# Conecte a API primeiro"
            return (
                "curl -sS "
                + shlex.quote(self.state.base_url.removesuffix("/v1") + "/health")
                + " -H "
                + shlex.quote(f"Authorization: Bearer {self.api_key}")
            )
        raise ValueError(f"Tipo de código inválido: {kind}")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "x-api-key": self.api_key,
        }

    def check_api(self) -> tuple[bool, str]:
        result = probe_endpoint(self.state.base_url, self.api_key)
        return result['online'], result['message']

    def metrics(self) -> dict:
        return self.last_metrics

    def emit_metrics(self) -> None:
        self.bridge.metricsChanged.emit(json.dumps(self.metrics(), ensure_ascii=False))

    def endpoint(self) -> Endpoint:
        return Endpoint(
            self.state.base_url,
            self.api_key,
            self.remote_model or MODELS[self.state.model]["model_id"],
            context=self.state.context,
            output=self.state.output,
        )

    def configure_tool(self, tool: str) -> dict:
        if not self.connection_verified or not self.last_metrics.get("agents_available"):
            return {
                "tool": tool,
                "ok": False,
                "path": "",
                "message": "Conecte API por túnel com suporte a SSE antes de configurar agentes.",
                "backup": "",
            }
        return configure_one(tool, self.endpoint()).dict()

    def configure_all(self) -> list[dict]:
        if not self.connection_verified or not self.last_metrics.get("agents_available"):
            return [
                {
                    "tool": "all",
                    "ok": False,
                    "path": "",
                    "message": "Conecte a API do Kaggle primeiro",
                    "backup": "",
                }
            ]
        installed = [name for name, status in self.tool_status().items() if status["installed"]]
        return [configure_one(name, self.endpoint()).dict() for name in installed]

    def tool_status(self) -> dict:
        home = Path.home()
        return {
            "codex": {
                "installed": bool(find_tool("codex")),
                "configured": is_configured("codex"),
                "path": str(home / ".codex" / "config.toml"),
            },
            "claude": {
                "installed": bool(find_tool("claude")),
                "configured": is_configured("claude"),
                "path": str(home / ".claude" / "settings.json"),
            },
            "opencode": {
                "installed": bool(find_tool("opencode")),
                "configured": is_configured("opencode"),
                "path": str(home / ".config" / "opencode" / "opencode.jsonc"),
            },
            "zcode": {
                "installed": bool(find_tool("zcode")),
                "configured": is_configured("zcode"),
                "path": str(home / ".zcode" / "v2" / "config.json"),
            },
        }

    def _command(self, tool: str) -> tuple[str | None, list[str]]:
        model = self.remote_model or MODELS[self.state.model]["model_id"]
        if tool == "codex":
            return find_tool("codex"), ["--profile", "kaggle-studio"]
        if tool == "claude":
            return find_tool("claude"), ["--model", model]
        if tool == "opencode":
            return find_tool("opencode"), ["--model", f"kaggle-studio/{model}"]
        if tool == "zcode":
            return find_tool("zcode"), []
        return None, []

    def launch_tool(self, tool: str) -> tuple[bool, str]:
        result = self.configure_tool(tool)
        if not result["ok"]:
            return False, result["message"]

        executable, args = self._command(tool)
        if not executable:
            return False, f"{tool} não encontrado no PATH; config foi gravado mesmo assim"

        env = launch_env(self.endpoint())
        try:
            if os.name == "nt":
                process = subprocess.Popen(
                    launch_argv(executable, args),
                    env=env,
                    cwd=ROOT,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            elif sys.platform == "darwin" and shutil.which("osascript"):
                command = " ".join(map(shlex.quote, [executable, *args]))
                export_keys = (
                    "KAGGLE_STUDIO_API_KEY",
                    "OPENAI_API_KEY",
                    "OPENAI_BASE_URL",
                    "OPENAI_API_BASE",
                    "ANTHROPIC_AUTH_TOKEN",
                    "ANTHROPIC_API_KEY",
                    "ANTHROPIC_BASE_URL",
                    "ANTHROPIC_MODEL",
                    "ZCODE_API_KEY",
                    "ZCODE_BASE_URL",
                )
                exports = "; ".join(
                    f"export {key}={shlex.quote(env[key])}" for key in export_keys
                )
                script = "tell application \"Terminal\" to do script " + json.dumps(
                    exports + "; " + command
                )
                process = subprocess.Popen(
                    ["osascript", "-e", script], env=env, cwd=ROOT
                )
            else:
                terminal = next(
                    (
                        shutil.which(name)
                        for name in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm")
                        if shutil.which(name)
                    ),
                    None,
                )
                command = [terminal, "-e", executable, *args] if terminal else [executable, *args]
                process = subprocess.Popen(command, env=env, cwd=ROOT)

            self.processes.append(process)
            return True, f"{tool} iniciado com o gateway Kaggle"
        except Exception as exc:
            return False, f"Falha ao abrir {tool}: {str(exc)[:100]}"

    def open_kaggle(self) -> None:
        self.browser.show()
        self.splitter.setSizes([880, 620])

    def hide_kaggle(self) -> None:
        self.browser.hide()
        self.splitter.setSizes([0, 1500])

    def reset_kaggle(self) -> None:
        self.browser.setUrl(QUrl(KAGGLE_URL))
        self.open_kaggle()

    def closeEvent(self, event) -> None:
        if self.probe_busy:
            self.bridge.toast.emit("Aguarde teste de conexão terminar antes de fechar.", False)
            event.ignore()
            return
        for process in self.processes:
            if process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Kaggle Studio")
    app.setOrganizationName("Kaggle Studio")
    window = Window()
    window.show()
    sys.exit(app.exec())
