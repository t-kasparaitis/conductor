"""POST /api/settings against a real server on a free port, in a throwaway project."""

import http.client
import json
import threading

from helpers import TempProject, serve


class ServerTest(TempProject):
    def setUp(self):
        super().setUp()
        handler = type("TestHandler", (serve.Handler,), {"root": self.root})
        self.httpd = serve.ThreadingHTTPServer(("127.0.0.1", 0), handler)
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


class SettingsApiTest(ServerTest):
    def test_valid_change_creates_the_file_with_version(self):
        status, body = self.post_setting("git.strategy", "trunk")
        self.assertEqual((status, body), (200, {"key": "git.strategy", "value": "trunk"}))
        self.assertEqual(self.settings_file(), {"version": 1, "git": {"strategy": "trunk"}})

    def test_change_keeps_other_values(self):
        self.write_settings({"version": 1, "git": {"strategy": "trunk", "notes": "off"}, "custom": {"x": 1}})
        self.assertEqual(self.post_setting("testing.verification", "track")[0], 200)
        self.assertEqual(self.settings_file(), {"version": 1, "git": {"strategy": "trunk", "notes": "off"},
                                                "custom": {"x": 1}, "testing": {"verification": "track"}})

    def test_written_file_uses_lf_line_endings(self):
        self.post_setting("git.push", "track")
        self.assertNotIn(b"\r\n", (self.root / "conductor" / "settings.json").read_bytes())

    def test_unknown_key_and_value_are_rejected(self):
        self.assertEqual(self.post_setting("git.rebase", "yes")[0], 400)
        self.assertEqual(self.post_setting("git.strategy", "gitflow")[0], 400)
        self.assertEqual(self.post_setting("git.strategy", ["trunk"])[0], 400)
        self.assertFalse((self.root / "conductor" / "settings.json").exists())

    def test_non_object_body_is_rejected(self):
        self.assertEqual(self.request("POST", "/api/settings", [1, 2])[0], 400)
        self.assertEqual(self.request("POST", "/api/settings", b"not json")[0], 400)

    def test_broken_file_is_never_overwritten(self):
        self.write_settings('{"git": {')
        status, body = self.post_setting("git.strategy", "trunk")
        self.assertEqual(status, 400)
        self.assertIn("fix it by hand", body["error"])
        self.assertEqual(self.read("conductor/settings.json"), '{"git": {')

    def test_cross_origin_post_is_rejected(self):
        status, _ = self.post_setting("git.strategy", "trunk", headers={"Origin": "http://evil.example"})
        self.assertEqual(status, 403)
        self.assertFalse((self.root / "conductor" / "settings.json").exists())

    def test_same_origin_post_is_accepted(self):
        for origin in (f"http://127.0.0.1:{self.port}", f"http://localhost:{self.port}"):
            host = origin.split("://")[1]
            status, _ = self.post_setting("git.push", "phase", headers={"Origin": origin, "Host": host})
            self.assertEqual(status, 200, origin)

    def test_new_value_shows_up_in_state(self):
        self.post_setting("git.notes", "off")
        status, state = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(state["settings"]["effective"]["git.notes"], {"value": "off", "source": "file"})


class DnsRebindingTest(ServerTest):
    """A site that points its own domain at 127.0.0.1 sends a matching Origin
    and Host. Only requests addressed to this machine by name are served."""

    def test_foreign_host_cannot_read_state(self):
        status, _ = self.request("GET", "/api/state", headers={"Host": f"evil.example:{self.port}"})
        self.assertEqual(status, 403)

    def test_foreign_host_cannot_write_even_with_matching_origin(self):
        host = f"evil.example:{self.port}"
        status, _ = self.post_setting("git.strategy", "trunk", headers={"Host": host, "Origin": f"http://{host}"})
        self.assertEqual(status, 403)
        self.assertFalse((self.root / "conductor" / "settings.json").exists())

    def test_local_names_are_served(self):
        for host in (f"127.0.0.1:{self.port}", f"localhost:{self.port}"):
            self.assertEqual(self.request("GET", "/api/version", headers={"Host": host})[0], 200, host)


if __name__ == "__main__":
    import unittest
    unittest.main()
