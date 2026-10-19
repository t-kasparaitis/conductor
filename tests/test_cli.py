"""serve.py as a command: reusing a running viewer, finding a free port, and
the single-file --export snapshot."""

import socket
import subprocess
import sys
import unittest

from browser import Browser, find_browser
from helpers import SERVE_PY, ServerTest, TempProject, serve


def run(*args, timeout=20):
    return subprocess.run([sys.executable, str(SERVE_PY), *args], capture_output=True, text=True, encoding="utf-8",
                          timeout=timeout)


def start(*args):
    """Start serve.py and return (process, first output line)."""
    proc = subprocess.Popen([sys.executable, str(SERVE_PY), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    return proc, proc.stdout.readline()


def stop(proc):
    proc.terminate()
    proc.wait(timeout=10)
    proc.stdout.close()


class PortTest(ServerTest):
    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# P\n")

    def test_existing_viewer_is_recognised_only_for_the_same_project(self):
        self.assertTrue(serve.existing_viewer(self.port, self.root))
        other = TempProject("run")
        other.setUp()
        self.addCleanup(other.doCleanups)
        self.assertFalse(serve.existing_viewer(self.port, other.root))

    def test_nothing_listening_is_not_a_viewer(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            free = s.getsockname()[1]
        self.assertFalse(serve.existing_viewer(free, self.root))

    def test_second_start_for_the_same_project_reuses_the_first(self):
        result = run("--root", str(self.root), "--port", str(self.port))
        self.assertEqual(result.returncode, 0)
        self.assertIn(f"already running for this project: http://127.0.0.1:{self.port}/", result.stdout)

    def test_busy_port_moves_to_the_next_free_one(self):
        # self.port is taken by this test's server, which serves a different root.
        other = TempProject("run")
        other.setUp()
        self.addCleanup(other.doCleanups)
        proc, line = start("--root", str(other.root), "--port", str(self.port))
        try:
            self.assertIn(f"port {self.port} is busy", line)
            line2 = proc.stdout.readline()
            self.assertRegex(line2, r"serving .* at http://127\.0\.0\.1:\d+/")
            self.assertNotIn(f":{self.port}/", line2)
        finally:
            stop(proc)

    def test_missing_conductor_folder_is_a_clear_error(self):
        other = TempProject("run")
        other.setUp()
        self.addCleanup(other.doCleanups)
        (other.root / "conductor").rmdir()
        result = run("--root", str(other.root), "--port", "0")
        self.assertEqual(result.returncode, 2)
        self.assertIn("no conductor/ directory", result.stderr)


EVIL_PLAN = "# P\n\n## Phase 1: A\n\n- [ ] Task: </script><script>window.pwned=1</script> and <b>bold</b>\n"


class ExportTest(TempProject):
    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# P\n")
        self.write("conductor/tracks/demo_1/plan.md", EVIL_PLAN)
        self.write("conductor/tracks/demo_1/spec.md", "# Demo Spec Title\n\n## Overview\n\nHello.\n")
        self.out = self.root / "snapshot.html"
        result = run("--root", str(self.root), "--export", str(self.out))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.html = self.out.read_text(encoding="utf-8")

    def test_snapshot_is_one_self_contained_file(self):
        self.assertIn("window.CONDUCTOR_SNAPSHOT=", self.html)
        for ref in ('href="style.css"', 'src="app.js"', 'src="map.js"'):
            self.assertNotIn(ref, self.html)

    def test_plan_text_cannot_close_the_script_tag(self):
        self.assertEqual(self.html.count("</script>"), 2)  # the two script tags we wrote

    @unittest.skipUnless(find_browser(), "test browser not installed")
    def test_snapshot_renders_read_only_in_a_browser(self):
        b = Browser()
        try:
            b.goto(self.out.as_uri() + "#/demo_1/plan", ready="document.querySelector('.overview')")
            self.assertIn("Demo Spec Title", b.js("document.querySelector('h1').textContent"))
            self.assertIsNone(b.js("window.pwned"))
            self.assertEqual(b.js("document.querySelectorAll('.comment-btn, .review-actions').length"), 0)
            self.assertTrue(b.js("!!document.querySelector('.snapshot-banner')"))
        finally:
            b.close()


if __name__ == "__main__":
    unittest.main()
