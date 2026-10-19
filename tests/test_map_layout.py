"""WorldMap.layout, the world-map auto-layout, as a pure function in a real browser."""

import json
import random
import unittest

from browser import Browser, find_browser
from helpers import REPO

INDEX = (REPO / "skills" / "conductor-view" / "assets" / "viewer" / "index.html").as_uri()
NODE_W, NODE_H = 190, 56


def node(i, region=None, **kw):
    return {"id": f"n{i}", "label": f"N{i}", **({"region": region} if region else {}), **kw}


@unittest.skipUnless(find_browser(), "test browser not installed")
class LayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = Browser()
        cls.b.goto(INDEX, ready="window.WorldMap")

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def layout(self, diagram):
        return self.b.js(f"""(() => {{ const L = window.WorldMap.layout({json.dumps(diagram)});
          return {{ manual: L.manual, nodes: Object.fromEntries(L.nodes.map(n => [n.id, [n.x, n.y, n.region || null]])) }}; }})()""")

    def assert_no_overlap(self, nodes):
        boxes = list(nodes.values())
        for i, (x1, y1, _) in enumerate(boxes):
            for x2, y2, _ in boxes[i + 1:]:
                overlap = x1 < x2 + NODE_W and x2 < x1 + NODE_W and y1 < y2 + NODE_H and y2 < y1 + NODE_H
                self.assertFalse(overlap, (x1, y1, x2, y2))

    def test_regions_are_left_to_right_columns(self):
        d = {"regions": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
             "nodes": [node(0, "c"), node(1, "a"), node(2, "b"), node(3, "a"), node(4, "c"), node(5)],
             "edges": [{"from": "n1", "to": "n3"}]}
        n = self.layout(d)["nodes"]
        right = lambda ids: max(n[i][0] for i in ids)
        left = lambda ids: min(n[i][0] for i in ids)
        self.assertLess(right(["n1", "n3"]), left(["n2"]))
        self.assertLess(right(["n2"]), left(["n0", "n4"]))
        self.assertLess(right(["n0", "n4"]), left(["n5"]))  # nodes without a region come last

    def test_edges_point_right_within_a_region(self):
        d = {"nodes": [node(i) for i in range(6)],
             "edges": [{"from": "n0", "to": "n1"}, {"from": "n1", "to": "n2"}, {"from": "n0", "to": "n3"},
                       {"from": "n3", "to": "n2"}, {"from": "n2", "to": "n4"}, {"from": "n5", "to": "n4"}]}
        n = self.layout(d)["nodes"]
        for e in d["edges"]:
            self.assertLess(n[e["from"]][0], n[e["to"]][0], e)

    def test_longest_path_ranks(self):
        # n0 -> n1 -> n2 and n0 -> n2: n2 sits two columns right of n0, not one.
        d = {"nodes": [node(0), node(1), node(2)],
             "edges": [{"from": "n0", "to": "n1"}, {"from": "n1", "to": "n2"}, {"from": "n0", "to": "n2"}]}
        n = self.layout(d)["nodes"]
        self.assertEqual(len({n["n0"][0], n["n1"][0], n["n2"][0]}), 3)

    def test_cycles_and_self_loops_still_lay_out(self):
        d = {"nodes": [node(i) for i in range(4)],
             "edges": [{"from": "n0", "to": "n1"}, {"from": "n1", "to": "n2"}, {"from": "n2", "to": "n0"},
                       {"from": "n3", "to": "n3"}]}
        n = self.layout(d)["nodes"]
        self.assertEqual(len(n), 4)
        for x, y, _ in n.values():
            self.assertTrue(isinstance(x, (int, float)) and isinstance(y, (int, float)))
        self.assert_no_overlap(n)

    def test_no_overlaps_on_random_graphs(self):
        rng = random.Random(7)
        for trial in range(15):
            count = rng.randint(1, 25)
            regions = [{"id": f"r{i}"} for i in range(rng.randint(0, 3))]
            nodes = [node(i, rng.choice(regions)["id"] if regions and rng.random() < 0.8 else None) for i in range(count)]
            edges = [{"from": f"n{rng.randrange(count)}", "to": f"n{rng.randrange(count)}"} for _ in range(rng.randint(0, count * 2))]
            n = self.layout({"regions": regions, "nodes": nodes, "edges": edges})["nodes"]
            self.assertEqual(len(n), count, trial)
            self.assert_no_overlap(n)

    def test_manual_coordinates_are_kept_only_when_every_node_has_them(self):
        d = {"nodes": [node(0, x=10, y=20), node(1, x=-300, y=500)]}
        out = self.layout(d)
        self.assertTrue(out["manual"])
        self.assertEqual(out["nodes"]["n0"][:2], [10, 20])
        self.assertEqual(out["nodes"]["n1"][:2], [-300, 500])
        partial = self.layout({"nodes": [node(0, x=10, y=20), node(1)]})
        self.assertFalse(partial["manual"])

    def test_same_input_same_layout(self):
        d = {"nodes": [node(i) for i in range(8)], "edges": [{"from": f"n{i}", "to": f"n{(i * 3) % 8}"} for i in range(8)]}
        self.assertEqual(self.layout(d), self.layout(d))

    def test_empty_diagram(self):
        self.assertEqual(self.layout({})["nodes"], {})


if __name__ == "__main__":
    unittest.main()
