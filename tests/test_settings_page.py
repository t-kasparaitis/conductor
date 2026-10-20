"""The settings page in a real browser: main rules with an exception list, and
a project's page with value sources, Use main rule and Tidy."""

import json
import unittest

from browser import Browser, find_browser
from helpers import ServerTest, UserHome, serve


@unittest.skipUnless(find_browser(), "test browser not installed")
class SettingsPageTest(UserHome, ServerTest):
    @classmethod
    def setUpClass(cls):
        cls.b = Browser(width=1300, height=900)

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# P\n")
        self.pid = serve._project_id(self.root, set())
        (self.home / "settings.json").write_text(json.dumps({"git": {"strategy": "trunk"}}))
        self.write_settings({"version": 1, "git": {"strategy": "feature-branch", "commit": "task"}})

    def open(self, hash_, ready):
        self.b.goto("about:blank")
        self.b.goto(f"http://127.0.0.1:{self.port}/{hash_}", ready=ready)

    def js(self, expr):
        return self.b.js(expr)

    def main_rules(self):
        return json.loads((self.home / "settings.json").read_text())

    def test_main_page_lists_exceptions_and_resets_them(self):
        self.open("#/settings", ready="document.querySelector('.exc')")
        text = self.js("document.querySelector('.exc').textContent")
        self.assertIn("Feature branch", text)
        self.assertIn("main rule: Trunk", text)
        self.b.click(".exc [data-reset='git.strategy']")
        self.b.wait("!document.querySelector('.exc')")
        self.assertEqual(self.settings_file()["git"], {"commit": "task"})

    def test_main_page_offers_tidy_for_repeated_rules(self):
        self.open("#/settings", ready="document.querySelector('[data-tidy]')")
        self.assertIn("Commit granularity", self.js("document.querySelector('.exceptions .banner').textContent"))
        self.b.click("[data-tidy]")
        self.b.wait("!document.querySelector('.exceptions [data-tidy]')")
        self.assertEqual(self.settings_file(), {"version": 1, "git": {"strategy": "feature-branch"}})

    def test_changing_a_main_rule(self):
        self.open("#/settings", ready="document.querySelector('.opt')")
        self.b.click('.opt[data-setting="git.push"][data-value="phase"]')
        self.b.wait("document.querySelector('.opt[data-setting=\"git.push\"][data-value=\"phase\"]').getAttribute('aria-checked') === 'true'")
        self.assertEqual(self.main_rules()["git"], {"strategy": "trunk", "push": "phase"})
        self.assertNotIn("push", self.settings_file()["git"])  # the repo is untouched

    def test_project_page_shows_sources_and_sets_exceptions(self):
        self.open(f"#/{self.pid}/settings", ready="document.querySelector('.opt')")
        chip = lambda key: self.js(f"document.querySelector('.opt[data-setting=\"{key}\"]').closest('.setting').querySelector('.setting-head .chip').textContent")
        self.assertEqual(chip("git.strategy"), "this repo's exception")
        self.assertEqual(chip("git.commit"), "same as main rule")
        self.assertEqual(chip("git.push"), "built-in default")
        self.assertEqual(self.js("document.querySelector('[data-follow]').getAttribute('aria-pressed')"), "false")
        self.b.click('.opt[data-setting="testing.style"][data-value="after"]')
        self.b.wait(f"""document.querySelector('.opt[data-setting="testing.style"][data-value="after"]').getAttribute('aria-checked') === 'true'""")
        self.assertEqual(self.settings_file()["testing"], {"style": "after"})
        self.b.click("[data-reset='testing.style']")
        self.b.wait("!document.querySelector(\"[data-reset='testing.style']\")")
        self.assertNotIn("testing", self.settings_file())

    def test_follow_main_rules_removes_every_exception(self):
        self.open(f"#/{self.pid}/settings", ready="document.querySelector('[data-follow]')")
        self.js("window.confirm = () => true")
        self.b.click("[data-follow]")
        self.b.wait("document.querySelector('[data-follow]').getAttribute('aria-pressed') === 'true'")
        self.assertEqual(self.settings_file(), {"version": 1})

    def test_workflow_chips_on_a_track_lead_to_the_project_page(self):
        self.write("conductor/tracks/t_1/plan.md", "# P\n\n## Phase 1: A\n\n- [ ] Task: x\n")
        self.open(f"#/{self.pid}/t_1/plan", ready="document.querySelector('.chip.wf')")
        self.b.click(".chip.wf")
        self.b.wait("document.querySelector('.follow')")
        self.assertEqual(self.js("location.hash"), f"#/{self.pid}/settings")


    def test_header_gear_opens_settings_and_no_live_pill(self):
        self.write("conductor/tracks/t_1/plan.md", "# P\n\n## Phase 1: A\n\n- [ ] Task: x\n")
        for start in ("#/", f"#/{self.pid}/t_1/plan"):
            self.open(start, ready="document.querySelector('#settings-btn') && document.querySelector('.track-link')")
            self.assertTrue(self.js("document.querySelector('#live').hidden"), start)
            self.assertFalse(self.js("document.querySelector('#settings-btn').hidden"), start)
            self.b.click("#settings-btn")
            self.b.wait("document.querySelector('#port-form')")
            self.assertEqual(self.js("location.hash"), "#/settings")
            self.assertEqual(self.js("document.querySelector('#settings-btn').getAttribute('aria-current')"), "page")
        # The main rules moved to the header; the home sidebar no longer repeats them.
        self.open("#/", ready="document.querySelector('.track-link')")
        self.assertIsNone(self.js("document.querySelector('.sidebar a[href=\"#/settings\"]')"))

    def test_port_can_be_saved_and_cleared(self):
        self.open("#/settings", ready="document.querySelector('#port-form')")
        self.assertIn(f"now: {self.port}", self.js("document.querySelector('#port').textContent"))
        self.js("document.querySelector('#port-input').value = '80'")
        self.b.click("#port-form [type=submit]")
        self.b.wait("document.querySelector('#toast').textContent.includes('1024')")
        self.assertFalse((self.home / "config.json").exists())
        self.js("document.querySelector('#port-input').value = '5222'")
        self.b.click("#port-form [type=submit]")
        self.b.wait("document.querySelector('[data-port-clear]')")
        self.assertEqual(json.loads((self.home / "config.json").read_text()), {"port": 5222})
        self.assertIn("next time the viewer starts", self.js("document.querySelector('#port').textContent"))
        self.b.click("[data-port-clear]")
        self.b.wait("!document.querySelector('[data-port-clear]')")
        self.assertEqual(json.loads((self.home / "config.json").read_text()), {})


if __name__ == "__main__":
    unittest.main()
