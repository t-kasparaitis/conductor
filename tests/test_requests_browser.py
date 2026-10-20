"""Archive, restore and delete from the home page: the confirm dialog with its
git check, the typed confirmation, the waiting state and Withdraw."""

import os
import shutil
import subprocess
import unittest

from browser import Browser, find_browser
from helpers import ServerTest, UserHome, serve
from test_gitinfo import ENV


@unittest.skipUnless(find_browser(), "test browser not installed")
class RequestsBrowserTest(UserHome, ServerTest):
    @classmethod
    def setUpClass(cls):
        cls.b = Browser(width=1300, height=900)

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# P\n")
        self.write("conductor/tracks/live_1/spec.md", "# Live One\n")
        self.write("conductor/archive/old_1/spec.md", "# Old One\n")
        self.pid = serve._project_id(self.root, set())

    def open(self, hash_="#/", ready="document.querySelector('.trow[data-row]')"):
        self.b.goto("about:blank")
        self.b.goto(f"http://127.0.0.1:{self.port}/{hash_}", ready=ready)

    def js(self, expr):
        return self.b.js(expr)

    def type_confirm(self, text):
        self.js(f"(() => {{ const i = document.querySelector('#req-confirm'); i.value = '{text}'; i.dispatchEvent(new Event('input', {{bubbles: true}})); }})()")

    def feedback(self, rel):
        return serve.parse_feedback(self.read(rel))

    def test_archive_from_the_home_page_then_withdraw(self):
        self.open()
        self.b.click("[data-request=archive][data-track=live_1]")
        self.b.wait("document.querySelector('.gitcheck')")
        self.assertIn("Not a git repo", self.js("document.querySelector('.dlg-git').textContent"))
        self.js("document.querySelector('#req-note').value = 'shipped'")
        self.b.click("#req-form [type=submit]")
        self.b.wait("document.querySelector('.chip.req')")
        self.assertIn("Archive requested", self.js("document.querySelector('.trow .chip.req').textContent"))
        self.assertFalse(self.js("!!document.querySelector('[data-request=archive][data-track=live_1]')"))
        [item] = self.feedback("conductor/tracks/live_1/feedback.md")
        self.assertEqual((item["kind"], item["status"]), ("archive", "open"))
        self.assertIn("Note from the user: shipped", item["body"])
        self.b.click("[data-withdraw]")
        self.b.wait("!document.querySelector('.chip.req')")
        self.assertEqual(self.feedback("conductor/tracks/live_1/feedback.md")[0]["status"], "resolved")

    def test_delete_needs_the_id_typed(self):
        self.open("#/?status=archived")
        self.b.click("[data-request=delete][data-track=old_1]")
        self.b.wait("document.querySelector('#req-confirm')")
        self.b.wait("document.querySelector('.gitcheck')")
        submit = "document.querySelector('#req-form [type=submit]')"
        self.assertTrue(self.js(f"{submit}.disabled"))
        self.assertEqual(self.js(f"{submit}.textContent"), "Delete anyway")  # no git: nothing protects it
        self.type_confirm("old_")
        self.assertTrue(self.js(f"{submit}.disabled"))
        self.type_confirm("old_1")
        self.assertFalse(self.js(f"{submit}.disabled"))
        self.b.click("#req-form [type=submit]")
        self.b.wait("document.querySelector('.chip.req')")
        self.assertEqual(self.feedback("conductor/archive/old_1/feedback.md")[0]["kind"], "delete")
        self.assertTrue((self.root / "conductor/archive/old_1").is_dir())

    def test_restore_from_an_archived_track_page(self):
        self.open(f"#/{self.pid}/old_1/spec", ready="document.querySelector('.archived-banner')")
        self.b.click(".archived-banner [data-request=restore]")
        self.b.wait("document.querySelector('#req-form')")
        self.b.click("#req-form [type=submit]")
        self.b.wait("document.querySelector('.req-banner')")
        self.assertIn("Restore requested", self.js("document.querySelector('.req-banner').textContent"))

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_git_check_names_what_would_be_lost(self):
        bare = self.root.parent / (self.root.name + "-remote.git")
        self.addCleanup(shutil.rmtree, bare, True)
        run = lambda *a, cwd=self.root: subprocess.run(["git", *a], cwd=cwd, env=ENV, check=True, capture_output=True)
        run("init", "-q", "-b", "main")
        run("add", "-A")
        run("commit", "-q", "-m", "init")
        run("init", "-q", "--bare", str(bare), cwd=self.root.parent)
        run("remote", "add", "origin", str(bare))
        run("push", "-q", "origin", "main")
        self.write("conductor/tracks/live_1/plan.md", "# new, uncommitted\n")
        self.open("#/?status=open,archived")  # the archived track too
        self.b.click("[data-request=delete][data-track=live_1]")
        self.b.wait("document.querySelector('.gitcheck')")
        report = self.js("document.querySelector('.gitcheck').textContent")
        self.assertIn("1 uncommitted file would be lost", report)
        self.assertIn("conductor/tracks/live_1/plan.md", report)
        self.assertEqual(self.js("document.querySelector('#req-form [type=submit]').textContent"), "Delete anyway")
        self.js("document.querySelector('#dlg').close()")
        self.b.click("[data-request=delete][data-track=old_1]")
        self.b.wait("document.querySelector('.gitcheck') && document.querySelector('#req-form').dataset.track === 'old_1'")
        self.b.wait("document.querySelector('.gitcheck').textContent.includes('Safe')")
        self.assertEqual(self.js("document.querySelector('#req-form [type=submit]').textContent"), "Delete")


if __name__ == "__main__":
    unittest.main()
