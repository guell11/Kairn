import ast
import base64
import json
import tempfile
import unittest
from pathlib import Path

from models_catalog import MODELS
from runtime_builder import RuntimeBuilder
from state_store import ACCELERATOR_PROFILE, AppState, StateStore


def embedded(code):
    compile(code, '<notebook-wrapper>', 'exec')
    call = next(n for n in ast.walk(ast.parse(code)) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'b64decode')
    return base64.b64decode(ast.literal_eval(call.args[0])).decode()


class RuntimeTests(unittest.TestCase):
    def test_runtime_inlines_gateway_backend_auth_and_heartbeat(self):
        root = Path(__file__).resolve().parents[1]
        state = AppState(backend="official-tensor", reasoning_budget=4096)
        code = embedded(RuntimeBuilder(root).runtime_cell(MODELS["gemopus"], state, "ks_test"))

        self.assertIn("BACKEND_FAMILY = 'official-tensor'", code)
        self.assertIn("API_KEY = 'ks_test'", code)
        self.assertIn("UNIVERSAL_GATEWAY_B64 = ", code)
        self.assertIn("KAGGLE_AGENT_SYSTEM_PROMPT", code)
        self.assertIn("headers=AUTH_HEADERS", code)
        self.assertIn("KEEP_RUNTIME_CELL_ACTIVE = True", code)
        self.assertIn("ACTIVE-CELL HEARTBEAT", code)
        self.assertIn("fallback automático para layer split", code)
        self.assertIn('LLAMA_PREBUILT_TAG = "b11009"', code)
        self.assertIn("zero build local", code)
        compile(code, "<generated-kaggle-runtime>", "exec")

    def test_runtime_key_is_generated_when_blank(self):
        root = Path(__file__).resolve().parents[1]
        code = embedded(RuntimeBuilder(root).runtime_cell(MODELS["gemopus"], AppState(), ""))
        self.assertIn("API_KEY = 'ks_", code)

    def test_runtime_failure_paths_are_explicit_and_global_python_is_untouched(self):
        root = Path(__file__).resolve().parents[1]
        builder = RuntimeBuilder(root)
        install = builder.install_cell()
        code = embedded(builder.runtime_cell(MODELS["gemopus"], AppState(), "ks_test"))
        gateway = (root / "kaggle_gateway.py").read_text("utf-8")

        self.assertIn("venv.EnvBuilder", install)
        self.assertIn("with_pip=False", install)
        self.assertIn('"--python", str(RUNTIME_PYTHON)', install)
        self.assertIn("RUNTIME_PYTHON", install)
        self.assertNotIn("with_pip=True", install)
        self.assertIn("Espaço insuficiente", code)
        self.assertIn("SHA-256 inválido", code)
        self.assertIn("Range recusado", code)
        self.assertIn("len(gpu_lines) < 2", code)
        self.assertIn("OOM confirmado", code)
        self.assertIn("Cloudflare Tunnel não iniciou", code)
        self.assertIn("CUDA::cuda_driver ausente", code)
        self.assertIn('"Invalid API key"', gateway)


class StateTests(unittest.TestCase):
    def test_setup_defaults_keep_dual_t4_and_automatic_slots(self):
        state = AppState()
        self.assertEqual(state.stage, "welcome")
        self.assertEqual(state.accelerator, ACCELERATOR_PROFILE)
        self.assertTrue(state.parallel_auto)

    def test_state_store_does_not_have_api_key_field(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            store = StateStore(path)
            store.save(AppState(base_url="https://x/v1"))
            raw = path.read_text()
            self.assertNotIn("api_key", raw)

    def test_state_load_clamps_corrupt_out_of_range_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "context": 1,
                        "parallel": 99,
                        "output": 999999,
                        "temperature": -8,
                        "top_p": 4,
                        "reasoning_budget": -1,
                    }
                )
            )
            state = StateStore(path).load()
            self.assertEqual(state.context, 2048)
            self.assertEqual(state.parallel, 8)
            self.assertEqual(state.output, 32768)
            self.assertEqual(state.temperature, 0.0)
            self.assertEqual(state.top_p, 1.0)
            self.assertEqual(state.reasoning_budget, 0)

    def test_state_load_repairs_invalid_setup_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "stage": "done-forever",
                        "accelerator": "p100",
                        "parallel_auto": "yes",
                    }
                )
            )
            state = StateStore(path).load()
            self.assertEqual(state.stage, "welcome")
            self.assertEqual(state.accelerator, ACCELERATOR_PROFILE)
            self.assertTrue(state.parallel_auto)


if __name__ == "__main__":
    unittest.main()
