"""summarize_track: the small per-track record the home page shows."""

import unittest

from helpers import TempProject, serve

PLAN = """# Plan

## Phase 1: Setup (diagram: map)

- [x] Task: Did it abc1234
- [x] Task: Also this

## Phase 2: Build

- [x] Task: Started
- [ ] Task: Waiting
    - [~] A sub-task in progress
- [ ] Task: Later
"""

FEEDBACK = """# Feedback

### FB-001 · resolved · approve
- **Target:** spec
- **When:** 2026-10-19 10:00

### FB-002 · resolved · approve
- **Target:** plan
- **When:** 2026-10-19 10:01

### FB-003 · open · revise
- **Target:** plan
- **When:** 2026-10-19 10:02

Change it.

### FB-004 · open · comment
- **Target:** plan › Phase 2: Build
- **When:** 2026-10-19 10:03

Hm.

### FB-005 · open · archive
- **Target:** track
- **When:** 2026-10-19 10:04
"""


class SummaryTest(TempProject):
    def setUp(self):
        super().setUp()
        self.write("conductor/tracks.md", "- [~] **Track: Registry words**\n*Link: [x](./tracks/demo_1/index.md)*\n")
        self.write("conductor/tracks/demo_1/plan.md", PLAN)
        self.write("conductor/tracks/demo_1/spec.md", "intro\n\n# Spec Title\n")
        self.write("conductor/tracks/demo_1/feedback.md", FEEDBACK)
        self.write("conductor/tracks/demo_1/metadata.json", '{"type": "bug", "created_at": "2026-10-19T00:00:00Z"}')

    def summary(self, tid="demo_1"):
        return next(serve.summarize_track(t) for t in serve.load_tracks(self.root) if t["id"] == tid)

    def test_fields(self):
        s = self.summary()
        self.assertEqual((s["title"], s["description"], s["type"], s["created"]),
                         ("Spec Title", "Registry words", "bug", "2026-10-19"))
        self.assertEqual((s["done"], s["total"]), (3, 5))
        self.assertEqual([p["title"] for p in s["phases"]], ["Setup", "Build"])
        self.assertEqual(s["phases"][1]["tasks"], ["done", "pending", "pending"])

    def test_a_sub_task_in_progress_makes_the_track_current(self):
        s = self.summary()
        self.assertEqual(s["group"], "now")
        self.assertEqual(s["current"], {"phase": 1, "text": "Waiting"})

    def test_feedback_counts_requests_and_decisions(self):
        s = self.summary()
        self.assertEqual(s["open_feedback"], 2)  # the revise and the comment, not the archive request
        self.assertEqual(s["requests"], [{"id": "FB-005", "kind": "archive"}])
        self.assertEqual(s["spec"], {"id": "FB-001", "kind": "approve", "status": "resolved"})
        self.assertEqual(s["plan"], {"id": "FB-003", "kind": "revise", "status": "open"})

    def test_groups(self):
        self.write("conductor/tracks/demo_1/plan.md", "## Phase 1: A\n- [ ] Task: x\n")
        self.assertEqual(self.summary()["group"], "open")
        self.write("conductor/tracks.md", "- [x] **Track: Registry words**\n*Link: [x](./tracks/demo_1/index.md)*\n")
        self.assertEqual(self.summary()["group"], "done")
        self.write("conductor/archive/old_1/metadata.json", '{"status": "completed"}')
        self.assertEqual(self.summary("old_1")["group"], "archived")

    def test_completed_metadata_counts_as_done(self):
        self.write("conductor/tracks/bare_2/metadata.json", '{"status": "completed", "description": "From metadata"}')
        s = self.summary("bare_2")
        self.assertEqual((s["group"], s["title"], s["status"]), ("done", "From metadata", "completed"))

    def test_empty_track(self):
        self.write("conductor/tracks/empty_3/.keep", "")
        s = self.summary("empty_3")
        self.assertEqual((s["title"], s["group"], s["phases"], s["spec"], s["current"]), ("empty_3", "open", [], None, None))


if __name__ == "__main__":
    unittest.main()
