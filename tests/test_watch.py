"""serve.py --watch: one line per open feedback item and per settings change."""

import json
import queue
import subprocess
import sys
import threading
import time

from helpers import SERVE_PY, TempProject

ITEM = "\n### {id} · {status} · comment\n- **Target:** plan\n- **When:** now\n\n{body}\n"


class WatchTest(TempProject):
    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# P\n")
        self.fb = "conductor/tracks/demo_1/feedback.md"
        self.write(self.fb, "# Feedback\n" + ITEM.format(id="FB-001", status="open", body="already open")
                   + ITEM.format(id="FB-002", status="resolved", body="done before"))

    def start(self):
        self.proc = subprocess.Popen([sys.executable, str(SERVE_PY), "--root", str(self.root), "--watch"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(self._stop)
        self.lines = queue.Queue()
        threading.Thread(target=lambda: [self.lines.put(line.rstrip("\n")) for line in self.proc.stdout],
                         daemon=True).start()
        self.assertTrue(self.next_line().startswith("watching "))

    def _stop(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self.proc.stdout.close()
        self.proc.stderr.close()

    def next_line(self, timeout=5):
        return self.lines.get(timeout=timeout)

    def assert_quiet(self, seconds=1.5):
        time.sleep(seconds)
        self.assertTrue(self.lines.empty(), f"unexpected: {self.lines.queue}")

    def append(self, text):
        path = self.root / self.fb
        path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")

    def test_already_open_items_first_then_new_ones(self):
        self.start()
        self.assertEqual(self.next_line(), "feedback FB-001 · comment · track demo_1 · target plan · already open")
        self.assert_quiet()
        self.append(ITEM.format(id="FB-003", status="open", body="new one"))
        self.assertIn("FB-003", self.next_line())

    def test_resolved_items_and_repeats_are_not_reported(self):
        self.start()
        self.next_line()
        self.append(ITEM.format(id="FB-003", status="resolved", body="agent did it"))
        self.assert_quiet()

    def test_long_bodies_are_shortened_to_one_line(self):
        self.append(ITEM.format(id="FB-003", status="open", body="word " * 100 + "\nsecond line"))
        self.start()
        lines = {self.next_line() for _ in range(2)}
        long_line = next(line for line in lines if "FB-003" in line)
        self.assertTrue(long_line.endswith("..."))
        self.assertLess(len(long_line), 200)

    def test_settings_changes(self):
        self.start()
        self.next_line()
        self.write_settings({"version": 1, "git": {"strategy": "trunk"}})
        self.assertEqual(self.next_line(), "settings changed: git.strategy = trunk")

    def test_half_written_files_cause_no_false_events(self):
        self.write_settings({"version": 1, "git": {"strategy": "trunk"}})
        self.start()
        self.next_line()
        self.write_settings('{"version": 1, "git": {"strat')  # caught mid-save
        self.append("\n### FB-00")
        self.assert_quiet()
        self.write_settings({"version": 1, "git": {"strategy": "trunk", "push": "track"}})
        self.assertEqual(self.next_line(), "settings changed: git.push = track")
        self.assertIsNone(self.proc.poll(), "watch must keep running")
