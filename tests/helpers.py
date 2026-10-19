"""Shared test helpers. Every test works in a fresh temporary project and never
touches this repo's own conductor/ directory."""

import atexit
import http.client
import importlib.util
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The viewer keeps a per-user project list and config. Point it at a throwaway
# folder for the whole test run (child processes inherit it), never the real one.
os.environ["CONDUCTOR_VIEW_HOME"] = tempfile.mkdtemp(prefix="conductor-view-home-")
atexit.register(shutil.rmtree, os.environ["CONDUCTOR_VIEW_HOME"], True)
SERVE_PY = REPO / "skills" / "conductor-view" / "scripts" / "serve.py"


def load_serve():
    spec = importlib.util.spec_from_file_location("conductor_view_serve", SERVE_PY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


serve = load_serve()


class TempProject(unittest.TestCase):
    """A throwaway project root with an empty conductor/ directory."""

    def setUp(self):
        # CONDUCTOR_TEST_TMP: somewhere a sandboxed browser can read (a snap Firefox can't see /tmp).
        base = os.environ.get("CONDUCTOR_TEST_TMP")
        if base:
            os.makedirs(base, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix="conductor-test-", dir=base))
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "conductor").mkdir()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def write_settings(self, obj):
        return self.write("conductor/settings.json", json.dumps(obj) if not isinstance(obj, str) else obj)

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")


class UserHome(unittest.TestCase):
    """A fresh, empty viewer config folder for one test."""

    def setUp(self):
        super().setUp()
        self.home = Path(tempfile.mkdtemp(prefix="conductor-view-home-"))
        self.addCleanup(shutil.rmtree, self.home, True)
        old = os.environ["CONDUCTOR_VIEW_HOME"]
        os.environ["CONDUCTOR_VIEW_HOME"] = str(self.home)
        self.addCleanup(os.environ.__setitem__, "CONDUCTOR_VIEW_HOME", old)
        serve.CONFIG_PROBLEMS.clear()
        self.addCleanup(serve.CONFIG_PROBLEMS.clear)


class ServerTest(TempProject):
    def setUp(self):
        super().setUp()
        handler = type("TestHandler", (serve.Handler,), {"root": self.root})
        self.httpd = serve.Server(("127.0.0.1", 0), handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(self.httpd.shutdown)

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(conn.close)
        data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode()
        hdrs = {"Content-Type": "application/json"}
        hdrs.update(headers or {})
        conn.request(method, path, body=data, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        try:
            return resp.status, json.loads(raw)
        except ValueError:
            return resp.status, raw

    def post_setting(self, key, value, **kw):
        return self.request("POST", "/api/settings", {"key": key, "value": value}, **kw)

    def settings_file(self):
        return json.loads(self.read("conductor/settings.json"))
