"""Raw diagrams/<slug>.svg files: drawn on the same pannable canvas, never able
to run script, in the card thumbnail or the open map."""

import unittest

from browser import Browser, find_browser
from helpers import ServerTest

HOSTILE = """<svg xmlns="http://www.w3.org/2000/svg" width="900" height="500" onload="parent.pwned = 'onload'">
  <script>parent.pwned = 'script'; top.pwned = 'script';</script>
  <rect width="900" height="500" fill="#3fc1c9"/>
  <image href="http://127.0.0.1:9/beacon.png" width="10" height="10"/>
  <foreignObject width="100" height="100"><div xmlns="http://www.w3.org/1999/xhtml"><img src="x" onerror="parent.pwned='fo'"/></div></foreignObject>
</svg>"""

VIEWBOX_ONLY = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300"><circle cx="200" cy="150" r="100"/></svg>'


@unittest.skipUnless(find_browser(), "test browser not installed")
class SvgDiagramTest(ServerTest):
    @classmethod
    def setUpClass(cls):
        cls.b = Browser(width=1200, height=800)

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# P\n")
        self.write("conductor/tracks/demo_1/plan.md", "# P\n")
        self.write("conductor/tracks/demo_1/diagrams/hostile.svg", HOSTILE)
        self.write("conductor/tracks/demo_1/diagrams/plain.svg", VIEWBOX_ONLY)

    def open(self, hash_, ready):
        self.b.goto("about:blank")
        self.b.goto(f"http://127.0.0.1:{self.port}/{hash_}", ready=ready)
        self.b.js("new Promise(r => setTimeout(r, 600))")

    def test_cards_show_svgs_as_images_without_running_them(self):
        self.open("#/demo_1/diagrams", "document.querySelectorAll('.diagram-card img').length === 2")
        self.assertIsNone(self.b.js("window.pwned === undefined ? null : window.pwned"))
        self.assertEqual(self.b.js("document.querySelectorAll('main svg script, main foreignObject').length"), 0)

    def test_open_svg_on_the_canvas_without_running_it(self):
        self.open("#/demo_1/diagrams/hostile", "document.querySelector('.wm-img') && document.querySelector('.wm-img').complete")
        self.assertIsNone(self.b.js("window.pwned === undefined ? null : window.pwned"))
        self.assertEqual(self.b.js("[document.querySelector('.wm-img').width, document.querySelector('.wm-img').height]"), [900, 500])
        self.assertEqual(self.b.js("document.querySelectorAll('.wm svg script').length"), 0)

    def test_viewbox_only_svg_still_gets_a_size_and_fits(self):
        self.open("#/demo_1/diagrams/plain", "document.querySelector('.wm-img') && document.querySelector('.wm-img').complete")
        w, h = self.b.js("[document.querySelector('.wm-img').width, document.querySelector('.wm-img').height]")
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)
        r = self.b.js("(() => { const b = document.querySelector('.wm-img').getBoundingClientRect(); return [b.left, b.right, b.top, b.bottom]; })()")
        self.assertGreaterEqual(r[0], -1)
        self.assertLessEqual(r[1], 1201)


if __name__ == "__main__":
    unittest.main()
