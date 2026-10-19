"""World-map input in a real browser: mouse drag, wheel zoom, trackpad-style
ctrl+wheel and two-finger touch pinch."""

import re
import unittest

from browser import Browser, browser_name, find_chrome
from helpers import ServerTest

MAP = ('{"title": "M", "nodes": [' + ", ".join(f'{{"id": "n{i}", "label": "Node {i}"}}' for i in range(6)) + '], '
       '"edges": [' + ", ".join(f'{{"from": "n{i}", "to": "n{i + 1}"}}' for i in range(5)) + ']}')


@unittest.skipUnless(find_chrome() and browser_name() == "chrome", "needs Chrome, Chromium or Edge (uses DevTools input events)")
class MapInputTest(ServerTest):
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
        self.write("conductor/tracks/demo_1/diagrams/m.json", MAP)
        self.b.goto("about:blank")
        self.b.goto(f"http://127.0.0.1:{self.port}/#/demo_1/diagrams/m", ready="window.WorldMap && window.WorldMap.isOpen()")
        self.b.js("new Promise(r => setTimeout(r, 900))")  # let the opening fly-in finish

    def cam(self):
        t = self.b.js("document.querySelector('.wm-world').style.transform")
        x, y, k = (float(v) for v in re.match(r"translate\(([-\d.e]+)px, ([-\d.e]+)px\) scale\(([-\d.e]+)\)", t).groups())
        return x, y, k

    def mouse(self, kind, x, y, **extra):
        self.b.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left", buttons=1 if kind != "mouseReleased" else 0,
                    clickCount=1, **extra)

    def test_drag_pans(self):
        x0, y0, k0 = self.cam()
        self.mouse("mousePressed", 300, 650)
        for step in range(1, 6):
            self.mouse("mouseMoved", 300 + step * 30, 650 + step * 10)
        self.mouse("mouseReleased", 450, 700)
        x1, y1, k1 = self.cam()
        self.assertAlmostEqual(x1 - x0, 150, delta=2)
        self.assertAlmostEqual(y1 - y0, 50, delta=2)
        self.assertEqual(k1, k0)

    def test_wheel_zooms_and_trackpad_pinch_zooms(self):
        k0 = self.cam()[2]
        self.b.call("Input.dispatchMouseEvent", type="mouseWheel", x=600, y=400, deltaX=0, deltaY=-300)
        k1 = self.cam()[2]
        self.assertGreater(k1, k0)
        self.b.call("Input.dispatchMouseEvent", type="mouseWheel", x=600, y=400, deltaX=0, deltaY=40, modifiers=2)  # ctrl = pinch
        self.assertLess(self.cam()[2], k1)

    def test_two_finger_pinch_zooms_on_touch_screens(self):
        k0 = self.cam()[2]
        def touch(kind, spread):
            pts = [] if kind == "touchEnd" else [{"x": 600 - spread, "y": 600, "id": 1}, {"x": 600 + spread, "y": 600, "id": 2}]
            self.b.call("Input.dispatchTouchEvent", type=kind, touchPoints=pts)
        touch("touchStart", 50)
        for spread in (70, 90, 110, 130):
            touch("touchMove", spread)
        touch("touchEnd", 0)
        self.assertAlmostEqual(self.cam()[2] / k0, 130 / 50, delta=0.15)

    def test_keyboard_moves_and_escape_closes(self):
        x0 = self.cam()[0]
        self.b.js("document.querySelector('.wm-viewport').focus()")
        self.b.key("ArrowLeft", key_code=37)
        self.assertNotEqual(self.cam()[0], x0)
        self.b.key("Escape", key_code=27)
        self.b.wait("!window.WorldMap.isOpen()")


if __name__ == "__main__":
    unittest.main()
