"""local.js (the no-Python viewer) must read files exactly like serve.py.
The same fixtures go through both and the results are compared. Also checks
the from-disk page end to end with a simulated folder pick."""

import json
import unittest

from browser import Browser, find_browser
from helpers import REPO, TempProject, serve
from test_plan_parser import PLAN

INDEX = (REPO / "skills" / "conductor-view" / "assets" / "viewer" / "index.html").as_uri()

FEEDBACK = """# Feedback: demo_1

### FB-001 · open · comment
- **Target:** plan › Phase 1: Setup › Did it
- **When:** 2026-10-19 10:00

Body line
- **Target:** this is body text, not metadata

### FB-002 · resolved · approve
- **Target:** spec
- **When:** 2026-10-19 11:00

_(no message)_

> **Agent:** Thanks.
> Second reply line.
"""

REGISTRY = """# Tracks

- [~] **Track: Demo**
*Link: [./tracks/demo_1/index.md](./tracks/demo_1/index.md)*
- [x] **Track: Escape**
*Link: [x](../index.md)*
- [ ] **Track: Dot**
*Link: [x](./index.md)*
## [ ] Track: Legacy
*Link: [x](./tracks/legacy_2/index.md)*
- [ ] **No link**
"""

ODD_PLANS = [
    "",
    "no headings at all\n- [ ] Task: loose",
    "# Only a title",
    "## Phase 1: A\r\n- [ ] Task: crlf\r\n\t- [x] tab-indented sub 1234567\r\n",
    "## P\n- [x] Task: unicode ünïcødé – dash 89abcdef0\n    - [~] sub `abcdef1`\n",
    "# T\n## P1 [checkpoint: 1234567]\n### P2\n- [X] Task: capital\n* [ ] Task: star\n",
]


def errors_to_flags(value):
    """Error messages differ between Python and JavaScript; compare only whether there is one."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            out[k] = bool(v) if k in ("error", "metadata_error") else errors_to_flags(v)
        return out
    if isinstance(value, list):
        return [errors_to_flags(v) for v in value]
    return value


@unittest.skipUnless(find_browser(), "test browser not installed")
class ParityTest(TempProject):
    @classmethod
    def setUpClass(cls):
        cls.b = Browser()
        cls.b.goto(INDEX, ready="window.ConductorLocal")

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def js(self, fn, *args):
        return self.b.js(f"window.ConductorLocal.{fn}(...{json.dumps(list(args))})")

    def test_plans(self):
        for text in [PLAN] + ODD_PLANS:
            self.assertEqual(self.js("parsePlan", text), serve.parse_plan(text), text[:40])

    def test_registry(self):
        self.assertEqual(self.js("parseRegistry", REGISTRY), serve.parse_registry(REGISTRY))

    def test_feedback(self):
        for text in (FEEDBACK, FEEDBACK.replace("\n", "\r\n"), "", "### FB-1 · open · comment\n"):
            self.assertEqual(self.js("parseFeedback", text), serve.parse_feedback(text))

    def test_diagram_checks(self):
        cases = [[], "x", {}, {"nodes": [{"id": 1}], "edges": [{"from": 1, "to": "1"}]},
                 {"nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "b"}]}, {"nodes": "a"},
                 {"nodes": [{"id": "a"}], "tour": ["a", "b"]}, {"nodes": [], "regions": {}},
                 {"nodes": [{"id": "a"}, {"id": "a"}]}, {"nodes": [{"id": 1}, {"id": "1"}]}]
        for data in cases:
            self.assertEqual(self.js("diagramProblem", data) is None, serve._diagram_problem(data) is None, data)

    def test_whole_project_state(self):
        files = {
            "conductor/index.md": "# P\n",
            "conductor/tracks.md": REGISTRY,
            "conductor/tracks/demo_1/plan.md": PLAN,
            "conductor/tracks/demo_1/spec.md": "# Spec\n\n## Overview\n",
            "conductor/tracks/demo_1/feedback.md": FEEDBACK,
            "conductor/tracks/demo_1/metadata.json": '{"type": "feature", "status": "in_progress"}',
            "conductor/tracks/demo_1/diagrams/a.json": '{"title": "A", "nodes": [{"id": "x"}]}',
            "conductor/tracks/demo_1/diagrams/b.json": "{broken",
            "conductor/tracks/demo_1/diagrams/c.svg": "<svg/>",
            "conductor/tracks/legacy_2/plan.md": "",
            "conductor/tracks/legacy_2/metadata.json": "[1]",
            "conductor/tracks/zz_9/spec.md": "unregistered",
            "conductor/archive/old_1/plan.md": "## Phase 1: A\n- [x] Task: done abc1234\n",
            "conductor/archive/Old_2/metadata.json": '{"status": "archived"}',
            "conductor/archive/zz_9/spec.md": "same id as a live track",
        }
        for path, text in files.items():
            self.write(path, text)
        expected = serve.load_state(self.root)["tracks"]
        actual = self.js("buildState", files, "proj")["tracks"]
        self.assertEqual(errors_to_flags(actual), errors_to_flags(expected))
        summaries = self.b.js(f"window.ConductorLocal.buildState({json.dumps(files)}, 'p').tracks.map(window.ConductorLocal.summarizeTrack)")
        self.assertEqual(summaries, [serve.summarize_track(t) for t in expected])

    def test_summaries(self):
        from test_summary import FEEDBACK as SUMMARY_FEEDBACK, PLAN as SUMMARY_PLAN
        specs = ["", "intro\n\n# Title\n", "#\nnot a title\n# Real", "# CRLF title\r\n"]
        metas = ["{}", '{"status": "completed", "description": "d", "type": "chore"}', '{"status": "DONE"}']
        registries = ["", "- [x] **Track: Reg**\n*Link: [x](./tracks/t_1/index.md)*\n"]
        for spec in specs:
            for meta in metas:
                for reg in registries:
                    files = {"conductor/tracks.md": reg, "conductor/tracks/t_1/spec.md": spec,
                             "conductor/tracks/t_1/metadata.json": meta, "conductor/tracks/t_1/plan.md": SUMMARY_PLAN,
                             "conductor/tracks/t_1/feedback.md": SUMMARY_FEEDBACK,
                             "conductor/archive/a_1/spec.md": spec}
                    for path, text in files.items():
                        self.write(path, text)
                    expected = [serve.summarize_track(t) for t in serve.load_tracks(self.root)]
                    actual = self.b.js(f"window.ConductorLocal.buildState({json.dumps(files)}, 'p').tracks.map(window.ConductorLocal.summarizeTrack)")
                    self.assertEqual(actual, expected, (spec, meta, reg))


@unittest.skipUnless(find_browser(), "test browser not installed")
class FromDiskPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Browser()

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def test_pick_a_folder_then_copy_feedback(self):
        b = self.b
        b.goto(INDEX + "#/demo_1/plan", ready="document.querySelector('#pick-folder')")
        self.assertIn("from disk", b.js("document.querySelector('#live').textContent"))
        # Simulate picking the project folder: files with webkitRelativePath under "proj/".
        b.js("""(() => {
          const make = (path, text) => { const f = new File([text], path.split('/').pop());
            Object.defineProperty(f, 'webkitRelativePath', { value: path }); return f; };
          const dt = new DataTransfer();
          dt.items.add(make('proj/conductor/index.md', '# P'));
          dt.items.add(make('proj/conductor/tracks/demo_1/plan.md', '# Plan\\n\\n## Phase 1: A\\n\\n- [ ] Task: hello from disk'));
          dt.items.add(make('proj/conductor/tracks/demo_1/spec.md', '# Disk Spec'));
          dt.items.add(make('proj/node_modules/huge.js', 'ignored'));
          const input = document.querySelector('#pick-folder');
          input.files = dt.files;
          input.dispatchEvent(new Event('change', { bubbles: true }));
        })()""")
        b.wait("document.querySelector('.task')")
        self.assertIn("hello from disk", b.js("document.querySelector('.task').textContent"))
        self.assertEqual(b.js("document.querySelector('h1').textContent"), "Disk Spec")
        # Commenting copies a ready-to-paste feedback item instead of saving.
        b.js("""window.__copied = null;
          Object.defineProperty(navigator, 'clipboard', { value: { writeText: (t) => { window.__copied = t; return Promise.resolve(); } } });""")
        b.click(".task .comment-btn")
        b.js("document.querySelector('#composer-text').value = 'from the disk viewer'")
        self.assertEqual(b.js("document.querySelector('#composer-send').textContent"), "Copy")
        b.click("#composer-send")
        b.wait("window.__copied")
        copied = b.js("window.__copied")
        self.assertIn("conductor/tracks/demo_1/feedback.md", copied)
        self.assertIn("### FB-NEW · open · comment", copied)
        self.assertIn("from the disk viewer", copied)


if __name__ == "__main__":
    unittest.main()
