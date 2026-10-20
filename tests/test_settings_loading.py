"""How the viewer reads conductor/settings.json: defaults, flags and errors."""

import unittest

from helpers import TempProject, serve

DEFAULTS = {
    "git.strategy": "current",
    "git.commit": "task",
    "git.push": "ask",
    "git.notes": "on",
    "testing.style": "tdd",
    "testing.verification": "phase",
}


def values(result):
    return {k: v["value"] for k, v in result["effective"].items()}


def sources(result):
    return {k: v["source"] for k, v in result["effective"].items()}


class LoadSettingsTest(TempProject):
    def test_missing_file_means_defaults(self):
        result = serve.load_settings(self.root)
        self.assertFalse(result["exists"])
        self.assertIsNone(result["error"])
        self.assertEqual(values(result), DEFAULTS)
        self.assertEqual(set(sources(result).values()), {"default"})

    def test_values_from_file_override_defaults(self):
        self.write_settings({"version": 1, "git": {"strategy": "trunk"}, "testing": {"verification": "track"}})
        result = serve.load_settings(self.root)
        self.assertEqual(values(result), {**DEFAULTS, "git.strategy": "trunk", "testing.verification": "track"})
        self.assertEqual(sources(result)["git.strategy"], "repo")
        self.assertEqual(sources(result)["git.commit"], "default")

    def test_unknown_value_falls_back_to_default_and_is_flagged(self):
        self.write_settings({"git": {"strategy": "gitflow", "push": ["not", "a", "string"]}})
        result = serve.load_settings(self.root)
        self.assertEqual(values(result)["git.strategy"], "current")
        self.assertEqual(sources(result)["git.strategy"], "invalid")
        self.assertEqual(sources(result)["git.push"], "invalid")

    def test_broken_json_is_reported_not_raised(self):
        self.write_settings('{"git": {')
        result = serve.load_settings(self.root)
        self.assertTrue(result["exists"])
        self.assertIn("settings.json", result["error"])
        self.assertEqual(values(result), DEFAULTS)

    def test_non_object_json_is_reported(self):
        self.write_settings("[1, 2]")
        self.assertIn("JSON object", serve.load_settings(self.root)["error"])

    def test_state_includes_settings(self):
        self.write_settings({"git": {"notes": "off"}})
        state = serve.load_state(self.root)
        self.assertEqual(state["settings"]["effective"]["git.notes"]["value"], "off")


if __name__ == "__main__":
    unittest.main()
