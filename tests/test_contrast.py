"""Text in the viewer meets WCAG AA contrast (4.5:1) in both themes. Computed
from the colour tokens in style.css, blending translucent backgrounds."""

import re
import unittest

from helpers import REPO

CSS = (REPO / "skills" / "conductor-view" / "assets" / "viewer" / "style.css").read_text(encoding="utf-8")

# (text token, background token, layered on) for every text/background pair the viewer draws.
PAIRS = [
    ("text", "bg", None), ("text", "panel", None), ("text", "bg-2", None),
    ("text-2", "panel", None), ("text-2", "bg", None), ("text-2", "accent-soft", "bg"),
    ("muted", "bg", None), ("muted", "panel", None), ("muted", "bg-2", None),
    ("accent", "bg", None), ("accent", "panel", None), ("accent", "accent-soft", "panel"),
    ("done", "done-soft", "panel"), ("done", "done-soft", "bg"),
    ("prog", "prog-soft", "panel"), ("prog", "prog-soft", "bg"),
    ("accent-ink", "accent", None), ("accent-ink", "done", None),
    ("danger", "panel", None),
    # Home page: the highlighted "Now" rows, warning banners, pressed filter chips, hovered rows.
    # (Muted text is too faint on the tinted ones, so those use --text-2.)
    ("text", "prog-soft", "panel"), ("text-2", "prog-soft", "panel"), ("text", "prog-soft", "bg"),
    ("text", "accent-soft", "panel"), ("text-2", "accent-soft", "panel"),
    ("text", "panel-2", None), ("text-2", "panel-2", None), ("muted", "panel-2", None),
    ("accent-ink", "danger", None),
    # Status badges in the sidebar.
    # The home table: current task, links and badges on plain and hovered rows.
    ("prog", "panel", None), ("prog", "panel-2", None), ("accent", "panel-2", None), ("text-2", "panel-2", None),
    ("prog", "prog-soft", "bg-2"), ("done", "done-soft", "bg-2"), ("text-2", "bg-2", None),
]


def tokens(block_selector):
    block = re.search(re.escape(block_selector) + r"\s*\{(.*?)\}", CSS, re.S).group(1)
    return dict(re.findall(r"--([\w-]+):\s*([^;]+);", block))


def rgba(value):
    value = value.strip()
    m = re.fullmatch(r"#([0-9a-f]{6})", value, re.I)
    if m:
        h = m.group(1)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (1.0,)
    m = re.fullmatch(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", value)
    if m:
        return tuple(int(m.group(i)) for i in (1, 2, 3)) + (float(m.group(4)),)
    raise ValueError(value)


def over(top, under):
    a = top[3]
    return tuple(top[i] * a + under[i] * (1 - a) for i in range(3)) + (1.0,)


def luminance(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(v) for v in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class ContrastTest(unittest.TestCase):
    def check(self, theme):
        failures = []
        for fg, bg, base in PAIRS:
            back = rgba(theme[bg])
            if back[3] < 1:
                back = over(back, rgba(theme[base]))
            r = ratio(rgba(theme[fg]), back)
            if r < 4.5:
                failures.append(f"--{fg} on --{bg}{'/' + base if base else ''}: {r:.2f}")
        self.assertEqual(failures, [])

    def test_dark_theme(self):
        self.check(tokens(":root"))

    def test_light_theme(self):
        dark = tokens(":root")
        self.check({**dark, **tokens(':root[data-theme="light"]')})


if __name__ == "__main__":
    unittest.main()
