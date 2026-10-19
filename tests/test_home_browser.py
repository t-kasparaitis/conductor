"""The home page in a real browser: every project's card, grouped track rows,
routes with a project in them, and old links that still work."""

import shutil
import tempfile
import unittest
from pathlib import Path

from browser import Browser, find_browser
from helpers import ServerTest, UserHome, serve

PLAN_NOW = "# P\n\n## Phase 1: Build\n\n- [x] Task: one abc1234\n- [~] Task: Wire the widget\n- [ ] Task: three\n"
PLAN_OPEN = "# P\n\n## Phase 1: A\n\n- [ ] Task: one\n"
REGISTRY = ("- [~] **Track: Alpha now**\n*Link: [x](./tracks/now_1/index.md)*\n"
            "- [ ] **Track: Alpha open**\n*Link: [x](./tracks/open_1/index.md)*\n"
            "- [x] **Track: Alpha done**\n*Link: [x](./tracks/done_1/index.md)*\n")


@unittest.skipUnless(find_browser(), "test browser not installed")
class HomeBrowserTest(UserHome, ServerTest):
    @classmethod
    def setUpClass(cls):
        cls.b = Browser(width=1300, height=900)

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# Alpha\n")
        self.write("conductor/tracks.md", REGISTRY)
        self.write("conductor/tracks/now_1/plan.md", PLAN_NOW)
        self.write("conductor/tracks/now_1/spec.md", "# Now Spec\n")
        self.write("conductor/tracks/open_1/plan.md", PLAN_OPEN)
        self.write("conductor/tracks/done_1/plan.md", "# P\n\n## Phase 1: A\n\n- [x] Task: one\n")
        self.write("conductor/tracks/shared_1/spec.md", "# Alpha Shared\n")
        self.write("conductor/archive/old_1/spec.md", "# Old Work\n")
        self.alpha = serve._project_id(self.root, set())
        base = Path(tempfile.mkdtemp(prefix="conductor-home-"))
        self.addCleanup(shutil.rmtree, base, True)
        self.beta = base / "beta"
        for tid, spec in (("shared_1", "# Beta Shared\n"), ("b_only", "# Beta Only\n")):
            (self.beta / "conductor/tracks" / tid).mkdir(parents=True)
            (self.beta / "conductor/tracks" / tid / "spec.md").write_text(spec)
        (self.beta / "conductor/index.md").write_text("# Beta\n")
        serve.add_project(self.beta)

    def open(self, hash_="#/", ready="document.querySelector('main').children.length"):
        self.b.goto("about:blank")
        self.b.goto(f"http://127.0.0.1:{self.port}/{hash_}", ready=ready)

    def js(self, expr):
        return self.b.js(expr)

    def test_home_lists_every_project_active_first(self):
        self.open(ready="document.querySelector('.proj-card')")
        self.assertEqual(self.js("[...document.querySelectorAll('.proj-card')].map(c => c.id)"),
                         [f"proj-{self.alpha}", "proj-beta"])
        self.assertIn("this folder", self.js("document.querySelector('.proj-card').textContent"))
        self.assertEqual(self.js("document.querySelectorAll('#sidebar a.track-link').length"), 4)  # home, rules, 2 projects

    def test_tracks_are_grouped_with_now_first_and_archive_collapsed(self):
        self.open(ready="document.querySelector('.proj-card')")
        groups = self.js("""[...document.querySelector('.proj-card').querySelectorAll('.tgroup')]
            .map(g => [g.className.match(/g-(\\w+)/)[1], g.querySelectorAll('.trow').length])""")
        self.assertEqual(groups, [["now", 1], ["open", 2], ["done", 1], ["archived", 1]])
        self.assertIn("Wire the widget", self.js("document.querySelector('.trow.g-now').textContent"))
        self.assertFalse(self.js("document.querySelector('details.g-archived').open"))

    def test_clicking_a_row_opens_the_track_with_the_project_in_the_link(self):
        self.open(ready="document.querySelector('.trow.g-now a')")
        self.b.click(".trow.g-now a.trow-main")
        self.b.wait("document.querySelector('.overview')")
        self.assertEqual(self.js("location.hash"), f"#/{self.alpha}/now_1/plan/phase-1")
        self.assertEqual(self.js("document.querySelector('h1').textContent"), "Now Spec")

    def test_old_links_without_a_project_still_work(self):
        self.open("#/now_1/plan", ready="document.querySelector('.overview')")
        self.assertEqual(self.js("location.hash"), f"#/{self.alpha}/now_1/plan/phase-1")
        self.open("#/b_only/spec", ready="document.querySelector('.overview')")
        self.assertEqual(self.js("location.hash"), "#/beta/b_only/spec/section-1")
        # In both projects: the one the viewer was started for wins.
        self.open("#/shared_1/spec", ready="document.querySelector('.overview')")
        self.assertEqual(self.js("document.querySelector('h1').textContent"), "Alpha Shared")

    def test_same_track_id_in_two_projects(self):
        self.open("#/beta/shared_1/spec", ready="document.querySelector('.overview')")
        self.assertEqual(self.js("document.querySelector('h1').textContent"), "Beta Shared")
        self.js("""fetch('api/feedback', {method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({project: 'beta', track: 'shared_1', text: 'to beta'})}).then(r => window.__s = r.status)""")
        self.b.wait("window.__s")
        self.assertIn("to beta", (self.beta / "conductor/tracks/shared_1/feedback.md").read_text())

    def test_project_link_focuses_its_card(self):
        self.open("#/beta", ready="document.querySelector('.proj-card.focused')")
        self.assertEqual(self.js("document.querySelector('.proj-card.focused').id"), "proj-beta")
        self.assertEqual(self.js("document.querySelector('#project-switch').value"), "beta")

    def test_switching_project_from_the_header(self):
        self.open(ready="document.querySelector('#project-switch')")
        self.js("const s = document.querySelector('#project-switch'); s.value = 'beta'; s.dispatchEvent(new Event('change', {bubbles: true}))")
        self.b.wait("location.hash === '#/beta'")
        self.b.wait("document.querySelector('.proj-card.focused')")

    def test_search_and_status_chips_live_in_the_link(self):
        self.open(ready="document.querySelector('#home-search')")
        self.js("const s = document.querySelector('#home-search'); s.value = 'beta only'; s.dispatchEvent(new Event('input', {bubbles: true}))")
        self.assertEqual(self.js("location.hash"), "#/?q=beta+only")
        self.assertEqual(self.js("[...document.querySelectorAll('.proj-card')].map(c => c.id)"), ["proj-beta"])
        self.assertEqual(self.js("document.activeElement.id"), "home-search")  # typing keeps focus
        self.open("#/?status=archived", ready="document.querySelector('.proj-card')")
        self.assertTrue(self.js("document.querySelector('details.g-archived').open"))
        self.assertEqual(self.js("document.querySelectorAll('.trow').length"), 1)
        self.assertEqual(self.js("document.querySelector('.fchip[aria-pressed=true]').dataset.status"), "archived")
        self.b.click('.fchip[data-status="now"]')
        self.assertEqual(self.js("location.hash"), "#/?status=now")
        self.assertEqual(self.js("[...document.querySelectorAll('.trow')].map(r => r.querySelector('.mono').textContent)"), ["now_1"])
        self.open("#/?q=zzz", ready="document.querySelector('.empty')")
        self.assertIn("No tracks match", self.js("document.querySelector('.empty').textContent"))

    def test_unknown_links_go_home(self):
        self.open("#/nope/zzz/plan", ready="document.querySelector('.proj-card')")
        self.assertEqual(self.js("location.hash"), "#/")

    def test_missing_project_is_shown_with_forget(self):
        shutil.rmtree(self.beta)
        self.open(ready="document.querySelector('.proj-card.missing')")
        card = self.js("document.querySelector('.proj-card.missing').textContent")
        self.assertIn("Folder not found", card)
        self.assertTrue(self.js("!!document.querySelector('.proj-card.missing [data-forget=beta]')"))

    def test_new_project_appears_live(self):
        self.open(ready="document.querySelectorAll('.proj-card').length === 2")
        gamma = self.beta.parent / "gamma"
        (gamma / "conductor").mkdir(parents=True)
        (gamma / "conductor/index.md").write_text("# G\n")
        serve.add_project(gamma)
        self.b.wait("document.querySelectorAll('.proj-card').length === 3", timeout=8)


if __name__ == "__main__":
    unittest.main()
