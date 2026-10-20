"""Pinned tracks for the sidebar: new and open tracks are pinned automatically,
done and archived ones drop off, and pins.json keeps only choices made by hand."""

import json
import unittest

from helpers import ServerTest, UserHome, serve

OPEN = "# P\n\n## Phase 1: A\n\n- [x] Task: one\n- [ ] Task: two\n"
NOW = "# P\n\n## Phase 1: A\n\n- [x] Task: one\n- [~] Task: two\n"
DONE = "# P\n\n## Phase 1: A\n\n- [x] Task: one\n"


class PinRuleTest(unittest.TestCase):
    def test_automatic_rule_and_hand_choices(self):
        none = {"pinned": [], "unpinned": []}
        for group, want in (("now", True), ("open", True), ("done", False), ("archived", False)):
            self.assertEqual(serve.pin_state(none, "p", {"id": "t", "group": group}), {"pinned": want, "pin": "auto"})
        self.assertEqual(serve.pin_state({"pinned": ["p/t"], "unpinned": []}, "p", {"id": "t", "group": "done"}),
                         {"pinned": True, "pin": "pinned"})
        self.assertEqual(serve.pin_state({"pinned": [], "unpinned": ["p/t"]}, "p", {"id": "t", "group": "now"}),
                         {"pinned": False, "pin": "unpinned"})
        # Same track id in another project is a different track.
        self.assertEqual(serve.pin_state({"pinned": ["q/t"], "unpinned": []}, "p", {"id": "t", "group": "done"})["pin"], "auto")


class PinsApiTest(UserHome, ServerTest):
    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# A\n")
        self.write("conductor/tracks/now_1/plan.md", NOW)
        self.write("conductor/tracks/open_1/plan.md", OPEN)
        self.write("conductor/tracks/done_1/plan.md", DONE)
        self.write("conductor/tracks/done_1/metadata.json", '{"status": "done"}')
        self.write("conductor/archive/old_1/plan.md", DONE)
        self.pid = serve._project_id(self.root, set())

    def pins(self):
        _, home = self.request("GET", "/api/projects")
        return {t["id"]: (t["pinned"], t["pin"]) for t in home["projects"][0]["tracks"]}

    def pin(self, tid, pinned):
        return self.request("POST", "/api/pins", {"project": self.pid, "track": tid, "pinned": pinned})

    def test_defaults(self):
        self.assertEqual(self.pins(), {"now_1": (True, "auto"), "open_1": (True, "auto"),
                                       "done_1": (False, "auto"), "old_1": (False, "auto")})

    def test_pin_unpin_and_back_to_automatic(self):
        _, before = self.request("GET", "/api/home-version")
        self.assertEqual(self.pin("done_1", True), (200, {"key": f"{self.pid}/done_1", "pin": "pinned"}))
        self.assertEqual(self.pin("now_1", False)[0], 200)
        p = self.pins()
        self.assertEqual((p["done_1"], p["now_1"]), ((True, "pinned"), (False, "unpinned")))
        _, after = self.request("GET", "/api/home-version")
        self.assertNotEqual(before, after)  # other tabs pick the change up
        saved = json.loads((serve.config_home() / "pins.json").read_text())
        self.assertEqual((saved["pinned"], saved["unpinned"]), ([f"{self.pid}/done_1"], [f"{self.pid}/now_1"]))
        self.pin("now_1", True)  # a choice replaces the opposite one
        saved = json.loads((serve.config_home() / "pins.json").read_text())
        self.assertEqual((saved["pinned"], saved["unpinned"]), ([f"{self.pid}/done_1", f"{self.pid}/now_1"], []))
        self.pin("done_1", None)
        self.pin("now_1", None)
        self.assertEqual(self.pins()["done_1"], (False, "auto"))
        saved = json.loads((serve.config_home() / "pins.json").read_text())
        self.assertEqual((saved["pinned"], saved["unpinned"]), ([], []))

    def test_bad_input(self):
        for body in ({"project": "../x", "track": "t", "pinned": True}, {"project": self.pid, "track": "", "pinned": True},
                     {"project": self.pid, "track": "a/b", "pinned": True}, {"project": self.pid, "track": "t", "pinned": "yes"},
                     {"project": self.pid, "track": "t", "pinned": 1}):
            self.assertEqual(self.request("POST", "/api/pins", body)[0], 400, body)

    def test_unreadable_pins_file_is_set_aside(self):
        home = serve.config_home()
        home.mkdir(parents=True, exist_ok=True)
        (home / "pins.json").write_text('{"pinned": "oops"}', encoding="utf-8")
        self.assertEqual(self.pins()["now_1"], (True, "auto"))
        _, home_body = self.request("GET", "/api/projects")
        self.assertEqual([p["name"] for p in home_body["problems"]], ["pins.json"])
        self.assertTrue(list(home.glob("pins.json.bad-*")))


if __name__ == "__main__":
    unittest.main()
