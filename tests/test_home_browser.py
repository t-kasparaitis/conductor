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


class HomeFixture(UserHome, ServerTest):
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


@unittest.skipUnless(find_browser(), "test browser not installed")
class HomeBrowserTest(HomeFixture):
    """Project cards, the sidebar and routes."""

    def test_home_lists_every_project_active_first(self):
        self.open(ready="document.querySelector('.proj-card')")
        self.assertEqual(self.js("[...document.querySelectorAll('.proj-card')].map(c => c.id)"),
                         [f"proj-{self.alpha}", "proj-beta"])
        self.assertIn("this folder", self.js("document.querySelector('.proj-card').textContent"))
        self.assertEqual(self.js("[...document.querySelectorAll('#sidebar [data-project-link]')].map(a => a.dataset.projectLink)"),
                         [self.alpha, "beta"])

    def test_tracks_are_grouped_with_in_progress_first(self):
        self.open(ready="document.querySelector('.proj-card')")
        groups = self.js("""[...document.querySelector('.proj-card').querySelectorAll('.tgroup')]
            .map(g => [g.className.match(/g-(\\w+)/)[1], g.querySelectorAll('.trow').length])""")
        self.assertEqual(groups, [["now", 1], ["open", 2], ["done", 1]])  # archived only when its status is on
        self.assertIn("Wire the widget", self.js("document.querySelector('.trow.g-now').textContent"))

    def test_clicking_a_row_opens_the_track_with_the_project_in_the_link(self):
        self.open(ready="document.querySelector('.trow.g-now a')")
        self.b.click(".trow.g-now a.trow-title")
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
        self.assertEqual(self.js("document.querySelectorAll('.trow[data-row]').length"), 1)
        self.assertEqual(self.js("document.querySelector('.fchip[aria-pressed=true]').dataset.status"), "archived")
        self.b.click('.fchip[data-status="now"]')
        self.assertEqual(self.js("location.hash"), "#/?status=archived%2Cnow")
        self.assertEqual(sorted(self.js("[...document.querySelectorAll('.trow[data-row]')].map(r => r.querySelector('.mono').textContent)")), ["now_1", "old_1"])
        self.open("#/?q=zzz", ready="document.querySelector('.empty')")
        self.assertIn("No tracks match", self.js("document.querySelector('.empty').textContent"))

    def test_archived_tracks_open_read_only(self):
        self.open(f"#/{self.alpha}/old_1/spec", ready="document.querySelector('.overview')")
        self.assertIn("Archived track", self.js("document.querySelector('.archived-banner').textContent"))
        self.assertEqual(self.js("document.querySelectorAll('.comment-btn, .review-actions').length"), 0)
        # A live track still has its buttons.
        self.open(f"#/{self.alpha}/now_1/plan", ready="document.querySelector('.overview')")
        self.assertGreater(self.js("document.querySelectorAll('.comment-btn').length"), 0)
        self.assertEqual(self.js("document.querySelectorAll('.archived-banner').length"), 0)

    SIDE = "[...document.querySelectorAll('#sidebar [data-track]')].map(a => a.dataset.project + '/' + a.dataset.track)"

    def test_sidebar_lists_unfinished_tracks_by_project(self):
        self.open(ready="document.querySelector('#sidebar [data-track]')")
        self.assertEqual(sorted(self.js(self.SIDE)), sorted([f"{self.alpha}/now_1", f"{self.alpha}/open_1", f"{self.alpha}/shared_1",
                                                             "beta/b_only", "beta/shared_1"]))  # not done_1 or old_1
        self.assertEqual(self.js(self.SIDE)[0], f"{self.alpha}/now_1")  # Now first
        self.assertEqual(self.js("document.querySelectorAll('#sidebar .gbadge').length"), 0)  # % ring says enough
        self.assertEqual(self.js("document.querySelector('.fchip[data-status=now]').firstChild.textContent.trim()"), "In progress")
        self.assertEqual(len(self.js("[...document.querySelectorAll('#sidebar .side-proj')]")), 2)
        self.assertEqual(self.js("document.querySelectorAll('.pin-btn, [data-pin]').length"), 0)

    def test_active_tracks_collapse_and_show_their_count(self):
        self.open(ready="document.querySelector('.side-active')")
        self.assertEqual(self.js("document.querySelector('.side-active summary').textContent.trim()"), "Active tracks · 5")
        self.assertTrue(self.js("document.querySelector('.side-active').open"))
        self.b.click(".side-active summary")
        self.b.wait("!document.querySelector('.side-active').open")
        self.open(ready="document.querySelector('.side-active')")  # remembered
        self.assertFalse(self.js("document.querySelector('.side-active').open"))
        self.b.click(".side-active summary")
        self.b.wait("document.querySelector('.side-active').open")

    def test_track_page_sidebar_puts_its_project_first(self):
        self.open("#/beta/b_only/plan", ready="document.querySelector('.overview')")
        side = self.js(self.SIDE)
        self.assertEqual(side[:2], ["beta/b_only", "beta/shared_1"])
        self.assertEqual(len(side), len(set(side)))  # each track once
        self.assertEqual(self.js("document.querySelector('#sidebar [aria-current=true]').dataset.track"), "b_only")
        self.assertEqual(self.js("document.querySelector('#project-switch').value"), "beta")
        self.b.click(".back-link")
        self.b.wait("document.querySelector('.proj-card')")
        self.assertEqual(self.js("location.hash"), "#/")

    def test_done_tracks_leave_the_sidebar(self):
        self.open(f"#/{self.alpha}/done_1/plan", ready="document.querySelector('.overview')")
        self.assertNotIn(f"{self.alpha}/done_1", self.js(self.SIDE))

    def test_add_by_path(self):
        gamma = self.beta.parent / "gamma"
        (gamma / "conductor").mkdir(parents=True)
        (gamma / "conductor/index.md").write_text("# G\n")
        self.open(ready="document.querySelector('[data-dialog=add]')")
        self.b.click("[data-dialog=add]")
        self.js("document.querySelector('#add-path').value = " + repr(str(self.beta.parent / "nope")))
        self.b.click("#add-form [type=submit]")
        self.b.wait("document.querySelector('.dlg-status').textContent.includes('conductor/index.md')")
        self.js("document.querySelector('#add-path').value = " + repr(str(gamma)))
        self.b.click("#add-form [type=submit]")
        self.b.wait("location.hash === '#/gamma' && document.querySelector('#proj-gamma.focused')")
        self.assertFalse(self.js("document.querySelector('#dlg').open"))

    def test_find_projects(self):
        for name in ("one", "two"):
            (self.beta.parent / "found" / name / "conductor").mkdir(parents=True)
            (self.beta.parent / "found" / name / "conductor/index.md").write_text("# P\n")
        self.open(ready="document.querySelector('[data-dialog=find]')")
        self.b.click("[data-dialog=find]")
        self.js("document.querySelector('#find-roots').value = " + repr(str(self.beta.parent)))
        self.b.click("[data-find]")
        self.b.wait("document.querySelectorAll('.found li').length === 3")
        rows = self.js("[...document.querySelectorAll('.found li')].map(li => [li.textContent.trim().split(/\\s+/)[0], li.querySelector('input').disabled])")
        self.assertEqual(rows, [["beta", True], ["one", False], ["two", False]])
        self.js("document.querySelectorAll('.found input')[2].checked = false")
        self.b.click("#find-form [type=submit]")
        self.b.wait("document.querySelectorAll('.proj-card').length === 3")
        self.assertEqual(sorted(e["id"] for e in serve.registered_projects()), ["beta", "one"])

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


@unittest.skipUnless(find_browser(), "test browser not installed")
class HomeFiltersTest(HomeFixture):
    """Status toggles, the Project and Git menus, sorting, and row actions."""
    ROWS = "[...document.querySelectorAll('.trow[data-row]')].map(r => r.dataset.row)"

    def rows(self):
        return self.js(self.ROWS)

    def menu(self, key):
        self.b.click(f'.th-filter[data-menu="{key}"] summary')
        self.b.wait(f'document.querySelector(\'.th-filter[data-menu="{key}"][open]\')')

    def test_progress_is_numbers_not_bars(self):
        self.open("#/", ready="document.querySelector('.trow[data-row] .prog-count')")
        cells = self.js("[...document.querySelectorAll('.trow[data-row] .c-progress')].map((c) => [c.querySelector('.prog-count').textContent, c.querySelector('.prog-phase').textContent])")
        for count, phase in cells:
            self.assertRegex(count, r"^\d+/\d+ tasks$")
            self.assertRegex(phase, r"^(phase \d+ of \d+|all \d+ phases? done|no plan yet)$")
        self.assertIsNone(self.js("document.querySelector('.pbar, .pseg')"))
        # The ring carries its percentage, like the sidebar's.
        labels = self.js("[...document.querySelectorAll('.trow[data-row] .c-progress .ring')].map((r) => getComputedStyle(r, '::after').content)")
        self.assertTrue(labels and all(l.strip('"').endswith("%") for l in labels), labels)

    def test_columns_line_up_across_rows(self):
        self.open(ready="document.querySelector('.trow[data-row]')")
        lefts = self.js("[...document.querySelectorAll('.trow[data-row] .c-progress')].map(c => c.getBoundingClientRect().left)")
        self.assertLessEqual(max(lefts) - min(lefts), 1)

    def test_status_toggles_and_archived_off_by_default(self):
        self.open(ready="document.querySelector('.trow[data-row]')")
        self.assertNotIn(f"{self.alpha}/old_1", self.rows())
        self.assertIn("1 more hidden by the status filter (archived)", self.js(f"document.querySelector('#proj-{self.alpha}').textContent"))
        self.b.click('.fchip[data-status="archived"]')
        self.assertEqual(self.js("location.hash"), "#/?status=now%2Copen%2Cdone%2Carchived")
        self.assertIn(f"{self.alpha}/old_1", self.rows())
        self.b.click('.fchip[data-status="archived"]')
        self.assertEqual(self.js("location.hash"), "#/")
        self.b.click('.fchip[data-status="open"]')
        self.b.click('.fchip[data-status="done"]')
        self.assertEqual(self.rows(), [f"{self.alpha}/now_1"])
        self.assertEqual(self.js("[...document.querySelectorAll('.fchip[aria-pressed=true]')].map(b => b.dataset.status)"), ["now"])

    def test_project_menu(self):
        self.open(ready="document.querySelector('.trow[data-row]')")
        self.menu("project")
        self.b.click('[data-filter=project][value=beta]')
        self.assertEqual(self.js("location.hash"), f"#/?project={self.alpha}")
        self.assertTrue(all(r.startswith(self.alpha + "/") for r in self.rows()))
        self.assertTrue(self.js("!!document.querySelector('.th-filter[data-menu=project][open]')"))  # stays open while you tick
        self.b.click("h1")
        self.b.wait("!document.querySelector('.th-filter[open]')")
        self.b.click("[data-clear-filters]")
        self.assertEqual(self.js("location.hash"), "#/")
        self.assertEqual(len(self.rows()), 6)

    def test_git_menu(self):
        self.open(ready="document.querySelector('.trow[data-row]')")
        self.menu("git")
        self.assertEqual(self.js("[...document.querySelectorAll('[data-filter=git]')].map(i => i.value)"), ["nogit"])
        self.b.key("Escape")
        self.b.wait("!document.querySelector('.th-filter[open]')")

    def test_sort_is_remembered(self):
        self.open(ready="document.querySelector('#home-sort')")
        self.js("const s = document.querySelector('#home-sort'); s.value = 'name'; s.dispatchEvent(new Event('change', {bubbles: true}))")
        titles = self.js(f"[...document.querySelectorAll('#proj-{self.alpha} .tgroup.g-open .trow-title')].map(a => a.textContent)")
        self.assertEqual(titles, sorted(titles, key=str.lower))
        self.open(ready="document.querySelector('#home-sort')")
        self.assertEqual(self.js("document.querySelector('#home-sort').value"), "name")

    def test_search_covers_project_names(self):
        self.open("#/?q=beta", ready="document.querySelector('.proj-card')")
        self.assertEqual(sorted(self.rows()), ["beta/b_only", "beta/shared_1"])

    def test_row_actions_always_visible_and_open_the_dialog(self):
        self.open(ready="document.querySelector('.trow[data-row]')")
        row = f'.trow[data-row="{self.alpha}/open_1"] .row-actions'
        self.assertEqual(self.js(f"getComputedStyle(document.querySelector('{row}')).opacity"), "1")
        self.b.click(f'.trow[data-row="{self.alpha}/open_1"] [data-request=archive]')
        self.b.wait("document.querySelector('#dlg').open")
        self.assertIn("Archive", self.js("document.querySelector('#dlg-title').textContent"))


@unittest.skipUnless(find_browser(), "test browser not installed")
class PhoneWidthTest(UserHome, ServerTest):
    def test_no_sideways_scroll_on_a_phone(self):
        self.write("conductor/index.md", "# P\n")
        self.write("conductor/tracks.md", REGISTRY)
        self.write("conductor/tracks/now_1/plan.md", PLAN_NOW)
        self.write("conductor/tracks/now_1/spec.md", "# A rather long track title that goes on and on for a while\n")
        b = Browser(width=390, height=844)
        try:
            pid = serve._project_id(self.root, set())
            for hash_ in ("#/", "#/settings", f"#/{pid}/settings", f"#/{pid}/now_1/plan"):
                b.goto("about:blank")
                b.goto(f"http://127.0.0.1:{self.port}/{hash_}", ready="document.querySelector('main').children.length > 1")
                self.assertLessEqual(b.js("document.documentElement.scrollWidth"), b.js("window.innerWidth"), hash_)
        finally:
            b.close()
