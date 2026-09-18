import json
import re
import tempfile
import unittest
from pathlib import Path

from models_catalog import MODELS
from runtime_builder import RuntimeBuilder
from localization import LANGUAGES, MESSAGES
from state_store import AppState, StateStore


ROOT = Path(__file__).resolve().parents[1]


class LocalizationContractTests(unittest.TestCase):
    """Small contracts for the PT-BR/English preference.

    These tests intentionally check behavior and public hooks, rather than
    enumerating every copy string.  Copy can evolve without making the test
    suite a second translation file.
    """

    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "ui" / "index.html").read_text("utf-8")
        cls.scripts = "\n".join(
            path.read_text("utf-8")
            for path in sorted((ROOT / "ui").glob("*.js"))
        )

    def test_state_exposes_supported_languages_and_defaults_to_portuguese(self):
        state = AppState()
        self.assertEqual(state.language, "pt-BR")
        self.assertIn("language", AppState.__dataclass_fields__)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            store = StateStore(path)
            store.save(AppState(language="en", context=32768, backend="official-layer"))
            loaded = store.load()
            self.assertEqual(loaded.language, "en")
            self.assertEqual(loaded.context, 32768)
            self.assertEqual(loaded.backend, "official-layer")

    def test_invalid_saved_language_falls_back_without_resetting_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(
                json.dumps({"language": "fr", "context": 65536, "parallel": 4}),
                "utf-8",
            )
            state = StateStore(path).load()
            self.assertEqual(state.language, "pt-BR")
            self.assertEqual(state.context, 65536)
            self.assertEqual(state.parallel, 4)

    def test_selector_is_accessible_and_has_both_locales(self):
        self.assertRegex(self.html, r'<select[^>]+id=["\']language(?:Select|Selector)?["\']')
        self.assertRegex(self.html, r'<option[^>]+value=["\']pt-BR["\']')
        self.assertRegex(self.html, r'<option[^>]+value=["\']en["\']')
        selector = re.search(r'<select[^>]+id=["\']language(?:Select|Selector)?["\'][\s\S]*?</select>', self.html)
        self.assertIsNotNone(selector)
        self.assertRegex(selector.group(0), r'(aria-label|labelledby)=')

    def test_frontend_has_dictionary_and_switch_path(self):
        # Keep names stable for the Qt bridge and browser preview.  The
        # dictionary may live in app.js or a separate ui/*.js module.
        self.assertRegex(self.scripts, r'(?i)(translations?|i18n)')
        self.assertRegex(self.scripts, r'\bsetLanguage\s*\(')
        self.assertRegex(self.scripts, r'(?i)(pt-BR|en)')
        self.assertRegex(self.scripts, r'(?i)(languageChanged|language)')

    def test_frontend_dictionary_keys_match_between_locales(self):
        section = self.scripts.split("const dictionaries = {", 1)[1].split("const staticTranslations", 1)[0]
        pt = section.split("'pt-BR': {", 1)[1].split("},\n    en: {", 1)[0]
        en = section.split("en: {", 1)[1]
        key_pattern = re.compile(r'(?:^|,)\s*([A-Za-z][A-Za-z0-9_]*)\s*:')
        self.assertEqual(set(key_pattern.findall(pt)), set(key_pattern.findall(en)))

        static = self.scripts.split("const staticTranslations = {", 1)[1]
        static_pt = static.split("'pt-BR': {", 1)[1].split("},\n    en: {", 1)[0]
        static_en = static.split("en: {", 1)[1].split("\n  };", 1)[0]
        selector_keys = re.compile(r"['\"]([^'\"]+)['\"]\s*:")
        self.assertEqual(set(selector_keys.findall(static_pt)), set(selector_keys.findall(static_en)))

    def test_backend_message_catalog_keys_and_placeholders_match(self):
        self.assertEqual(set(MESSAGES["pt-BR"]), set(MESSAGES["en"]))
        for key in MESSAGES["pt-BR"]:
            self.assertEqual(
                set(re.findall(r"\{(\w+)\}", MESSAGES["pt-BR"][key])),
                set(re.findall(r"\{(\w+)\}", MESSAGES["en"][key])),
                key,
            )
        self.assertEqual(set(LANGUAGES), {"pt-BR", "en"})

    def test_generated_kaggle_cells_compile_in_both_languages(self):
        builder = RuntimeBuilder(ROOT)
        for language in ("pt-BR", "en"):
            state = AppState(language=language)
            compile(builder.install_cell(language=language), "<install-cell>", "exec")
            notebook = builder.notebook(MODELS["gemopus"], state)
            self.assertIn("cells", __import__("json").loads(notebook))
            self.assertIn(
                "Kaggle Studio" if language == "en" else "Ative Internet",
                notebook,
            )

    def test_switch_does_not_require_rebuilding_runtime_configuration(self):
        # Language is a UI preference. It must not be sent as a model/runtime
        # option, which would risk replacing values during a locale switch.
        collect = re.search(r'function\s+collectOptions\s*\([^)]*\)\s*\{([\s\S]*?)\n\}', self.scripts)
        if collect:
            self.assertNotRegex(collect.group(1), r'\blanguage\b')


if __name__ == "__main__":
    unittest.main()
