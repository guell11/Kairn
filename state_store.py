from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from localization import normalize_language


SETUP_STAGES = (
    "welcome", "model", "context", "output", "review", "environment",
    "cell1", "cell2", "connect", "agents", "ready",
)
ACCELERATOR_PROFILE = "t4x2"


@dataclass
class AppState:
    language: str = "pt-BR"
    model: str = "gemopus"
    base_url: str = ""
    context: int = 16384
    parallel: int = 2
    output: int = 8192
    mtp_tokens: int = 2
    speculation: str = "auto"
    temperature: float = 0.6
    top_k: int = 40
    top_p: float = 0.95
    min_p: float = 0.05
    backend: str = "official-layer"
    reasoning_budget: int = 3072
    # These preferences make the setup resumable without ever saving its API key.
    stage: str = "welcome"
    accelerator: str = ACCELERATOR_PROFILE
    parallel_auto: bool = True
    tunnel_mode: str = "quick"
    tunnel_url: str = ""

    def public(self) -> dict:
        return asdict(self)


class StateStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> AppState:
        try:
            raw = json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            return AppState()
        if not isinstance(raw, dict):
            return AppState()

        allowed = AppState.__dataclass_fields__
        try:
            state = AppState(**{key: raw[key] for key in allowed if key in raw})
        except (TypeError, ValueError):
            return AppState()

        # Defensive bounds for hand-edited/corrupted state files. The UI applies
        # the same limits when values are edited interactively.
        try:
            state.context = max(2048, min(131072, int(state.context)))
            state.parallel = max(1, min(8, int(state.parallel)))
            state.output = max(256, min(32768, int(state.output)))
            state.mtp_tokens = max(0, min(8, int(state.mtp_tokens)))
            state.temperature = max(0.0, min(2.0, float(state.temperature)))
            state.top_k = max(0, min(200, int(state.top_k)))
            state.top_p = max(0.0, min(1.0, float(state.top_p)))
            state.min_p = max(0.0, min(1.0, float(state.min_p)))
            state.reasoning_budget = max(0, min(32768, int(state.reasoning_budget)))
        except (TypeError, ValueError):
            return AppState()

        if state.stage not in SETUP_STAGES:
            state.stage = AppState().stage
        # The generated runtime requires two GPUs. Keep the profile explicit so
        # a future UI cannot silently promise a single-GPU fallback.
        if state.accelerator != ACCELERATOR_PROFILE:
            state.accelerator = ACCELERATOR_PROFILE
        if not isinstance(state.parallel_auto, bool):
            state.parallel_auto = AppState().parallel_auto
        state.language = normalize_language(state.language)
        if state.speculation not in ("auto", "off", "ngram"):
            state.speculation = "auto"
        return state

    def save(self, state: AppState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(state.public(), indent=2, ensure_ascii=False) + "\n", "utf-8"
        )
        tmp.replace(self.path)
