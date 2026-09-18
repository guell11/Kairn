"""Regenerate the GitHub runtime compatibility and integrity manifest."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kaggle.bootstrap import RUNTIME_FILES
from models_catalog import MODELS


def manifest(root=ROOT):
    return {
        "schema": 2,
        "backends": ["auto", "official-layer", "official-tensor", "ik_llama", "wackmall", "prism-ml"],
        "models": {key: {"sha256": value["sha256"], "backend": value["backend"]}
                   for key, value in MODELS.items()},
        "files": {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                  for name in (*RUNTIME_FILES, "kaggle/bootstrap.py")},
    }


if __name__ == "__main__":
    path = ROOT / "runtime-manifest.json"
    path.write_text(json.dumps(manifest(), indent=2) + "\n", "utf-8")
    print(path)
