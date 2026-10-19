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


def option_values(key):
    st = next(st for st in all_settings(load_schema()) if st["key"] == key)
    return [o["value"] for o in st["options"]]


class SkillsObeySettingsTest(unittest.TestCase):
    """Each core skill loads settings.json and covers every value it acts on."""

    def test_core_skills_load_settings_in_their_handshake(self):
        for name in ("conductor-new-track", "conductor-implement", "conductor-review", "conductor-status"):
            handshake = section(skill(name), "## 1. Handshake")
            self.assertIn("read `conductor/settings.json` if it exists", handshake, name)

    def test_new_track_shapes_plans_for_every_testing_value(self):
        plan = section(skill("conductor-new-track"), "### 2.3 Interactive Plan Generation")
        for key in ("testing.style", "testing.verification"):
            for value in option_values(key):
                self.assertIn(f"`{value}`", plan, f"{key}={value}")
        self.assertIn("## Phase N: Track Verification", plan)

    def test_new_track_creates_the_branch_before_writing_files(self):
        artifacts = section(skill("conductor-new-track"), "### 2.4 Create Track Artifacts")
        branch, workspace = artifacts.index("**Track Branch"), artifacts.index("Create the track's workspace")
        self.assertLess(branch, workspace)
        self.assertIn("--unset-upstream", artifacts)

    def test_implement_handles_every_strategy_and_never_lands_on_main(self):
        text = skill("conductor-implement")
        for value in option_values("git.strategy"):
            self.assertIn(f"`{value}`", text, value)
        self.assertIn("Re-read `settings.json`", text)
        self.assertIn("Never merge into or push to `main` yourself", text)

    def test_review_checks_every_setting(self):
        compliance = section(skill("conductor-review"), "### 2.3 Analyze and Verify")
        for st in all_settings(load_schema()):
            self.assertIn(f"`{st['key']}`", compliance, st["key"])


class ViewSkillTest(unittest.TestCase):
    def setUp(self):
        self.text = skill("conductor-view")

    def test_paths_it_names_exist(self):
        base = SKILLS / "conductor-view"
        for rel in ("scripts/serve.py", "assets/viewer/index.html", "references/file-contract.md"):
            self.assertIn(rel.replace("scripts/", "<skill>/scripts/").replace("assets/", "<skill>/assets/").replace("references/", "<skill>/references/"), self.text)
            self.assertTrue((base / rel).is_file(), rel)

    def test_flags_it_names_exist(self):
        serve_py = (SKILLS / "conductor-view" / "scripts" / "serve.py").read_text(encoding="utf-8")
        commands = re.findall(r"`[^`]*serve\.py[^`]*`", self.text)
        flags = {f for c in commands for f in re.findall(r"--[a-z]+", c)}
        self.assertEqual(flags, {"--root", "--open", "--export", "--watch"})
        for flag in flags:
            self.assertIn(f'"{flag}"', serve_py, flag)

    def test_viewer_loads_nothing_from_the_internet(self):
        viewer = SKILLS / "conductor-view" / "assets" / "viewer"
        for f in viewer.iterdir():
            urls = re.findall(r"https?://[^\"' )]+", f.read_text(encoding="utf-8"))
            self.assertEqual([u for u in urls if not u.startswith("http://www.w3.org/")], [], f.name)

    def test_example_diagram_is_valid(self):
        from helpers import serve
        example = json.loads(re.search(r"```json\n(.*?)```", self.text, re.S).group(1))
        # The example's edge points at a node that isn't shown; give it one.
        example["nodes"].append({"id": "server", "label": "serve.py"})
        self.assertIsNone(serve._diagram_problem(example))


class VisualCompanionHooksTest(unittest.TestCase):
    def test_core_skills_mention_the_viewer_and_its_feedback_file(self):
        for name in ("conductor-new-track", "conductor-implement", "conductor-review", "conductor-status"):
            text = skill(name)
            self.assertIn("`conductor-view`", text, name)
            self.assertIn("feedback.md", text, name)


if __name__ == "__main__":
    unittest.main()
