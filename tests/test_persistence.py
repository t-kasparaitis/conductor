"""Feedback writes: atomic, LF everywhere, no duplicate ids under load, and no
lost edits when an agent changes the file at the same moment."""

import os
import threading
from pathlib import Path
from unittest import mock

from helpers import TempProject, serve


class PersistenceTest(TempProject):
    def setUp(self):
        super().setUp()
        (self.root / "conductor/tracks/demo_1").mkdir(parents=True)
        self.fb = self.root / "conductor/tracks/demo_1/feedback.md"

    def post(self, text="hi", **kw):
        payload = {"track": "demo_1", "kind": "comment", "target": "plan", "text": text}
        payload.update(kw)
        return serve.append_feedback(self.root, payload)

    def items(self):
        return serve.parse_feedback(self.fb.read_text(encoding="utf-8"))

    def test_concurrent_posts_get_distinct_ids_and_none_are_lost(self):
        errors = []

        def worker(n):
            try:
                self.post(f"comment {n}")
            except Exception as e:  # pragma: no cover - reported below
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(n,)) for n in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        items = self.items()
        self.assertEqual(sorted(i["id"] for i in items), [f"FB-{n:03d}" for n in range(1, 11)])
        self.assertEqual(sorted(i["body"] for i in items), sorted(f"comment {n}" for n in range(10)))

    def test_lf_only_even_when_the_file_had_crlf(self):
        self.post("first")
        self.fb.write_bytes(self.fb.read_bytes().replace(b"\n", b"\r\n"))
        self.post("line one\r\nline two")
        data = self.fb.read_bytes()
        self.assertNotIn(b"\r", data)
        self.assertEqual(len(self.items()), 2)

    def test_no_temp_files_left_behind(self):
        for _ in range(3):
            self.post()
        self.assertEqual([p.name for p in self.fb.parent.iterdir()], ["feedback.md"])

    def test_a_failed_write_leaves_the_old_file_intact(self):
        self.post("keep me")
        before = self.fb.read_bytes()
        with mock.patch.object(serve.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.post("never written")
        self.assertEqual(self.fb.read_bytes(), before)
        self.assertEqual([p.name for p in self.fb.parent.iterdir()], ["feedback.md"])

    def test_an_agent_edit_made_while_writing_is_not_lost(self):
        self.post("please fix")
        real_read = serve._read
        calls = {"n": 0}

        def read_then_agent_edits(path):
            text = real_read(path)
            if Path(path).resolve() == self.fb.resolve() and calls["n"] == 0:
                calls["n"] += 1
                # The agent resolves FB-001 right after the server read the file.
                agent = text.replace("### FB-001 · open ·", "### FB-001 · resolved ·") + "\n> **Agent:** fixed\n"
                self.fb.write_text(agent, encoding="utf-8")
            return text

        with mock.patch.object(serve, "_read", side_effect=read_then_agent_edits):
            self.post("another")
        items = self.items()
        self.assertEqual([(i["id"], i["status"]) for i in items], [("FB-001", "resolved"), ("FB-002", "open")])
        self.assertEqual(items[0]["reply"], "**Agent:** fixed")

    def test_gives_up_rather_than_overwrite_a_file_that_keeps_changing(self):
        real_read = serve._read

        def always_changing(path):
            text = real_read(path)
            if Path(path).resolve() == self.fb.resolve():
                self.fb.write_text((text or "") + "x", encoding="utf-8")
            return text

        self.post("seed")
        with mock.patch.object(serve, "_read", side_effect=always_changing):
            with self.assertRaises(RuntimeError):
                self.post("blocked")
        self.assertNotIn("blocked", self.fb.read_text(encoding="utf-8"))
