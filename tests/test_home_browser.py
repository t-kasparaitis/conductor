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
    LAYOUT = "cards"

    @classmethod
    def setUpClass(cls):
        cls.b = Browser(width=1300, height=900)
        # Each test's server is a new origin, so set the remembered layout before every page.
        cls.b.init_script(f"try {{ localStorage.setItem('conductor-view-layout', '{cls.LAYOUT}') }} catch (e) {{}}")

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
    """The Cards layout, plus the sidebar and routes."""

    def test_home_lists_every_project_active_first(self):
        self.open(ready="document.querySelector('.proj-card')")
        self.assertEqual(self.js("[...document.querySelectorAll('.proj-card')].map(c => c.id)"),
                         [f"proj-{self.alpha}", "proj-beta"])
        self.assertIn("this folder", self.js("document.querySelector('.proj-card').textContent"))
        self.assertEqual(self.js("[...document.querySelectorAll('#sidebar [data-project-link]')].map(a => a.dataset.projectLink)"),
                         [self.alpha, "beta"])

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

    def test_archived_tracks_open_read_only(self):
        self.open(f"#/{self.alpha}/old_1/spec", ready="document.querySelector('.overview')")
        self.assertIn("Archived track", self.js("document.querySelector('.archived-banner').textContent"))
        self.assertEqual(self.js("document.querySelectorAll('.comment-btn, .review-actions').length"), 0)
        self.assertTrue(self.js("document.querySelector('details.side-archive').open"))
        # A live track still has its buttons.
        self.open(f"#/{self.alpha}/now_1/plan", ready="document.querySelector('.overview')")
        self.assertGreater(self.js("document.querySelectorAll('.comment-btn').length"), 0)
        self.assertEqual(self.js("document.querySelectorAll('.archived-banner').length"), 0)

    def pinned(self):
        return self.js("[...document.querySelectorAll('#sidebar [data-pinned]')].map(a => a.closest('.side-item').querySelector('[data-project]').dataset.project + '/' + a.dataset.pinned)")

    def test_sidebar_pins_open_tracks_with_their_status(self):
        self.open(ready="document.querySelector('#sidebar [data-pinned]')")
        self.assertEqual(sorted(self.pinned()), sorted([f"{self.alpha}/now_1", f"{self.alpha}/open_1", f"{self.alpha}/shared_1",
                                                        "beta/b_only", "beta/shared_1"]))
        badge = self.js(f"document.querySelector('#sidebar [data-pinned=now_1]').querySelector('.gbadge').textContent")
        self.assertEqual(badge, "Now")
        self.assertEqual(self.js("[...document.querySelectorAll('#sidebar .side-proj')].map(h => h.textContent.trim())"),
                         [self.js(f"document.querySelector('[data-project-link={self.alpha}] .t-name').textContent"), "beta"])

    def test_pin_and_unpin(self):
        self.open(f"#/{self.alpha}/done_1/plan", ready="document.querySelector('.eyebrow .pin-btn')")
        self.assertEqual(self.js("document.querySelector('.eyebrow .pin-btn').getAttribute('aria-pressed')"), "false")
        self.b.click(".eyebrow .pin-btn")
        self.b.wait("document.querySelector('#sidebar [data-pinned=done_1]')")
        self.assertIn(f"{self.alpha}/done_1", serve.load_pins()["pinned"])
        self.assertEqual(self.js("document.querySelector('#sidebar [data-pinned=done_1] .gbadge').textContent"), "Done")
        # Unpinning a track that's open by default is remembered too; pinning it again just clears that.
        self.b.click(f'#sidebar .side-item:has([data-pinned=now_1]) .pin-btn')
        self.b.wait("!document.querySelector('#sidebar [data-pinned=now_1]')")
        self.assertEqual(serve.load_pins()["unpinned"], [f"{self.alpha}/now_1"])
        self.b.click('#sidebar .side-item:has([data-track=now_1]) .pin-btn')
        self.b.wait("document.querySelector('#sidebar [data-pinned=now_1]')")
        self.assertEqual(serve.load_pins(), {"pinned": [f"{self.alpha}/done_1"], "unpinned": []})

    def test_project_sidebar_marks_status_and_archive(self):
        self.open(f"#/{self.alpha}/now_1/plan", ready="document.querySelector('.overview')")
        badges = lambda attr: self.js(f"Object.fromEntries([...document.querySelectorAll('#sidebar [{attr}]')].map(a => [a.dataset.{attr[5:]}, a.querySelector('.gbadge').textContent]))")
        # Each track once: pinned ones under Pinned (with beta's), the rest in the project's list.
        self.assertEqual(badges("data-track"), {"done_1": "Done", "old_1": "Archived"})
        self.assertEqual(badges("data-pinned"), {"now_1": "Now", "open_1": "Open", "shared_1": "Open", "b_only": "Open"})
        ids = self.js("[...document.querySelectorAll('#sidebar [data-track], #sidebar [data-pinned]')].filter(a => a.closest('.side-item').querySelector('[data-project]').dataset.project === '%s').map(a => a.dataset.track || a.dataset.pinned)" % self.alpha)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.js("[...document.querySelectorAll('#sidebar h2')].map(h => h.textContent)").count("Other tracks"), 1)

    def test_track_page_sidebar_belongs_to_its_project(self):
        self.open("#/beta/b_only/plan", ready="document.querySelector('.overview')")
        self.assertEqual(self.js("[...document.querySelectorAll('#sidebar [data-track]')].map(a => a.dataset.track)"), [])
        self.assertIn("Every open track is pinned above", self.js("document.querySelector('#sidebar').textContent"))
        self.assertEqual(self.js("document.querySelector('#project-switch').value"), "beta")
        self.b.click(".back-link")
        self.b.wait("document.querySelector('.proj-card')")
        self.assertEqual(self.js("location.hash"), "#/")

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
class HomeTableTest(HomeFixture):
    """The Table layout: one row per track, Excel-style filters, sorting and columns."""
    LAYOUT = "table"
    ROWS = "[...document.querySelectorAll('.tracks-table tbody tr')].map(r => r.dataset.row)"

    def rows(self):
        return self.js(self.ROWS)

    def menu(self, key):
        self.b.click(f'.th-filter[data-menu="{key}"] summary')
        self.b.wait(f'document.querySelector(\'.th-filter[data-menu="{key}"][open]\')')

    def test_one_row_per_track_now_first_archive_hidden(self):
        self.open(ready="document.querySelector('.tracks-table')")
        rows = self.rows()
        self.assertEqual(rows[0], f"{self.alpha}/now_1")
        self.assertEqual(sorted(rows), sorted([f"{self.alpha}/{t}" for t in ("now_1", "open_1", "done_1", "shared_1")]
                                              + ["beta/shared_1", "beta/b_only"]))
        self.assertIn("Wire the widget", self.js("document.querySelector('.tracks-table tr.g-now').textContent"))
        self.assertEqual(self.js("document.querySelector('.fchip[aria-pressed=true]').dataset.status"), "all")

    def test_status_menu_shows_archived_and_lives_in_the_link(self):
        self.open(ready="document.querySelector('.tracks-table')")
        self.menu("status")
        counts = self.js("Object.fromEntries([...document.querySelectorAll('[data-filter=status]')].map(i => [i.value, [i.checked, i.closest('label').querySelector('.count').textContent]]))")
        self.assertEqual(counts, {"now": [True, "1"], "open": [True, "4"], "done": [True, "1"], "archived": [False, "1"]})
        self.b.click('[data-filter=status][value=archived]')
        self.assertEqual(self.js("location.hash"), "#/?status=now%2Copen%2Cdone%2Carchived")
        self.assertIn(f"{self.alpha}/old_1", self.rows())
        self.assertTrue(self.js("!!document.querySelector('.th-filter[data-menu=status][open]')"))  # stays open while you tick
        self.assertEqual(self.js("document.activeElement.value"), "archived")
        self.b.click('[data-filter-set="status:none"]')
        self.assertEqual(self.rows(), [])
        self.b.click('[data-filter=status][value=done]')
        self.assertEqual(self.rows(), [f"{self.alpha}/done_1"])
        self.b.click('[data-filter-set="status:reset"]')
        self.assertEqual(self.js("location.hash"), "#/")
        self.open("#/?status=archived", ready="document.querySelector('.tracks-table tbody tr')")
        self.assertEqual(self.rows(), [f"{self.alpha}/old_1"])
        self.assertEqual(self.js("document.querySelector('.fchip[aria-pressed=true]').dataset.status"), "archived")

    def test_project_filter_and_project_links(self):
        self.open(ready="document.querySelector('.tracks-table')")
        self.menu("project")
        self.b.click('[data-filter=project][value=beta]')
        self.assertEqual(self.js("location.hash"), f"#/?project={self.alpha}")
        self.assertTrue(all(r.startswith(self.alpha + "/") for r in self.rows()))
        self.assertTrue(self.js("document.querySelector('.th-filter[data-menu=project] summary').classList.contains('on')"))
        self.assertEqual(self.js("document.querySelector('.proj-strip').id"), f"proj-{self.alpha}")
        self.open("#/beta", ready="document.querySelector('.tracks-table tbody tr')")
        self.assertEqual(sorted(self.rows()), ["beta/b_only", "beta/shared_1"])
        self.assertEqual(self.js("document.querySelector('h1').textContent"), "beta")
        self.b.click("[data-clear-filters]")
        self.assertEqual(self.js("location.hash"), "#/")
        self.assertEqual(len(self.rows()), 6)

    def test_search_covers_project_names(self):
        self.open("#/?q=beta", ready="document.querySelector('.tracks-table')")
        self.assertEqual(sorted(self.rows()), ["beta/b_only", "beta/shared_1"])
        self.open("#/?q=zzz", ready="document.querySelector('.tracks-table')")
        self.assertIn("No tracks match", self.js("document.querySelector('.table-wrap .empty').textContent"))

    def test_sorting_is_remembered(self):
        self.open(ready="document.querySelector('.tracks-table')")
        self.b.click("[data-sort=track]")
        titles = self.js("[...document.querySelectorAll('.tt-title')].map(a => a.textContent)")
        self.assertEqual(titles, sorted(titles, key=str.lower))
        self.assertEqual(self.js("document.querySelector('th.c-track').getAttribute('aria-sort')"), "ascending")
        self.b.click("[data-sort=track]")
        self.assertEqual(self.js("document.querySelector('th.c-track').getAttribute('aria-sort')"), "descending")
        self.open(ready="document.querySelector('.tracks-table')")
        self.assertEqual(self.js("document.querySelector('th.c-track').getAttribute('aria-sort')"), "descending")

    def test_columns_can_be_hidden_and_shown(self):
        self.open(ready="document.querySelector('.tracks-table')")
        self.assertEqual(self.js("document.querySelectorAll('td.c-reviews').length"), 0)  # hidden by default
        self.menu("columns")
        self.b.click("[data-col=git]")
        self.b.click("[data-col=reviews]")
        self.assertEqual(self.js("document.querySelectorAll('td.c-git').length"), 0)
        self.assertGreater(self.js("document.querySelectorAll('td.c-reviews').length"), 0)
        self.b.key("Escape")
        self.b.wait("!document.querySelector('.th-filter[open]')")
        self.open(ready="document.querySelector('.tracks-table')")
        self.assertEqual(self.js("document.querySelectorAll('td.c-git').length"), 0)

    def test_menu_closes_on_a_click_elsewhere(self):
        self.open(ready="document.querySelector('.tracks-table')")
        self.menu("status")
        self.b.click("h1")
        self.b.wait("!document.querySelector('.th-filter[open]')")

    def test_pin_from_a_row(self):
        self.open(ready="document.querySelector('.tracks-table')")
        self.b.click(f'tr[data-row="{self.alpha}/done_1"] .pin-btn')
        self.b.wait("document.querySelector('#sidebar [data-pinned=done_1]')")
        self.assertEqual(self.js(f"document.querySelector('tr[data-row=\"{self.alpha}/done_1\"] .pin-btn').getAttribute('aria-pressed')"), "true")

    def test_row_actions_open_the_request_dialog(self):
        self.open(ready="document.querySelector('.tracks-table')")
        self.b.click(f'tr[data-row="{self.alpha}/open_1"] [data-request=archive]')
        self.b.wait("document.querySelector('#dlg').open")
        self.assertIn("Archive", self.js("document.querySelector('#dlg-title').textContent"))

    def test_switch_to_cards_and_back(self):
        self.open(ready="document.querySelector('.tracks-table')")
        self.b.click("[data-layout=cards]")
        self.assertTrue(self.js("!!document.querySelector('.proj-card')"))
        self.assertEqual(self.js("localStorage.getItem('conductor-view-layout')"), "cards")
        self.b.click("[data-layout=table]")
        self.assertTrue(self.js("!!document.querySelector('.tracks-table')"))


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
