import io
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from kaggle.bootstrap import RUNTIME_FILES, fetch_runtime, source_sha256
from models_catalog import MODELS
from prebuilt_support import cuda_device_ids, require_cuda_devices, write_backend_launcher, install_wackmall
from runtime_builder import RuntimeBuilder
from state_store import AppState

ROOT = Path(__file__).resolve().parents[1]


class CudaTests(unittest.TestCase):
    def test_gpu_probe_rejects_help_success_cpu_only_and_partial_gpu(self):
        for output in ("usage: llama-server --help", "Available devices:\nCPU: x86", "CUDA0: T4\nCUDA0: T4"):
            with patch("prebuilt_support.subprocess.run", return_value=subprocess.CompletedProcess([], 0, output, "")):
                with self.assertRaisesRegex(RuntimeError, "CUDA indisponível"):
                    require_cuda_devices(ROOT / "llama-server")
        with patch("prebuilt_support.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "Available devices:\nCUDA0: Tesla T4 (15000 MiB)\nCUDA1: Tesla T4 (15000 MiB)", "")):
            self.assertEqual(require_cuda_devices(ROOT / "llama-server"), ["CUDA0", "CUDA1"])

    def test_launcher_changes_directory_before_private_loader(self):
        with tempfile.TemporaryDirectory(prefix="kairn space ") as tmp:
            root = Path(tmp)
            binary = root / "llama-server.bin"
            binary.touch()
            (root / "libggml-cuda.so").touch()
            launcher = write_backend_launcher(root, binary, [root], root / "sysroot/ld-linux-x86-64.so.2")
            text = launcher.read_text()
            self.assertLess(text.index("cd "), text.index("exec "))
            self.assertIn("--library-path", text)
            self.assertIn('"$@"', text)
            self.assertNotIn("GGML_BACKEND_PATH=", text)  # This env var expects a file, not a directory.

    def test_cuda_validated_before_model_download_in_every_backend(self):
        for backend in ("auto", "official-layer", "official-tensor", "wackmall", "ik_llama"):
            code = RuntimeBuilder(ROOT).runtime_source(MODELS["gemopus"], AppState(backend=backend))
            compile(code, "<runtime>", "exec")
            self.assertLess(code.index("require_cuda_devices(LLAMA_SERVER)"), code.index("# SELECIONAR MODELOS"))
            self.assertIn("repair_official_launcher(RUNTIME_SERVER.parent)", code)

    def test_unpublished_wackmall_linux_has_explicit_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            error = urllib.error.HTTPError("https://github.com", 404, "Not found", {}, None)
            with patch("prebuilt_support.urllib.request.urlopen", side_effect=error):
                with self.assertRaisesRegex(RuntimeError, "só oferece CUDA para Windows"):
                    install_wackmall(Path(tmp))


class BootstrapTests(unittest.TestCase):
    def test_source_integrity_is_independent_of_git_line_endings(self):
        self.assertEqual(source_sha256(b"one\r\ntwo\r\n"), source_sha256(b"one\ntwo\n"))

    def test_downloaded_runtime_imports_without_desktop_checkout(self):
        def fetch(url, **kwargs):
            return io.BytesIO((ROOT / url.rsplit("/", 1)[-1]).read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            checkout = Path(tmp)
            with patch("kaggle.bootstrap.urllib.request.urlopen", side_effect=fetch):
                fetch_runtime("guell11/Kairn", "a" * 40, checkout)
            probe = subprocess.run(
                [sys.executable, "-I", "-c",
                 "import sys; sys.path.insert(0, sys.argv[1]); "
                 "from state_store import AppState; from models_catalog import MODELS; "
                 "from runtime_builder import RuntimeBuilder; "
                 "from pathlib import Path; "
                 "compile(RuntimeBuilder(Path(sys.argv[1])).runtime_source(MODELS['gemopus'], AppState()), '<runtime>', 'exec')",
                 str(checkout)], cwd=checkout, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)

    def test_downloads_one_commit_without_overwriting_model_cache(self):
        seen = []
        def fetch(url, **kwargs):
            seen.append(url)
            return io.BytesIO(b"# test fixture\nVALUE = 1\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            model = root / "models/model.gguf"
            model.parent.mkdir()
            model.write_bytes(b"preserved")
            with patch("kaggle.bootstrap.urllib.request.urlopen", side_effect=fetch):
                fetch_runtime("guell11/Kairn", "a" * 40, root / ".kairn" / ("a" * 40))
            self.assertEqual(len(seen), len(RUNTIME_FILES))
            self.assertTrue(all("/" + "a" * 40 + "/" in url for url in seen))
            self.assertEqual(model.read_bytes(), b"preserved")

    def test_github_cell_has_config_and_no_local_endpoint_or_saved_key(self):
        cell = RuntimeBuilder(ROOT).github_cell(MODELS["gemopus"], AppState(backend="wackmall", base_url="https://private.example/v1"))
        compile(cell, "<github-cell>", "exec")
        self.assertIn("guell11/Kairn", cell)
        self.assertIn("'backend': 'wackmall'", cell)
        self.assertNotIn("private.example", cell)
        self.assertNotIn("API_KEY", cell)

    def test_invalid_commit_cannot_escape_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                fetch_runtime("guell11/Kairn", "../../escape", Path(tmp))


if __name__ == "__main__":
    unittest.main()
