import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from integrations import (
    API_PATHS,
    Endpoint,
    configure_all,
    configure_codex,
    disconnect_all,
    is_configured,
    launch_argv,
    launch_env,
    restore_backup,
    _restrict,
)


class TestIntegrations(unittest.TestCase):
    def test_writes_configs_with_current_provider_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            endpoint = Endpoint(
                "https://example.test/v1",
                "secret-token",
                "model-x",
                context=32768,
                output=12288,
            )
            with patch("integrations.find_tool", return_value="installed"):
                results = configure_all(endpoint, home)
            self.assertTrue(all(result.ok for result in results))

            codex = (home / ".codex/config.toml").read_text()
            self.assertIn('wire_api = "responses"', codex)
            self.assertIn("[model_providers.kaggle_studio.auth]", codex)
            profile = (home / ".codex/kaggle-studio.config.toml").read_text()
            self.assertIn('model_context_window = 32768', profile)
            self.assertNotIn("secret-token", codex)
            self.assertNotIn("env_key", codex)

            token_file = home / ".codex/.kaggle-studio-token"
            self.assertEqual(token_file.read_text().strip(), "secret-token")
            if os.name != "nt" and hasattr(stat, "S_IMODE"):
                self.assertEqual(stat.S_IMODE(token_file.stat().st_mode) & 0o077, 0)

            claude_path = home / ".claude/settings.json"
            claude = json.loads(claude_path.read_text())
            self.assertEqual(claude["env"]["ANTHROPIC_BASE_URL"], "https://example.test")
            self.assertNotIn("secret-token", claude_path.read_text())
            self.assertTrue((home / ".claude/CLAUDE.md").exists())

            opencode_path = home / ".config/opencode/opencode.jsonc"
            opencode = json.loads(opencode_path.read_text())
            provider = opencode["provider"]["kaggle-studio"]
            self.assertEqual(provider["options"]["apiKey"], "{file:~/.kaggle-studio-opencode-token}")
            self.assertEqual(provider["models"]["model-x"]["limit"]["context"], 32768)
            self.assertEqual(provider["models"]["model-x"]["limit"]["output"], 12288)
            self.assertTrue((opencode_path.parent / "AGENTS.md").exists())
            self.assertEqual(
                json.loads(claude_path.read_text())["apiKeyHelper"].split()[-1].strip('"'),
                str(home / ".claude/kaggle-studio-api-key.py"),
            )
            self.assertEqual((home / ".kaggle-studio-opencode-token").read_text().strip(), "secret-token")

            zcode_desktop = json.loads((home / ".zcode/v2/config.json").read_text())
            zcode_cli = json.loads((home / ".zcode/cli/config.json").read_text())
            self.assertEqual(
                zcode_desktop["provider"]["kaggle-studio"]["options"]["baseURL"],
                "https://example.test/v1",
            )
            self.assertEqual(zcode_desktop["provider"]["kaggle-studio"]["options"]["apiKey"], "secret-token")
            self.assertNotIn("apiKey", zcode_cli["provider"]["kaggle-studio"]["options"])
            self.assertEqual(zcode_cli["model"]["main"], "kaggle-studio/model-x")

            for tool in ("codex", "claude", "opencode", "zcode"):
                self.assertTrue(is_configured(tool, home), tool)

    def test_codex_reconfigure_updates_sections_without_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".codex/config.toml"
            config.parent.mkdir(parents=True)
            config.write_text('approval_policy = "never"\n')

            configure_codex(Endpoint("https://one/v1", "token-a", "m1"), home)
            configure_codex(Endpoint("https://two/v1", "token-b", "m2"), home)
            text = config.read_text()

            self.assertEqual(text.count("[model_providers.kaggle_studio]"), 1)
            self.assertEqual(text.count("[model_providers.kaggle_studio.auth]"), 1)
            self.assertNotIn("[profiles.kaggle-studio]", text)
            self.assertTrue((home / ".codex/kaggle-studio.config.toml").exists())
            self.assertIn('approval_policy = "never"', text)
            self.assertIn('base_url = "https://two/v1"', text)
            profile = (home / ".codex/kaggle-studio.config.toml").read_text()
            self.assertIn('model = "m2"', profile)
            self.assertNotIn("https://one/v1", text)
            self.assertEqual((home / ".codex/.kaggle-studio-token").read_text().strip(), "token-b")

    def test_launch_env_exposes_all_cli_credentials(self):
        endpoint = Endpoint("https://example.test/v1", "env-token", "model-x")
        env = launch_env(endpoint)
        self.assertEqual(env["KAGGLE_STUDIO_API_KEY"], "env-token")
        self.assertEqual(env["OPENAI_API_KEY"], "env-token")
        self.assertEqual(env["OPENAI_BASE_URL"], "https://example.test/v1")
        self.assertEqual(env["ANTHROPIC_AUTH_TOKEN"], "env-token")
        self.assertEqual(env["ANTHROPIC_BASE_URL"], "https://example.test")
        self.assertEqual(env["ZCODE_API_KEY"], "env-token")
        self.assertEqual(env["ZCODE_BASE_URL"], "https://example.test/v1")

    def test_reconfigure_is_noop_when_values_are_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            endpoint = Endpoint("https://same/v1", "same-token", "same-model")
            with patch("integrations.find_tool", return_value="installed"):
                first = configure_all(endpoint, home)
                second = configure_all(endpoint, home)
            self.assertTrue(all(result.ok for result in first + second))
            self.assertTrue(all(not result.backup for result in second))

    def test_gateway_routes_are_normalised_for_all_client_protocols(self):
        endpoint = Endpoint("https://example.test/", "token", "model")
        self.assertEqual(endpoint.api_url, "https://example.test/v1")
        self.assertEqual(endpoint.root_url, "https://example.test")
        for capability, path in API_PATHS.items():
            self.assertEqual(endpoint.url_for(capability), "https://example.test" + path)
        with self.assertRaises(ValueError):
            endpoint.url_for("unknown")

    def test_uninstalled_tools_are_skipped_without_writing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with patch("integrations.find_tool", return_value=None):
                results = configure_all(Endpoint("https://example.test/v1", "token", "model"), home)
            self.assertTrue(all(not result.ok for result in results))
            self.assertTrue(all("não instalado" in result.message for result in results))
            self.assertFalse((home / ".codex").exists())

    def test_invalid_client_config_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/opencode/opencode.jsonc"
            config.parent.mkdir(parents=True)
            config.write_text('{ invalid settings')
            with patch("integrations.find_tool", return_value="installed"):
                result = configure_all(Endpoint("https://example.test/v1", "token", "model"), home)[2]
            self.assertFalse(result.ok)
            self.assertEqual(config.read_text(), "{ invalid settings")

    def test_disconnect_removes_only_kaggle_entries_and_managed_prompts(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            endpoint = Endpoint("https://example.test/v1", "token", "model")
            with patch("integrations.find_tool", return_value="installed"):
                configure_all(endpoint, home)

            (home / ".claude/CLAUDE.md").write_text("Keep this.\n" + (home / ".claude/CLAUDE.md").read_text())
            results = disconnect_all(home)
            self.assertTrue(all(result.ok for result in results))
            self.assertFalse((home / ".codex/.kaggle-studio-token").exists())
            self.assertNotIn("kaggle_studio", (home / ".codex/config.toml").read_text())
            self.assertNotIn("kaggle-studio", (home / ".config/opencode/opencode.jsonc").read_text())
            self.assertIn("Keep this.", (home / ".claude/CLAUDE.md").read_text())
            self.assertNotIn("kaggle-studio managed", (home / ".claude/CLAUDE.md").read_text())
            self.assertTrue(all(not result.backup for result in disconnect_all(home)))

    def test_restore_backup_retains_current_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"before": true}\n')
            backup = Path(str(path) + ".kaggle-studio-test.bak")
            backup.write_text('{"original": true}\n')
            current_backup = restore_backup(path, backup)
            self.assertEqual(path.read_text(), backup.read_text())
            self.assertTrue(Path(current_backup).exists())

    def test_windows_launcher_wraps_scripts_but_not_executables(self):
        with patch("integrations.os.name", "nt"):
            ps1 = launch_argv(r"C:\\tools\\codex.ps1", ["--profile", "kaggle-studio"])
            cmd = launch_argv(r"C:\\tools\\codex.cmd", ["--profile", "kaggle-studio"])
            exe = launch_argv(r"C:\\tools\\codex.exe", ["--profile", "kaggle-studio"])
        self.assertEqual(ps1[:7], ["powershell.exe", "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", r"C:\\tools\\codex.ps1"])
        self.assertEqual(cmd[:4], ["cmd.exe", "/d", "/s", "/c"])
        self.assertTrue(cmd[4].startswith("call "))
        self.assertEqual(exe, [r"C:\\tools\\codex.exe", "--profile", "kaggle-studio"])

    def test_windows_secret_acl_uses_account_specific_icacls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "token"
            path.write_text("secret")
            with patch("integrations.os.name", "nt"), patch.dict(
                "integrations.os.environ", {"USERNAME": "user", "USERDOMAIN": "DOMAIN"}, clear=False
            ), patch("integrations.subprocess.run") as run:
                _restrict(path)
        self.assertEqual(run.call_args.args[0][:5], ["icacls", str(path), "/inheritance:r", "/grant:r", "DOMAIN\\user:(R,W)"])
        self.assertTrue(run.call_args.kwargs["check"])


if __name__ == "__main__":
    unittest.main()
