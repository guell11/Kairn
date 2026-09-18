import ast
import base64
import unittest
from pathlib import Path

from models_catalog import MODELS
from runtime_builder import RuntimeBuilder
from state_store import AppState


def embedded(code):
    tree = ast.parse(code)
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr == "b64decode")
    return base64.b64decode(ast.literal_eval(call.args[0])).decode()

class BonsaiRuntimeTests(unittest.TestCase):
    def test_catalog_pins_prism_backend_and_verified_file_metadata(self):
        model = MODELS["bonsai-abliterated"]
        self.assertEqual(model["required_backend"], "prism-ml")
        self.assertEqual(model["backend_ref"], "1a07bfa5f4144274c8f1c9963821dd9d9a51854b")
        self.assertEqual(model["gguf"], "Ternary-Bonsai-2-27B-Abliterated-PTQ1_0.gguf")
        self.assertEqual(model["size_bytes"], 5946648928)
        self.assertEqual(len(model["sha256"]), 64)

    def test_generated_runtime_has_prism_compile_path(self):
        root = Path(__file__).resolve().parents[1]
        state = AppState()
        code = embedded(RuntimeBuilder(root).runtime_cell(MODELS["bonsai-abliterated"], state, "ks_test"))
        compile(code, "<bonsai-runtime>", "exec")
        self.assertIn("PrismML-Eng/llama.cpp", code)
        self.assertIn("BACKEND_FAMILY = 'prism-ml'", code)
        self.assertIn("1a07bfa5f4144274c8f1c9963821dd9d9a51854b", code)
        self.assertIn("PTQ1_0", code)
        self.assertNotIn("Quick Tunnel não suporta SSE", code)
        self.assertIn("SSE em lotes de ~4 s", code)

if __name__ == "__main__":
    unittest.main()
