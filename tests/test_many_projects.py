"""Fifty projects of twenty tracks, all git repos: the home page stays fast and
a refresh only re-reads the projects that changed."""

import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from helpers import ServerTest, UserHome, serve
from test_gitinfo import ENV

PLAN = "# P\n\n## Phase 1: A\n\n" + "".join(f"- [{'x' if i < 3 else ' '}] Task: task {i}\n" for i in range(8))


@unittest.skipUnless(shutil.which("git"), "git not installed")
class ManyProjectsTest(UserHome, ServerTest):
    PROJECTS, TRACKS = 50, 20

    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# A\n")
        self.base = Path(tempfile.mkdtemp(prefix="conductor-many-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.roots = []
        for n in range(self.PROJECTS):
            root = self.base / f"p{n:02d}"
            for t in range(self.TRACKS):
                d = root / "conductor" / "tracks" / f"t{t:02d}_1"
                d.mkdir(parents=True)
                (d / "plan.md").write_text(PLAN)
                (d / "spec.md").write_text(f"# Track {t}\n")
            (root / "conductor" / "index.md").write_text("# P\n")
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=root, env=ENV, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, env=ENV, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, env=ENV, check=True)
            serve.add_project(root)
            self.roots.append(root)

    def load_home(self):
        start = time.perf_counter()
        status, body = self.request("GET", "/api/projects")
        self.assertEqual(status, 200)
        return body, time.perf_counter() - start

    def test_warm_home_page_is_fast_and_reads_only_changed_projects(self):
        body, cold = self.load_home()
        self.assertEqual(len(body["projects"]), self.PROJECTS + 1)
        self.assertEqual(sum(len(p["tracks"]) for p in body["projects"]), self.PROJECTS * self.TRACKS)
        self.assertLess(cold, 20, "first load")  # generous: CI machines vary
        _, warm = self.load_home()
        self.assertLess(warm, 1.0, f"cached home page took {warm:.2f}s")
        # Agents edit two projects at once.
        (self.roots[3] / "conductor/tracks/t00_1/plan.md").write_text(PLAN + "- [~] Task: new\n")
        (self.roots[41] / "conductor/tracks/t05_1/feedback.md").write_text("### FB-001 · open · comment\n\nhi\n")
        with mock.patch.object(serve, "load_tracks", wraps=serve.load_tracks) as spy:
            body, _ = self.load_home()
        self.assertEqual(sorted(Path(c.args[0]).name for c in spy.call_args_list), ["p03", "p41"])
        p03 = next(p for p in body["projects"] if p["id"] == "p03")
        self.assertEqual(p03["tracks"][0]["group"], "now")
        self.assertEqual(p03["tracks"][0]["git"]["safety"], "uncommitted")

    def test_home_version_poll_is_cheap(self):
        self.load_home()
        start = time.perf_counter()
        self.request("GET", "/api/home-version")
        self.assertLess(time.perf_counter() - start, 1.0)


if __name__ == "__main__":
    unittest.main()
