"""The skills are Markdown that agents follow literally, so the examples and
links in them must match the schema and the files they describe."""

import json
import re
import unittest

from test_settings_schema import REPO, all_settings, load_schema

SKILLS = REPO / "skills"


def skill(name):
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def section(text, heading):
    start = text.index(heading)
    nxt = re.search(r"^#{2,3} ", text[start + len(heading):], re.M)
    return text[start:start + len(heading) + (nxt.start() if nxt else len(text))]


class SetupSkillTest(unittest.TestCase):
    def setUp(self):
        self.text = skill("conductor-setup")
        self.step = section(self.text, "### 2.6 Repository Workflow")

    def test_example_settings_are_the_schema_defaults(self):
        example = json.loads(re.search(r"```json\n(.*?)```", self.step, re.S).group(1))
        self.assertEqual(example.pop("version"), 1)
        flat = {f"{g}.{k}": v for g, vals in example.items() for k, v in vals.items()}
        self.assertEqual(flat, {st["key"]: st["default"] for st in all_settings(load_schema())})

    def test_step_reads_the_schema_and_links_the_file(self):
        self.assertIn("assets/settings.schema.json", self.step)
        self.assertTrue((SKILLS / "conductor-setup" / "assets" / "settings.schema.json").is_file())
        self.assertIn("[Workflow Settings](./settings.json)", self.step)

    def test_index_template_links_settings(self):
        handshake = section(self.text, "## 3. The Handshake")
        self.assertIn("[Workflow Settings](./settings.json)", handshake)

    def test_initialized_projects_without_settings_are_offered_the_step(self):
        audit = section(self.text, "### 1.2 Audit Artifacts")
        self.assertIn("conductor/settings.json", audit)
        self.assertIn("Section 2.6", audit)


if __name__ == "__main__":
    unittest.main()
