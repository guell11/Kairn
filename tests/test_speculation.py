import unittest

from runtime_support import llama_command


class SpeculationTests(unittest.TestCase):
    def test_auto_uses_ngram_only_when_server_advertises_it(self):
        help_text = "--spec-type none,draft-simple,ngram-simple\n  --spec-draft-n-max N\n --spec-ngram-simple-size-m N"
        command = llama_command("server", "model.gguf", "model", 1024, 1,
                               "layer", help_text, speculation="auto", draft_tokens=8)
        self.assertIn("--spec-type", command)
        self.assertIn("ngram-simple", command)
        self.assertEqual(command[command.index("--spec-ngram-simple-size-m") + 1], "8")
        self.assertNotIn("--spec-draft-n-max", command)

    def test_auto_falls_back_when_fork_has_no_speculation_flag(self):
        command = llama_command("server", "model.gguf", "model", 1024, 1,
                               "layer", "--flash-attn", speculation="auto")
        self.assertNotIn("--spec-type", command)

    def test_off_never_enables_ngram(self):
        command = llama_command("server", "model.gguf", "model", 1024, 1,
                               "layer", "--spec-type none,ngram-simple", speculation="off")
        self.assertNotIn("ngram-simple", command)

    def test_forced_ngram_rejects_unsupported_server(self):
        with self.assertRaises(RuntimeError):
            llama_command("server", "model.gguf", "model", 1024, 1,
                          "layer", "--spec-type none,draft-simple", speculation="ngram")


if __name__ == "__main__":
    unittest.main()
