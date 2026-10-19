"""One viewer, many projects: the project list, per-project state and writes,
the summary cache, and the viewer's own config over HTTP."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import ServerTest, UserHome, serve

PLAN = "# P\n\n## Phase 1: A\n\n- [x] Task: one\n- [~] Task: two\n"


def make_project(base: Path, name: str, tracks=("t_1",)) -> Path:
    root = base / name
    for tid in tracks:
        d = root / "conductor" / "tracks" / tid
        d.mkdir(parents=True)
        (d / "plan.md").write_text(PLAN, encoding="utf-8")
    (root / "conductor").mkdir(parents=True, exist_ok=True)
    (root / "conductor" / "index.md").write_text("# P\n", encoding="utf-8")
    return root


class ProjectsApiTest(UserHome, ServerTest):
    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# A\n")
        self.write("conductor/tracks/t_1/plan.md", PLAN)
        self.base = Path(tempfile.mkdtemp(prefix="conductor-projects-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.b_root = make_project(self.base, "beta", ("t_1", "b_only"))
        serve.add_project(self.b_root)

    def projects(self):
        status, body = self.request("GET", "/api/projects")
        self.assertEqual(status, 200)
        return body

    def test_lists_the_active_project_and_registered_ones(self):
        home = self.projects()
        ids = [(p["id"], p["active"], p["registered"]) for p in home["projects"]]
        self.assertEqual(ids, [(serve._project_id(self.root, set()), True, False), ("beta", False, True)])
        beta = home["projects"][1]
        self.assertEqual([t["id"] for t in beta["tracks"]], ["b_only", "t_1"])
        self.assertEqual(beta["tracks"][0]["group"], "now")
        self.assertIn("safety", beta["tracks"][0]["git"])
        self.assertEqual(home["port"]["value"], self.port)
        self.assertEqual(home["problems"], [])

    def test_state_is_per_project(self):
        status, state = self.request("GET", "/api/state?project=beta")
        self.assertEqual((status, state["project_id"]), (200, "beta"))
        self.assertEqual([t["id"] for t in state["tracks"]], ["b_only", "t_1"])
        _, active = self.request("GET", "/api/state")
        self.assertEqual([t["id"] for t in active["tracks"]], ["t_1"])

    def test_unknown_or_path_like_project_ids_are_refused(self):
        for pid in ("nope", "..", "../beta", str(self.b_root), "%2e%2e"):
            status, _ = self.request("GET", f"/api/state?project={pid}")
            self.assertEqual(status, 404, pid)
            status, _ = self.request("POST", "/api/feedback", {"project": pid, "track": "t_1", "text": "x"})
            self.assertEqual(status, 404, pid)

    def test_feedback_goes_to_the_named_project_only(self):
        status, _ = self.request("POST", "/api/feedback", {"project": "beta", "track": "t_1", "text": "for beta"})
        self.assertEqual(status, 201)
        self.assertIn("for beta", (self.b_root / "conductor/tracks/t_1/feedback.md").read_text())
        self.assertFalse((self.root / "conductor/tracks/t_1/feedback.md").exists())
        status, _ = self.request("POST", "/api/feedback", {"project": "beta", "track": "nope_1", "text": "x"})
        self.assertEqual(status, 404)

    def test_add_and_forget(self):
        g = make_project(self.base, "gamma")
        status, body = self.request("POST", "/api/projects", {"action": "add", "path": str(g)})
        self.assertEqual((status, body["id"]), (200, "gamma"))
        self.assertIn("gamma", [p["id"] for p in self.projects()["projects"]])
        status, _ = self.request("POST", "/api/projects", {"action": "add", "path": str(self.base)})
        self.assertEqual(status, 400)
        status, _ = self.request("POST", "/api/projects", {"action": "forget", "id": "gamma"})
        self.assertEqual(status, 200)
        self.assertTrue((g / "conductor/index.md").exists())
        self.assertEqual(self.request("POST", "/api/projects", {"action": "explode"})[0], 400)

    def test_missing_project_is_listed_not_dropped(self):
        shutil.rmtree(self.b_root)
        beta = self.projects()["projects"][1]
        self.assertEqual((beta["id"], beta["missing"], beta["tracks"]), ("beta", True, []))
        self.assertEqual(self.request("GET", "/api/state?project=beta")[0], 404)

    def test_summaries_are_cached_until_a_project_changes(self):
        self.projects()
        with mock.patch.object(serve, "load_tracks", wraps=serve.load_tracks) as spy:
            self.projects()
            self.assertEqual(spy.call_count, 0)
            (self.b_root / "conductor/tracks/t_1/plan.md").write_text(PLAN + "- [ ] Task: three\n")
            self.projects()
            self.assertEqual(spy.call_count, 1)  # only beta was re-read

    def test_home_version_changes_with_any_project(self):
        v1 = self.request("GET", "/api/home-version")[1]["version"]
        self.assertEqual(v1, self.request("GET", "/api/home-version")[1]["version"])
        (self.b_root / "conductor/tracks/t_1/spec.md").write_text("# S\n")
        self.assertNotEqual(v1, self.request("GET", "/api/home-version")[1]["version"])

    def test_git_detail(self):
        status, d = self.request("GET", "/api/git?project=beta&track=t_1")
        self.assertEqual(status, 200)
        self.assertIn(d["safety"], ("nogit", "uncommitted"))
        self.assertEqual(self.request("GET", "/api/git?project=beta&track=zzz")[0], 404)

    def test_port_config_and_problems(self):
        self.assertEqual(self.request("POST", "/api/config", {"key": "port", "value": 5123})[0], 200)
        self.assertEqual(self.projects()["port"]["saved"], 5123)
        self.assertEqual(self.request("POST", "/api/config", {"key": "port", "value": 1})[0], 400)
        (self.home / "config.json").write_text("{oops")
        problems = self.projects()["problems"]
        self.assertEqual([p["name"] for p in problems], ["config.json"])
        self.assertEqual(self.request("POST", "/api/config/restore", {"file": "config.json"})[0], 400)
        Path(problems[0]["saved_as"]).write_text('{"port": 5124}')
        self.assertEqual(self.request("POST", "/api/config/restore", {"file": "config.json"})[0], 200)
        home = self.projects()
        self.assertEqual((home["problems"], home["port"]["saved"]), ([], 5124))


if __name__ == "__main__":
    unittest.main()
