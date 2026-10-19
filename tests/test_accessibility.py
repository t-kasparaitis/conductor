"""Keyboard use, accessible names, themes and blocked storage, in a real browser."""

import unittest

from browser import Browser, find_chrome
from test_viewer_browser import PLAN, SPEC
from helpers import ServerTest

NAMELESS = """[...document.querySelectorAll('button, a[href], [role=tab], [role=radio], input, textarea')]
  .filter(el => !el.hidden && el.type !== 'hidden' && el.offsetParent !== null)
  .filter(el => !((el.getAttribute('aria-label') || '').trim() || (el.textContent || '').trim() ||
                  (el.getAttribute('title') || '').trim() || (el.labels && el.labels.length) || el.placeholder))
  .map(el => el.outerHTML.slice(0, 120))"""


@unittest.skipUnless(find_chrome(), "no Chrome, Chromium or Edge installed")
class AccessibilityTest(ServerTest):
    @classmethod
    def setUpClass(cls):
        cls.b = Browser(width=1300, height=800)

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# P\n")
        self.write("conductor/tracks/demo_1/plan.md", PLAN)
        self.write("conductor/tracks/demo_1/spec.md", SPEC)
        self.write("conductor/tracks/demo_1/diagrams/map.json",
                   '{"title": "M", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], '
                   '"edges": [{"from": "a", "to": "b"}], "tour": ["a", "b"]}')

    def open(self, hash_):
        self.b.goto("about:blank")
        self.b.goto(f"http://127.0.0.1:{self.port}/{hash_}", ready="document.querySelector('main').children.length")

    def test_every_control_has_a_name(self):
        for view in ("#/demo_1/plan", "#/demo_1/spec", "#/demo_1/diagrams", "#/demo_1/feedback", "#/settings"):
            self.open(view)
            self.assertEqual(self.b.js(NAMELESS), [], view)

    def test_map_controls_have_names(self):
        self.open("#/demo_1/diagrams/map")
        self.b.wait("window.WorldMap.isOpen()")
        self.assertEqual(self.b.js(NAMELESS), [])

    def test_keyboard_reaches_and_uses_the_progress_bar(self):
        self.open("#/demo_1/plan")
        self.b.js("document.querySelector('.pg-phase[data-goto-phase=\"2\"]').focus()")
        self.b.key("Enter", key_code=13)
        self.b.wait("document.querySelector('article.phase') && document.querySelector('article.phase').id === 'phase-2'")
        self.b.js("document.querySelector('.pg-task[data-goto-task=\"0/0\"]').focus()")
        self.b.key(" ", code="Space", key_code=32)
        self.b.wait("document.querySelector('article.phase').id === 'phase-0'")

    def test_focus_is_visible(self):
        self.open("#/demo_1/plan")
        self.b.js("document.querySelector('.tab').focus()")
        self.b.key("Tab", key_code=9)
        style = self.b.js("getComputedStyle(document.activeElement).outlineStyle")
        self.assertNotEqual(style, "none")

    def test_tabs_and_dialog_by_keyboard(self):
        self.open("#/demo_1/plan")
        self.b.js("document.querySelector('[data-tab=spec]').focus()")
        self.b.key("Enter", key_code=13)
        self.b.wait("location.hash.includes('/spec')")
        self.b.js("document.querySelector('[data-tab=plan]').click()")
        self.b.js("document.querySelector('.task .comment-btn').focus()")
        self.b.key("Enter", key_code=13)
        self.b.wait("document.querySelector('#composer').open")
        self.assertEqual(self.b.js("document.activeElement.id"), "composer-text")
        self.b.key("Escape", key_code=27)
        self.b.wait("!document.querySelector('#composer').open")

    def test_light_and_dark_themes(self):
        self.open("#/demo_1/plan")
        start = self.b.js("document.documentElement.dataset.theme")
        self.b.click("#theme-toggle")
        flipped = self.b.js("document.documentElement.dataset.theme")
        self.assertEqual({start, flipped}, {"light", "dark"})
        self.assertNotEqual(self.b.js("getComputedStyle(document.body).backgroundColor"), "rgba(0, 0, 0, 0)")

    def test_works_with_storage_blocked(self):
        blocker = self.b.init_script(
            "Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('blocked', 'SecurityError'); } });")
        try:
            self.open("#/demo_1/plan")
            self.b.wait("document.querySelector('article.phase')")
            self.b.click('[data-show-all="plan"]')
            self.assertEqual(self.b.js("document.querySelectorAll('article.phase').length"), 3)
            self.b.click("#theme-toggle")
        finally:
            self.b.remove_init_script(blocker)


if __name__ == "__main__":
    unittest.main()
