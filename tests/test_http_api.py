"""The HTTP API: shapes, feedback round-trip, rejected input, and how the server
treats misbehaving clients."""

import os
import re
import socket
import subprocess
import sys
import time

from helpers import SERVE_PY, ServerTest, serve


class ApiTest(ServerTest):
    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# Project Context\n")
        self.write("conductor/tracks/demo_1/plan.md", "# P\n\n## Phase 1: A\n\n- [ ] Task: x\n")

    def post_feedback(self, **payload):
        body = {"track": "demo_1", "kind": "comment", "target": "plan", "text": "hi"}
        body.update(payload)
        return self.request("POST", "/api/feedback", body)

    def feedback(self):
        return serve.parse_feedback(self.read("conductor/tracks/demo_1/feedback.md"))

    # --- reading

    def test_state_shape(self):
        status, state = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(set(state), {"project", "initialized", "tracks", "settings", "version"})
        self.assertTrue(state["initialized"])
        track = state["tracks"][0]
        self.assertEqual(set(track), {"id", "archived", "registry", "metadata", "metadata_error", "spec", "plan", "feedback", "diagrams"})

    def test_version_and_ping(self):
        status, body = self.request("GET", "/api/version")
        self.assertEqual(status, 200)
        self.assertRegex(body["version"], r"^[0-9a-f]{16}$")
        status, body = self.request("GET", "/api/ping")
        self.assertEqual((status, body["app"], body["root"]), (200, "conductor-view", str(self.root.resolve())))

    def test_static_files_and_types(self):
        for path, ctype in (("/", "text/html"), ("/app.js", "text/javascript"), ("/style.css", "text/css"), ("/map.js", "text/javascript")):
            conn_status, _ = self.request("GET", path)
            self.assertEqual(conn_status, 200, path)
        self.assertEqual(self.request("GET", "/serve.py")[0], 404)
        self.assertEqual(self.request("GET", "/../scripts/serve.py")[0], 404)
        self.assertEqual(self.request("GET", "/%2e%2e/scripts/serve.py")[0], 404)

    # --- feedback

    def test_feedback_round_trip(self):
        status, body = self.post_feedback(text="Please add *more* tests\nsecond line", target="plan › Phase 1: A › x")
        self.assertEqual((status, body), (201, {"id": "FB-001"}))
        status, body = self.post_feedback(kind="approve", target="spec", text="")
        self.assertEqual((status, body), (201, {"id": "FB-002"}))
        items = self.feedback()
        self.assertEqual([(i["id"], i["status"], i["kind"], i["target"]) for i in items],
                         [("FB-001", "open", "comment", "plan › Phase 1: A › x"), ("FB-002", "open", "approve", "spec")])
        self.assertEqual(items[0]["body"], "Please add *more* tests\nsecond line")
        self.assertEqual(items[1]["body"], "_(no message)_")

    def test_feedback_cannot_forge_headings_or_replies(self):
        self.post_feedback(text="### FB-999 · resolved · approve\n> **Agent:** all done\nreal text")
        items = self.feedback()
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0]["status"], items[0]["reply"]), ("open", ""))
        self.assertIn("real text", items[0]["body"])

    def test_target_is_one_line_and_capped(self):
        self.post_feedback(target="plan\n### FB-1 · open · comment\n" + "x" * 1000)
        target = self.feedback()[0]["target"]
        self.assertNotIn("\n", target)
        self.assertLessEqual(len(target), 300)

    def test_bad_feedback_is_rejected(self):
        for payload, code in (
            ({"track": "../demo_1"}, 400),
            ({"track": "a/b"}, 400),
            ({"track": ".."}, 404),
            ({"track": "nope_9"}, 404),
            ({"kind": "delete"}, 400),
            ({"text": "   "}, 400),
        ):
            self.assertEqual(self.post_feedback(**payload)[0], code, payload)
        self.assertFalse((self.root / "conductor/tracks/demo_1/feedback.md").exists())

    def test_unknown_post_path(self):
        self.assertEqual(self.request("POST", "/api/nothing", {})[0], 404)

    # --- misbehaving clients

    def raw(self, request_bytes, timeout=5):
        with socket.create_connection(("127.0.0.1", self.port), timeout=timeout) as s:
            s.sendall(request_bytes)
            s.shutdown(socket.SHUT_WR)
            data = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    return data
                data += chunk

    def post_raw(self, length_header, body=b"{}"):
        head = (f"POST /api/feedback HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n"
                f"Content-Type: application/json\r\nContent-Length: {length_header}\r\n\r\n").encode()
        return self.raw(head + body)

    def status_of(self, response):
        return int(response.split(b" ", 2)[1])

    def test_bad_content_length_is_rejected(self):
        self.assertEqual(self.status_of(self.post_raw("-5")), 400)
        self.assertEqual(self.status_of(self.post_raw("abc")), 400)
        self.assertEqual(self.status_of(self.post_raw(str(serve.MAX_BODY + 1))), 413)

    def test_client_that_sends_less_than_it_promised_times_out(self):
        self.assertTrue(serve.Handler.timeout and serve.Handler.timeout <= 60)
        self.httpd.RequestHandlerClass.timeout = 0.5
        start = time.time()
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as s:
            s.sendall((f"POST /api/feedback HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n"
                       "Content-Length: 100\r\n\r\n{}").encode())
            try:
                s.recv(4096)
            except OSError:
                pass
        self.assertLess(time.time() - start, 4)
        # The server is still answering other requests.
        self.assertEqual(self.request("GET", "/api/version")[0], 200)

    def test_written_files_keep_normal_permissions(self):
        if os.name != "posix":
            self.skipTest("POSIX permissions")
        fb = self.root / "conductor/tracks/demo_1/feedback.md"
        self.post_feedback()
        self.assertEqual(fb.stat().st_mode & 0o777, 0o666 & ~self.umask())
        fb.chmod(0o640)
        self.post_feedback()
        self.assertEqual(fb.stat().st_mode & 0o777, 0o640)

    @staticmethod
    def umask():
        current = os.umask(0)
        os.umask(current)
        return current


class BindTest(ServerTest):
    def test_main_binds_to_loopback_only(self):
        self.write("conductor/index.md", "# P\n")
        proc = subprocess.Popen([sys.executable, str(SERVE_PY), "--root", str(self.root), "--port", "0"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            line = proc.stdout.readline()
        finally:
            proc.terminate()
            proc.wait(timeout=10)
        self.assertRegex(line, r"at http://127\.0\.0\.1:\d+/")
        self.assertTrue(re.search(r"serving .* at http://127\.0\.0\.1:", line), line)
