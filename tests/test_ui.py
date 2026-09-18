import unittest
from pathlib import Path

from models_catalog import MODELS
from state_store import AppState


class UiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.html = (root / "ui" / "index.html").read_text("utf-8")
        cls.js = (root / "ui" / "app.js").read_text("utf-8")
        cls.translations = (root / "ui" / "i18n.js").read_text("utf-8")

    def test_light_theme_is_fixed(self):
        self.assertIn('<html lang="pt-BR" data-theme="light">', self.html)
        self.assertIn('name="color-scheme" content="light"', self.html)
        self.assertNotIn('data-theme="dark"', self.html)

    def test_runtime_has_context_and_output_presets(self):
        for value in (8192, 16384, 32768, 65536, 131072):
            self.assertIn(f'data-value="{value}"', self.html)
        self.assertIn('data-preset-group="context"', self.html)
        self.assertIn('data-preset-group="output"', self.html)
        self.assertIn('id="context"', self.html)
        self.assertIn('id="output"', self.html)

    def test_prebuilt_cuda_is_primary_backend(self):
        self.assertEqual(AppState().backend, "official-layer")
        self.assertTrue(all(model["backend"] == "official-layer" for model in MODELS.values() if not model.get("required_backend")))
        self.assertIn('value="official-layer">CUDA prebuilt', self.html)
        self.assertIn('CUDA prebuilt é o padrão', self.html)

    def test_sidebar_and_mascot_exist(self):
        self.assertIn('class="app-sidebar"', self.html)
        self.assertIn('assets/penguin-guide.png', self.html)
        self.assertIn('ative <b>Internet</b>', self.html)

    def test_kaggle_flow_is_explicit(self):
        self.assertIn('Copiar célula 1', self.html)
        self.assertIn('id="runtimeCode"', self.html)
        self.assertIn('BASE URL →', self.html)
        self.assertIn('API KEY →', self.html)
        self.assertIn('Copiado. Execute no Kaggle', self.translations)
        self.assertIn('Pegue BASE URL e API KEY', self.translations)

    def test_single_decision_screens_and_accessibility_hooks_exist(self):
        for screen in ("welcome", "model", "context", "output", "review", "environment", "cell1", "cell2", "connect", "agents", "ready"):
            self.assertIn(f'data-screen="{screen}"', self.html)
        self.assertIn('aria-live="polite"', self.html)
        self.assertIn('prefers-reduced-motion:reduce', (Path(__file__).resolve().parents[1] / 'ui' / 'styles.css').read_text('utf-8'))


if __name__ == "__main__":
    unittest.main()
