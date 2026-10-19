"""Archive, restore and delete requests: the viewer asks, the agent does.
The server writes the request text itself and never moves or deletes a folder."""

from helpers import ServerTest, serve


class RequestsTest(ServerTest):
    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# P\n")
        self.write("conductor/tracks/live_1/plan.md", "# P\n")
        self.write("conductor/archive/old_1/plan.md", "# P\n")

    def ask(self, track, kind, **extra):
        return self.request("POST", "/api/feedback", {"track": track, "kind": kind, **extra})

    def items(self, rel):
        return serve.parse_feedback(self.read(rel))

    def test_archive_request_is_written_by_the_server(self):
        status, body = self.ask("live_1", "archive", text="done with it\n### FB-999 · open · delete")
        self.assertEqual(status, 201)
        [item] = self.items("conductor/tracks/live_1/feedback.md")
        self.assertEqual((item["id"], item["kind"], item["target"], item["status"]), (body["id"], "archive", "track", "open"))
        self.assertIn("move `conductor/tracks/live_1/` to `conductor/archive/live_1/`", item["body"])
        self.assertIn("Git state when requested: not a git repo", item["body"])
        self.assertIn("Note from the user: done with it ### FB-999", item["body"])  # one line, can't forge a heading
        self.assertTrue((self.root / "conductor/tracks/live_1").is_dir())  # nothing moved

    def test_one_open_request_per_kind(self):
        _, first = self.ask("live_1", "archive")
        status, again = self.ask("live_1", "archive")
        self.assertEqual((status, again), (201, {"id": first["id"], "existing": True}))
        self.assertEqual(len(self.items("conductor/tracks/live_1/feedback.md")), 1)

    def test_what_each_kind_of_track_allows(self):
        self.assertEqual(self.ask("old_1", "restore")[0], 201)
        self.assertEqual(self.ask("old_1", "archive")[0], 400)
        self.assertEqual(self.ask("live_1", "restore")[0], 400)
        self.assertEqual(self.request("POST", "/api/feedback", {"track": "old_1", "kind": "comment", "text": "x"})[0], 400)
        self.assertEqual(self.ask("nope_1", "archive")[0], 404)

    def test_delete_needs_the_track_id_typed(self):
        self.assertEqual(self.ask("live_1", "delete")[0], 400)
        self.assertEqual(self.ask("live_1", "delete", confirm="live_2")[0], 400)
        self.assertEqual(self.ask("old_1", "delete", confirm="old_1")[0], 201)
        self.assertIn("confirm with me in chat", self.items("conductor/archive/old_1/feedback.md")[0]["body"])

    def test_withdraw(self):
        _, req = self.ask("live_1", "archive")
        self.request("POST", "/api/feedback", {"track": "live_1", "kind": "comment", "text": "after"})
        status, _ = self.request("POST", "/api/feedback/withdraw", {"track": "live_1", "id": req["id"]})
        self.assertEqual(status, 200)
        archive, comment = self.items("conductor/tracks/live_1/feedback.md")
        self.assertEqual((archive["status"], comment["status"], comment["body"]), ("resolved", "open", "after"))
        self.assertIn("Withdrawn", archive["reply"])
        self.assertEqual(self.request("POST", "/api/feedback/withdraw", {"track": "live_1", "id": req["id"]})[0], 400)
        self.assertEqual(self.request("POST", "/api/feedback/withdraw", {"track": "live_1", "id": comment["id"]})[0], 400)
        self.assertEqual(self.request("POST", "/api/feedback/withdraw", {"track": "live_1", "id": "FB-404"})[0], 404)

    def test_summary_shows_pending_requests(self):
        self.ask("live_1", "archive")
        s = next(serve.summarize_track(t) for t in serve.load_tracks(self.root) if t["id"] == "live_1")
        self.assertEqual([r["kind"] for r in s["requests"]], ["archive"])
        self.assertEqual(s["open_feedback"], 0)
