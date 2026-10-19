"""load_state and friends: a malformed file shows up as a visible error on that
item and never takes down the whole page."""

import json

from helpers import TempProject, serve


class LoadersTest(TempProject):
    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# Project Context\n")

    def track(self, tid="t_1", **files):
        for name, text in files.items():
            self.write(f"conductor/tracks/{tid}/{name.replace('__', '/').replace('_dot_', '.')}", text)
        return next(t for t in serve.load_state(self.root)["tracks"] if t["id"] == tid)

    def test_complete_track(self):
        t = self.track(metadata_dot_json='{"type": "feature"}', spec_dot_md="# S\n", plan_dot_md="# P\n## Phase 1: A\n- [ ] Task: x\n")
        self.assertEqual(t["metadata"], {"type": "feature"})
        self.assertIsNone(t["metadata_error"])
        self.assertEqual(len(t["plan"]["phases"]), 1)

    def test_missing_files_are_empty_not_errors(self):
        self.write("conductor/tracks/bare_1/.keep", "")
        t = next(x for x in serve.load_state(self.root)["tracks"] if x["id"] == "bare_1")
        self.assertEqual((t["metadata"], t["spec"], t["feedback"], t["diagrams"]), ({}, "", [], []))

    def test_broken_metadata_is_reported(self):
        t = self.track(metadata_dot_json='{"type": ')
        self.assertEqual(t["metadata"], {})
        self.assertTrue(t["metadata_error"])

    def test_non_object_metadata_is_reported(self):
        t = self.track(metadata_dot_json='["not", "an", "object"]')
        self.assertEqual(t["metadata"], {})
        self.assertIn("object", t["metadata_error"])

    def test_broken_diagram_becomes_an_error_card(self):
        t = self.track(diagrams__bad_dot_json="{nope", diagrams__good_dot_json='{"title": "G", "nodes": []}')
        kinds = {d["slug"]: d["type"] for d in t["diagrams"]}
        self.assertEqual(kinds, {"bad": "error", "good": "map"})

    def test_diagram_that_is_not_an_object_does_not_crash(self):
        t = self.track(diagrams__list_dot_json="[1, 2, 3]")
        self.assertEqual(t["diagrams"][0]["type"], "error")

    def test_diagram_with_malformed_nodes_or_edges_is_an_error(self):
        cases = {
            "nodes_not_list": {"nodes": {"a": 1}},
            "node_not_object": {"nodes": ["a"]},
            "node_without_id": {"nodes": [{"label": "x"}]},
            "edges_not_list": {"nodes": [{"id": "a"}], "edges": "a->b"},
            "edge_to_nowhere": {"nodes": [{"id": "a"}], "edges": [{"from": "a", "to": "zzz"}]},
            "tour_to_nowhere": {"nodes": [{"id": "a"}], "tour": ["zzz"]},
            "duplicate_ids": {"nodes": [{"id": "a"}, {"id": "a"}]},
            "duplicate_after_str": {"nodes": [{"id": 1}, {"id": "1"}]},
        }
        files = {f"diagrams__{k}_dot_json": json.dumps(v) for k, v in cases.items()}
        t = self.track(**files)
        for d in t["diagrams"]:
            self.assertEqual(d["type"], "error", d["slug"])
            self.assertIn(d["slug"], d["error"])

    def test_svg_and_unknown_files(self):
        t = self.track(diagrams__pic_dot_svg="<svg/>", diagrams__notes_dot_txt="ignored")
        self.assertEqual([(d["slug"], d["type"]) for d in t["diagrams"]], [("pic", "svg")])

    def test_non_utf8_text_is_shown_not_dropped(self):
        path = self.root / "conductor/tracks/t_1/spec.md"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"# Spec\n\ncaf\xe9\n")
        t = next(x for x in serve.load_state(self.root)["tracks"] if x["id"] == "t_1")
        self.assertIn("caf�", t["spec"])

    def test_registry_links_cannot_escape_the_tracks_folder(self):
        self.write("conductor/tracks.md", "- [ ] **Track: Sneaky**\n*Link: [x](../index.md)*\n"
                                          "- [ ] **Track: Dot**\n*Link: [x](./index.md)*\n")
        self.write("conductor/tracks/real_1/plan.md", "")
        ids = [t["id"] for t in serve.load_state(self.root)["tracks"]]
        self.assertEqual(ids, ["real_1"])

    def test_registry_order_then_unregistered_folders(self):
        self.write("conductor/tracks.md", "- [ ] **Track: B**\n*Link: [x](./tracks/b_2/index.md)*\n"
                                          "- [ ] **Track: Gone**\n*Link: [x](./tracks/gone_9/index.md)*\n")
        for tid in ("a_1", "b_2", "c_3"):
            self.write(f"conductor/tracks/{tid}/plan.md", "")
        self.assertEqual([t["id"] for t in serve.load_state(self.root)["tracks"]], ["b_2", "a_1", "c_3"])

    def test_version_changes_when_a_file_changes(self):
        self.write("conductor/tracks/t_1/plan.md", "a")
        v1 = serve.state_version(self.root)
        self.write("conductor/tracks/t_1/plan.md", "ab")
        self.assertNotEqual(v1, serve.state_version(self.root))
