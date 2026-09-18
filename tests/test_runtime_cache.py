import ast
import hashlib
import tempfile
import types
import unittest
from pathlib import Path

from models_catalog import MODELS
from runtime_builder import RuntimeBuilder
from state_store import AppState


class _Response:
    status_code = 200
    headers = {}
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *exc): return False
    def raise_for_status(self): pass
    def iter_content(self, _size): yield self.payload


class _Progress:
    def __init__(self, iterable=None, **kwargs): self.iterable = iterable
    def __enter__(self): return self
    def __exit__(self, *exc): return False
    def update(self, _size): pass


class RuntimeCacheTests(unittest.TestCase):
    @staticmethod
    def downloader():
        root = Path(__file__).resolve().parents[1]
        source = RuntimeBuilder(root).runtime_source(MODELS["velum"], AppState(), "ks_test")
        nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
                 and n.name in {"_sha256", "direct_download"}]
        namespace = {"Path": Path, "hashlib": hashlib, "MODELS_DIR": None,
                     "MIN_FREE_AFTER_DOWNLOAD_GB": 0, "HF_TOKEN_REAL": "",
                     "quote": lambda value, safe="/": value, "disk_free": lambda: 10**15,
                     "human_bytes": str, "tqdm": _Progress, "print": lambda *args, **kwargs: None}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "runtime", "exec"), namespace)
        return namespace["direct_download"], namespace

    def test_validated_file_is_reused_after_runtime_parameter_change(self):
        downloader, ns = self.downloader()
        payload = b"verified-model"
        with tempfile.TemporaryDirectory() as folder:
            ns["MODELS_DIR"] = Path(folder)
            info = {"repo": "guell00/VELUM-Coder", "filename": "VELUM-Coder-Q8_0.gguf",
                    "revision": "main", "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            ns["requests"] = types.SimpleNamespace(get=lambda *a, **k: _Response(payload))
            path = downloader(info)
            ns["requests"] = types.SimpleNamespace(get=lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
            self.assertEqual(path, downloader(info))

    def test_invalid_file_is_not_reused(self):
        downloader, ns = self.downloader()
        payload = b"correct-model"
        with tempfile.TemporaryDirectory() as folder:
            ns["MODELS_DIR"] = Path(folder)
            info = {"repo": "guell00/VELUM-Coder", "filename": "VELUM-Coder-Q8_0.gguf",
                    "revision": "main", "size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
            destination = Path(folder) / "guell00__VELUM-Coder" / info["filename"]
            destination.parent.mkdir(parents=True)
            destination.write_bytes(b"stale")
            calls = []
            ns["requests"] = types.SimpleNamespace(get=lambda *a, **k: (calls.append(1) or _Response(payload)))
            self.assertEqual(downloader(info).read_bytes(), payload)
            self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
