"""The settings schema is the single source of truth for setup, skills and the
viewer, so a malformed schema breaks all three. Run from the repo root:

    python3 -m unittest discover -s tests
"""

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEMA = REPO / "skills" / "conductor-setup" / "assets" / "settings.schema.json"


def load_schema():
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


def all_settings(schema):
    return [st for g in schema["groups"] for st in g["settings"]]


class SchemaShapeTest(unittest.TestCase):
    def setUp(self):
        self.schema = load_schema()

    def test_version_and_file(self):
        self.assertEqual(self.schema["version"], 1)
        self.assertEqual(self.schema["file"], "conductor/settings.json")

    def test_keys_are_unique_and_belong_to_their_group(self):
        keys = []
        for g in self.schema["groups"]:
            self.assertTrue(g["label"] and g["summary"], g["id"])
            for st in g["settings"]:
                group, _, name = st["key"].partition(".")
                self.assertEqual(group, g["id"], st["key"])
                self.assertTrue(name, st["key"])
                keys.append(st["key"])
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_setting_has_labelled_unique_options_and_a_valid_default(self):
        for st in all_settings(self.schema):
            values = [o["value"] for o in st["options"]]
            self.assertGreaterEqual(len(values), 2, st["key"])
            self.assertEqual(len(values), len(set(values)), st["key"])
            self.assertIn(st["default"], values, st["key"])
            for o in st["options"]:
                self.assertTrue(o["label"].strip() and o["summary"].strip(), f'{st["key"]}={o["value"]}')

    def test_defaults_keep_upstream_behaviour(self):
        defaults = {st["key"]: st["default"] for st in all_settings(self.schema)}
        self.assertEqual(defaults, {
            "git.strategy": "current",
            "git.commit": "task",
            "git.push": "ask",
            "git.notes": "on",
            "testing.style": "tdd",
            "testing.verification": "phase",
        })

    def test_no_option_ever_force_pushes_main(self):
        for st in all_settings(self.schema):
            for o in st["options"]:
                for line in o.get("detail", "").splitlines():
                    if "--force" in line:
                        self.assertNotIn("main", line.split("#")[0], line)


class RepoSettingsTest(unittest.TestCase):
    """This repo's own conductor/settings.json must stay valid."""

    def test_repo_settings_match_schema(self):
        settings = json.loads((REPO / "conductor" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(settings.pop("version"), 1)
        by_key = {st["key"]: st for st in all_settings(load_schema())}
        for group, values in settings.items():
            for name, value in values.items():
                key = f"{group}.{name}"
                self.assertIn(key, by_key)
                self.assertIn(value, [o["value"] for o in by_key[key]["options"]], key)


class WorkflowDocTest(unittest.TestCase):
    """workflow.md tells agents what each setting does; it must list exactly
    the schema's settings and values, default first."""

    def table(self, path):
        rows = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\| `([a-z]+\.[a-z]+)` \| (.+?) \|", line)
            if m:
                rows[m.group(1)] = re.findall(r"`([^`]+)`", m.group(2))
        return rows

    def expected(self):
        out = {}
        for st in all_settings(load_schema()):
            values = [o["value"] for o in st["options"]]
            values.remove(st["default"])
            out[st["key"]] = [st["default"]] + values
        return out

    def test_template_table_matches_schema(self):
        self.assertEqual(self.table(REPO / "skills" / "conductor-setup" / "assets" / "workflow.md"), self.expected())

    def test_repo_copy_table_matches_schema(self):
        self.assertEqual(self.table(REPO / "conductor" / "workflow.md"), self.expected())


if __name__ == "__main__":
    unittest.main()
