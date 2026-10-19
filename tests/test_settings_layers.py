"""Main rules for every project, exceptions per repo: resolution, sources,
reset to the main rule, and Tidy."""

import json

from helpers import ServerTest, UserHome, serve


class LayersTest(UserHome, ServerTest):
    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# P\n")

    def main(self, obj):
        (self.home / "settings.json").write_text(json.dumps(obj))

    def eff(self, key):
        return serve.load_settings(self.root)["effective"][key]

    def test_main_rule_applies_where_the_repo_is_silent(self):
        self.main({"git": {"strategy": "trunk"}})
        self.assertEqual((self.eff("git.strategy")["value"], self.eff("git.strategy")["source"]), ("trunk", "main"))
        self.assertEqual(self.eff("git.commit")["source"], "default")

    def test_repo_value_is_an_exception(self):
        self.main({"git": {"strategy": "trunk", "commit": "phase"}})
        self.write_settings({"git": {"strategy": "feature-branch", "commit": "phase"}})
        s = serve.load_settings(self.root)
        self.assertEqual(s["effective"]["git.strategy"]["value"], "feature-branch")
        self.assertEqual((s["effective"]["git.strategy"]["source"], s["effective"]["git.strategy"]["main"]), ("repo", "trunk"))
        self.assertEqual(s["exceptions"], ["git.strategy"])
        self.assertEqual(s["same_as_main"], ["git.commit"])

    def test_invalid_repo_value_falls_back_to_the_main_rule(self):
        self.main({"testing": {"style": "after"}})
        self.write_settings({"testing": {"style": "yolo"}})
        self.assertEqual((self.eff("testing.style")["value"], self.eff("testing.style")["source"]), ("after", "invalid"))

    def test_unreadable_main_rules_are_set_aside(self):
        self.main("not json")
        (self.home / "settings.json").write_text("{nope")
        self.assertEqual(self.eff("git.strategy")["source"], "default")
        self.assertIn("settings.json", serve.CONFIG_PROBLEMS)

    def test_setting_and_resetting_over_http(self):
        status, _ = self.request("POST", "/api/settings", {"scope": "main", "key": "git.push", "value": "phase"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads((self.home / "settings.json").read_text())["git"], {"push": "phase"})
        self.assertEqual(self.eff("git.push")["source"], "main")
        self.post_setting("git.push", "track")
        self.assertEqual(self.eff("git.push")["source"], "repo")
        status, _ = self.request("POST", "/api/settings", {"key": "git.push", "value": None})  # use main rule
        self.assertEqual(status, 200)
        self.assertEqual((self.eff("git.push")["value"], self.eff("git.push")["source"]), ("phase", "main"))
        self.assertNotIn("git", self.settings_file())  # emptied parent removed
        self.request("POST", "/api/settings", {"scope": "main", "key": "git.push", "value": None})
        self.assertEqual(self.eff("git.push")["source"], "default")
        self.assertEqual(self.request("POST", "/api/settings", {"scope": "galaxy", "key": "git.push", "value": "phase"})[0], 400)

    def test_tidy_removes_only_keys_equal_to_the_main_rule(self):
        self.main({"git": {"strategy": "trunk", "notes": "off"}})
        self.write_settings({"version": 1, "git": {"strategy": "trunk", "commit": "task", "push": "track", "notes": "off"},
                             "testing": {"style": "tdd"}, "custom": {"keep": True}})
        status, body = self.request("POST", "/api/settings/tidy", {})
        self.assertEqual(status, 200)
        # commit=task and style=tdd equal the built-in defaults the main rules fall back to.
        self.assertEqual(sorted(body["removed"]), ["git.commit", "git.notes", "git.strategy", "testing.style"])
        self.assertEqual(self.settings_file(), {"version": 1, "git": {"push": "track"}, "custom": {"keep": True}})
        self.assertEqual(serve.load_settings(self.root)["exceptions"], ["git.push"])

    def test_home_cards_show_exceptions_and_follow_main_rule_changes(self):
        self.write_settings({"git": {"strategy": "trunk"}})
        card = lambda: self.request("GET", "/api/projects")[1]["projects"][0]
        self.assertEqual(card()["exceptions"], ["git.strategy"])
        self.main({"git": {"strategy": "trunk"}})
        self.assertEqual((card()["exceptions"], card()["same_as_main"]), ([], ["git.strategy"]))
        home = self.request("GET", "/api/projects")[1]
        self.assertEqual(home["main_settings"]["effective"]["git.strategy"]["value"], "trunk")
