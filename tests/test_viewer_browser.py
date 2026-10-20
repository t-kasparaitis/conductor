"""The viewer in a real headless browser: frozen overview, focus mode, safe
rendering. Skipped when no Chrome, Chromium or Edge is installed."""

import unittest

from browser import Browser, find_browser
from helpers import ServerTest

PLAN = """# Implementation Plan: Demo

> Planned under: test settings.

## Phase 1: Done Already

- [x] Task: First thing abc1234
- [x] Task: Second thing def5678

## Phase 2: Doing Now

- [x] Task: Started 1234567
- [~] Task: Working on it
- [ ] Task: Next up <img src=x onerror="window.pwned=1">

## Phase 3: Later

""" + "".join(f"- [ ] Task: Later task {i}\n    - [ ] A sub-task with some words to make it longer\n" for i in range(30))

SPEC = """# Demo Spec

## Overview

What this is.

## Functional Requirements

Lots of requirements.

## Open Questions

-   Anything?
"""


@unittest.skipUnless(find_browser(), "test browser not installed")
class ViewerBrowserTest(ServerTest):
    @classmethod
    def setUpClass(cls):
        cls.browser = Browser(width=1300, height=800)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()

    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# Project Context\n")
        self.write("conductor/tracks.md", "# Tracks\n\n---\n\n- [~] **Track: Demo track**\n*Link: [./tracks/demo_1/index.md](./tracks/demo_1/index.md)*\n")
        self.write("conductor/tracks/demo_1/metadata.json", '{"track_id": "demo_1", "type": "feature", "status": "in_progress"}')
        self.write("conductor/tracks/demo_1/plan.md", PLAN)
        self.write("conductor/tracks/demo_1/spec.md", SPEC)
        self.b = self.browser

    def open(self, hash_="#/demo_1/plan"):
        # Each test serves on a new port, so it is a new origin with empty storage.
        self.b.goto("about:blank")
        self.b.goto(f"http://127.0.0.1:{self.port}/{hash_}", ready="document.querySelector('.overview')")

    def visible_phases(self):
        return self.b.js("[...document.querySelectorAll('article.phase')].map(a => a.id)")

    def test_plan_opens_on_the_active_phase_only(self):
        self.open()
        self.assertEqual(self.visible_phases(), ["phase-1"])
        self.assertIn("/phase-2", self.b.js("location.hash"))

    def test_clicking_a_phase_bar_switches_to_it(self):
        self.open()
        self.b.click('.pg[data-goto-phase="2"]')
        self.assertEqual(self.visible_phases(), ["phase-2"])
        self.assertTrue(self.b.js("location.hash.endsWith('/phase-3')"))
        self.assertEqual(self.b.js("document.querySelector('.pg[aria-current=true]').dataset.gotoPhase"), "2")

    def test_phase_buttons_show_tasks_done_as_numbers(self):
        self.open()
        counts = self.b.js("[...document.querySelectorAll('.progress-groups .pg')].map((p) => p.querySelector('.pg-count').textContent)")
        self.assertEqual(len(counts), 3)
        self.assertTrue(all(c.count("/") == 1 and all(n.isdigit() for n in c.split("/")) for c in counts), counts)
        self.assertIsNone(self.b.js("document.querySelector('.pg-task')"))
        # A short plan names its phases; past five phases only the numbers show.
        self.assertGreater(self.b.js("document.querySelector('.pg-name').offsetWidth"), 0)

    def test_pager_moves_between_phases(self):
        self.open("#/demo_1/plan/phase-1")
        self.assertEqual(self.visible_phases(), ["phase-0"])
        self.b.click(".pager .pager-next")
        self.assertEqual(self.visible_phases(), ["phase-1"])

    def test_show_all_phases(self):
        self.open()
        self.b.click('[data-show-all="plan"]')
        self.assertEqual(self.visible_phases(), ["phase-0", "phase-1", "phase-2"])
        self.assertTrue(self.b.js("location.hash.endsWith('/phase-all')"))

    def test_overview_stays_frozen_under_the_top_bar(self):
        self.open("#/demo_1/plan/phase-3")
        self.b.js("window.scrollTo(0, document.body.scrollHeight)")
        self.b.wait("window.scrollY > 300")
        top = self.b.js("Math.round(document.querySelector('#overview').getBoundingClientRect().top)")
        bar = self.b.js("document.querySelector('.topbar').offsetHeight")
        self.assertEqual(top, bar)

    def test_switching_phase_while_scrolled_keeps_content_below_the_overview(self):
        self.open("#/demo_1/plan/phase-3")
        self.b.js("window.scrollTo(0, document.body.scrollHeight)")
        self.b.click('.pg[data-goto-phase="0"]')
        gap = self.b.js("""(() => {
          const ov = document.querySelector('#overview').getBoundingClientRect();
          const ph = document.querySelector('article.phase').getBoundingClientRect();
          return Math.round(ph.top - ov.bottom); })()""")
        self.assertGreaterEqual(gap, 0)
        self.assertLess(gap, 200)

    def test_spec_shows_one_section_with_chips(self):
        self.open("#/demo_1/spec")
        self.assertEqual(self.b.js("document.querySelectorAll('.spec-section').length"), 1)
        self.b.click('.spec-toc [data-focus="spec:2"]')
        self.assertIn("Open Questions", self.b.js("document.querySelector('.spec-section').textContent"))
        self.assertTrue(self.b.js("location.hash.endsWith('/section-3')"))

    def test_pasting_a_link_into_an_open_tab_follows_it(self):
        self.open()
        self.b.js("location.hash = '#/demo_1/spec/section-2'")
        self.b.wait("document.querySelector('.spec-section')")
        self.assertIn("Functional Requirements", self.b.js("document.querySelector('.spec-section').textContent"))

    def test_task_text_is_escaped(self):
        self.open("#/demo_1/plan/phase-2")
        self.assertIsNone(self.b.js("window.pwned"))
        self.assertEqual(self.b.js("document.querySelectorAll('main img[src=x]').length"), 0)


if __name__ == "__main__":
    unittest.main()
