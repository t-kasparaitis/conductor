"""Find projects: scan folders for conductor/index.md, skipping what can't hold one."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers import ServerTest, UserHome, serve


class ScanTest(UserHome, ServerTest):
    def setUp(self):
        super().setUp()
        self.base = Path(tempfile.mkdtemp(prefix="conductor-scan-"))
        self.addCleanup(shutil.rmtree, self.base, True)
        for rel in ("code/alpha", "code/work/beta", "deep/a/b/c/d/e/gamma", ".hidden/delta",
                    "code/node_modules/epsilon", "code/alpha/sub/nested"):
            (self.base / rel / "conductor").mkdir(parents=True)
            (self.base / rel / "conductor" / "index.md").write_text("# P\n")
        (self.base / "code/not_init/conductor").mkdir(parents=True)  # no index.md

    def names(self, result):
        return sorted(f["name"] for f in result["found"])

    def test_finds_projects_and_skips_the_rest(self):
        r = serve.scan_projects([str(self.base)])
        self.assertEqual(self.names(r), ["alpha", "beta"])  # gamma is too deep; nested is inside alpha
        self.assertFalse(r["truncated"])

    def test_depth(self):
        self.assertEqual(self.names(serve.scan_projects([str(self.base)], depth=8)), ["alpha", "beta", "gamma"])
        self.assertEqual(self.names(serve.scan_projects([str(self.base)], depth=1)), [])

    def test_marks_registered_projects(self):
        serve.add_project(self.base / "code/alpha")
        found = {f["name"]: f["registered"] for f in serve.scan_projects([str(self.base)])["found"]}
        self.assertEqual(found, {"alpha": True, "beta": False})

    @unittest.skipIf(os.name == "nt", "symlinks need extra rights on Windows")
    def test_symlink_loops_are_not_followed(self):
        os.symlink(self.base, self.base / "code" / "loop")
        self.assertEqual(self.names(serve.scan_projects([str(self.base)], depth=8)), ["alpha", "beta", "gamma"])

    def test_time_limit_truncates(self):
        r = serve.scan_projects([str(self.base)], time_limit=0)
        self.assertTrue(r["truncated"])

    def test_bad_roots(self):
        for roots in (["relative"], [str(self.base / "nope")]):
            with self.assertRaises(ValueError):
                serve.scan_projects(roots)

    def test_over_http(self):
        status, r = self.request("POST", "/api/scan", {"roots": [str(self.base)], "depth": 3})
        self.assertEqual((status, self.names(r)), (200, ["alpha", "beta"]))
        self.assertEqual(self.request("POST", "/api/scan", {"roots": "x"})[0], 400)


if __name__ == "__main__":
    unittest.main()
