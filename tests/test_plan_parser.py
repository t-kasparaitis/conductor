"""parse_plan and parse_registry: the grammar in references/file-contract.md."""

import unittest

from helpers import serve

PLAN = """# Implementation Plan: Demo

> Planned under: something.
Second preamble line.

## Phase 1: Setup (diagram: arch) [checkpoint: abcdef1]

- [x] Task: Did it 1234567
    - [x] Sub done 89abcde
    - [~] Sub doing
    Notes about the task.
- [~] Task: Doing `code` now
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

Phase note after tasks.

## Phase 2: Next

* [X] Task: Star bullet and capital X `fedcba9`
- [ ] Task: Two commits 5cc6deb 258f462
- [ ] Task: Bracketed [0123456]
- [ ] Task: Ends with a short hex word: cafe
- [ ] Task: Try it with the user, iterate on feedback, sign-off (Refer to workflow.md)

## Phase 3: Empty
"""


class PlanParserTest(unittest.TestCase):
    def setUp(self):
        self.plan = serve.parse_plan(PLAN)
        self.p1, self.p2, self.p3 = self.plan["phases"]

    def test_title_and_preamble(self):
        self.assertEqual(self.plan["title"], "Implementation Plan: Demo")
        self.assertEqual(self.plan["preamble"], ["> Planned under: something.", "Second preamble line."])

    def test_phase_titles_and_checkpoint(self):
        self.assertEqual(self.p1["title"], "Phase 1: Setup (diagram: arch)")
        self.assertEqual(self.p1["checkpoint"], "abcdef1")
        self.assertIsNone(self.p2["checkpoint"])

    def test_tasks_states_and_shas(self):
        t = self.p1["tasks"]
        self.assertEqual([x["status"] for x in t], ["done", "in_progress", "pending"])
        self.assertEqual(t[0]["text"], "Did it")
        self.assertEqual(t[0]["sha"], "1234567")
        self.assertEqual(t[1]["text"], "Doing `code` now")
        self.assertIsNone(t[1]["sha"])

    def test_subtasks_and_notes(self):
        task = self.p1["tasks"][0]
        self.assertEqual([(s["text"], s["status"], s["sha"]) for s in task["subtasks"]],
                         [("Sub done", "done", "89abcde"), ("Sub doing", "in_progress", None)])
        self.assertEqual(task["notes"], ["Notes about the task."])

    def test_text_after_the_last_task_attaches_to_that_task(self):
        self.assertEqual(self.p1["tasks"][2]["notes"], ["Phase note after tasks."])

    def test_star_bullets_capital_x_and_backticked_sha(self):
        t = self.p2["tasks"][0]
        self.assertEqual((t["text"], t["status"], t["sha"]), ("Star bullet and capital X", "done", "fedcba9"))

    def test_several_trailing_shas(self):
        t = self.p2["tasks"][1]
        self.assertEqual(t["text"], "Two commits")
        self.assertEqual(t["shas"], ["5cc6deb", "258f462"])
        self.assertEqual(t["sha"], "258f462")

    def test_bracketed_sha(self):
        self.assertEqual(self.p2["tasks"][2]["sha"], "0123456")

    def test_short_hex_words_are_not_shas(self):
        t = self.p2["tasks"][3]
        self.assertEqual(t["text"], "Ends with a short hex word: cafe")
        self.assertIsNone(t["sha"])

    def test_checkpoint_tasks(self):
        self.assertEqual([x["is_checkpoint"] for x in self.p1["tasks"]], [False, False, True])
        self.assertTrue(self.p2["tasks"][4]["is_checkpoint"])

    def test_phase_status_and_counts(self):
        self.assertEqual((self.p1["status"], self.p1["done"], self.p1["total"]), ("in_progress", 1, 3))
        self.assertEqual((self.p2["status"], self.p2["done"], self.p2["total"]), ("in_progress", 1, 5))
        self.assertEqual((self.p3["status"], self.p3["total"]), ("pending", 0))

    def test_empty_and_heading_free_plans(self):
        self.assertEqual(serve.parse_plan("")["phases"], [])
        loose = serve.parse_plan("- [ ] Task: no phase yet\n")
        self.assertEqual(loose["phases"], [])
        self.assertEqual(loose["preamble"], ["- [ ] Task: no phase yet"])

    def test_windows_line_endings(self):
        crlf = serve.parse_plan(PLAN.replace("\n", "\r\n"))
        self.assertEqual(crlf, self.plan)


class RegistryParserTest(unittest.TestCase):
    def test_entries_status_and_track_id(self):
        text = """# Tracks

---

- [~] **Track: First one**
*Link: [./tracks/first_1/index.md](./tracks/first_1/index.md)*

---

- [x] **Second, no prefix**
*Link: [./tracks/second_2/index.md](./tracks/second_2/index.md)*

## [ ] Track: legacy heading format
*Link: [./tracks/legacy_3/index.md](./tracks/legacy_3/index.md)*
"""
        entries = serve.parse_registry(text)
        self.assertEqual([(e["status"], e["description"], e["track_id"]) for e in entries],
                         [("in_progress", "First one", "first_1"), ("done", "Second, no prefix", "second_2"),
                          ("pending", "legacy heading format", "legacy_3")])

    def test_entry_without_link(self):
        self.assertEqual(serve.parse_registry("- [ ] **Track: Orphan**\n")[0]["track_id"], None)


if __name__ == "__main__":
    unittest.main()
