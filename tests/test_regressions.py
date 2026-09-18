import ast
import base64
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from connection import normalize_url, probe_endpoint
from models_catalog import MODELS
from runtime_builder import RuntimeBuilder
from runtime_support import llama_command, retry_slots, stop_process
from state_store import AppState

ROOT = Path(__file__).resolve().parents[1]


def unpack(code):
    tree = ast.parse(code)
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr == "b64decode")
    return base64.b64decode(ast.literal_eval(call.args[0])).decode()


class RuntimeRegressionTests(unittest.TestCase):
    def test_rejects_output_that_leaves_no_room_for_prompt(self):
        with self.assertRaises(ValueError):
            RuntimeBuilder(ROOT).runtime_cell(MODELS["gemopus"], AppState(context=8192, output=8192), "test")

    def test_pip_fallback_keeps_install_subcommand(self):
        from types import SimpleNamespace
        tree = ast.parse(RuntimeBuilder(ROOT).install_cell())
        install = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == "install" for t in n.targets))
        scope = {"sys": SimpleNamespace(executable="kernel-python"), "RUNTIME_PYTHON": Path("venv-python")}
        scope["install"] = eval(compile(ast.Expression(install), "<install-list>", "eval"), scope)
        fallback = next(n for n in ast.walk(tree) if isinstance(n, ast.List) and any(isinstance(item, ast.Starred) for item in n.elts))
        argv = eval(compile(ast.Expression(fallback), "<fallback-list>", "eval"), scope)
        self.assertEqual(argv[:4], ["venv-python", "-m", "pip", "install"])
        self.assertIn("requests", argv)

    def test_supported_flags_sampling_and_tensor_cache(self):
        help_text = "--flash-attn --cache-type-k --cache-type-v --temp --top-k --top-p --min-p --reasoning-budget"
        for split in ("layer", "tensor", "graph"):
            command = llama_command("server", "model", "alias", 8192, 2, split, help_text, temperature=.3, reasoning_budget=512)
            self.assertNotIn("--parallel-tool-calls", command)
            self.assertEqual(command[command.index("--ctx-size") + 1], "16384")
            self.assertEqual(command[command.index("--cache-type-k") + 1], "f16" if split == "tensor" else "q8_0")
            self.assertEqual(command[command.index("--temp") + 1], "0.3")
            self.assertEqual(command[command.index("--reasoning-budget") + 1], "512")

    def test_retries_all_slot_counts_and_kills_hung_process(self):
        self.assertEqual(retry_slots(4), [4, 2, 1])
        self.assertEqual(retry_slots(3), [3, 1])
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("server", 10), 0]
        stop_process(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()

    def test_export_has_no_saved_key_and_all_cells_compile(self):
        builder = RuntimeBuilder(ROOT)
        for backend in ("official-layer", "official-tensor", "auto", "ik_llama"):
            state = AppState(backend=backend, tunnel_mode="named", tunnel_url="https://example.org")
            notebook = json.loads(builder.notebook(MODELS["gemopus"], state))
            for cell in notebook["cells"]:
                if cell["cell_type"] == "code":
                    compile("".join(cell["source"]), "<notebook>", "exec")
            runtime = unpack("".join(notebook["cells"][-1]["source"]))
            compile(runtime, "<runtime>", "exec")
            self.assertNotIn("__RUNTIME_KEY__", runtime)
            assignment = next(n for n in ast.parse(runtime).body if isinstance(n, ast.Assign)
                              and any(isinstance(t, ast.Name) and t.id == "API_KEY" for t in n.targets))
            self.assertIsInstance(assignment.value, ast.BinOp)
            # Run the fresh-build selection prelude, which used to leave graph enabled.
            start = runtime.index('backend = BACKEND_FAMILY if BACKEND_FAMILY != "auto" else "official-layer"', runtime.index('# BACKEND COMPILADO'))
            end = runtime.index('BUILD_ID = ', start)
            env = {"BACKEND_FAMILY": backend, "ROOT": ROOT, "LLAMA_PREBUILT_TAG": "test"}
            exec(runtime[start:end], env)
            self.assertEqual(env["SPLIT_MODE"], "graph" if backend == "ik_llama" else "tensor" if backend == "official-tensor" else "layer")


class ConnectionTests(unittest.TestCase):
    def test_url_normalization(self):
        self.assertEqual(normalize_url(" https://example.org/v1/ "), "https://example.org/v1")
        self.assertEqual(normalize_url("https://example.org"), "https://example.org/v1")
        for url in ("https://user:secret@example.org", "https://example.org/?key=secret", "file:///tmp/test", "https://exa mple.org"):
            with self.assertRaises(ValueError):
                normalize_url(url)

    def run_probe(self, handler, url="https://example.org/v1"):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch("connection.httpx.Client", return_value=client):
            return probe_endpoint(url, "test")

    def test_quick_tunnel_health_does_not_unlock_streaming_agents(self):
        def handler(request):
            if request.url.path == "/health": return httpx.Response(200, json={"status": "ok"})
            if request.url.path == "/v1/models": return httpx.Response(200, json={"data": [{"id": "actual-model"}]})
            return httpx.Response(200, text="")
        result = self.run_probe(handler, "https://test.trycloudflare.com/v1")
        self.assertTrue(result["online"])
        self.assertFalse(result["agents_available"])

    def test_metrics_failure_does_not_report_healthy_server_offline(self):
        def handler(request):
            if request.url.path == "/health": return httpx.Response(200, json={"status": "ok"})
            if request.url.path == "/v1/models": return httpx.Response(200, json={"data": [{"id": "actual-model"}]})
            return httpx.Response(404)
        result = self.run_probe(handler)
        self.assertTrue(result["online"])
        self.assertEqual(result["model"], "actual-model")
        self.assertIn("Telemetria indisponível", result["message"])

    def test_rejects_bad_auth_and_missing_model(self):
        self.assertFalse(self.run_probe(lambda request: httpx.Response(401))["online"])
        result = self.run_probe(lambda request: httpx.Response(200, json={"status": "ok", "data": []}))
        self.assertFalse(result["online"])


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_messages_keeps_tools_and_errors_are_not_streams(self):
        import kaggle_gateway as gateway
        captured = []
        async def handler(request):
            captured.append(request)
            return httpx.Response(400, json={"error": {"message": "invalid input"}})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as upstream:
            with patch.object(gateway, "client", upstream), patch.object(gateway, "API_KEY", "test"), patch.object(gateway, "BACKEND_FAMILY", "official-layer"):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=gateway.app), base_url="http://test") as client:
                    response = await client.post("/v1/messages", headers={"x-api-key": "test"}, json={"stream": True, "messages": [], "tools": [{"name": "read", "input_schema": {"type": "object"}}]})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn("application/json", response.headers["content-type"])
                    self.assertEqual(captured[0].url.path, "/v1/messages")
                    self.assertEqual(json.loads(captured[0].content)["tools"][0]["name"], "read")
                    response = await client.post("/v1/messages", json={})
                    self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
