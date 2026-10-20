"""The Feedback tab as a conversation: threads, Needs you, and replying."""

import unittest

from browser import Browser, find_browser
from helpers import ServerTest, UserHome, serve

FEEDBACK = """# Feedback: t_1

### FB-001 · resolved · comment
- **Target:** plan
- **When:** 2026-10-20 09:00

First thing.

> **Agent:** Done.

### FB-002 · waiting · comment
- **Target:** spec
- **When:** 2026-10-20 10:00

Can it do X?

> **Agent · 2026-10-20 10:05:** Do you mean X on Windows too?

### FB-003 · open · comment
- **Target:** plan
- **When:** 2026-10-20 11:00

Newest.
"""


@unittest.skipUnless(find_browser(), "test browser not installed")
class FeedbackLogTest(UserHome, ServerTest):
    @classmethod
    def setUpClass(cls):
        cls.b = Browser(width=1300, height=900)

    @classmethod
    def tearDownClass(cls):
        cls.b.close()

    def setUp(self):
        super().setUp()
        self.write("conductor/index.md", "# P\n")
        self.write("conductor/tracks/t_1/plan.md", "# P\n\n## Phase 1: A\n\n- [ ] Task: one\n")
        self.write("conductor/tracks/t_1/feedback.md", FEEDBACK)
        self.pid = serve._project_id(self.root, set())

    def open(self, hash_):
        self.b.goto("about:blank")
        self.b.goto(f"http://127.0.0.1:{self.port}/{hash_}", ready="document.querySelector('main').children.length > 1")

    def js(self, expr):
        return self.b.js(expr)

    def test_threads_with_needs_you_on_top(self):
        self.open(f"#/{self.pid}/t_1/feedback")
        self.b.wait("document.querySelector('.fb-item')")
        self.assertEqual(self.js("[...document.querySelectorAll('.fb-item')].map(a => a.id)"), ["fb-FB-002", "fb-FB-003", "fb-FB-001"])
        thread = self.js("[...document.querySelectorAll('#fb-FB-002 .fb-msg')].map(m => [m.className.split(' ')[1], m.querySelector('.md').textContent.trim()])")
        self.assertEqual(thread, [["you", "Can it do X?"], ["agent", "Do you mean X on Windows too?"]])
        self.assertIn("Needs your answer", self.js("document.querySelector('#fb-FB-002 .fb-head').textContent"))
        self.assertEqual(self.js("document.querySelector('[data-tab=feedback] .count').textContent"), "1 needs you")
        self.b.click('[data-fbfilter="waiting"]')
        self.assertEqual(self.js("[...document.querySelectorAll('.fb-item')].map(a => a.id)"), ["fb-FB-002"])

    def test_reply_from_the_viewer(self):
        self.open(f"#/{self.pid}/t_1/feedback")
        self.b.wait("document.querySelector('[data-reply=FB-002]')")
        self.b.click("[data-reply=FB-002]")
        self.b.wait("document.querySelector('#composer').open")
        self.assertEqual(self.js("document.querySelector('#composer-kind').textContent"), "Reply to FB-002")
        self.js("document.querySelector('#composer-text').value = 'Yes, Windows too.'")
        self.b.click("#composer-send")
        self.b.wait("document.querySelectorAll('#fb-FB-002 .fb-msg').length === 3")
        self.assertIn("With the agent", self.js("document.querySelector('#fb-FB-002 .fb-head').textContent"))
        [item] = [i for i in serve.parse_feedback(self.read("conductor/tracks/t_1/feedback.md")) if i["id"] == "FB-002"]
        self.assertEqual((item["status"], item["thread"][-1]["who"], item["thread"][-1]["text"]), ("open", "you", "Yes, Windows too."))

    def test_needs_you_shows_on_home_and_sidebar(self):
        self.open("#/")
        self.b.wait("document.querySelector('.needs-you')")
        self.assertIn("1 needs you", self.js("document.querySelector('.tracks-table .needs-you').textContent"))
        self.assertIn("1 needs you", self.js("document.querySelector('#sidebar [data-track=t_1]').textContent"))

    def test_archived_threads_are_read_only(self):
        self.write("conductor/archive/old_1/feedback.md", FEEDBACK)
        self.write("conductor/archive/old_1/spec.md", "# Old\n")
        self.open(f"#/{self.pid}/old_1/feedback")
        self.b.wait("document.querySelector('.fb-item')")
        self.assertEqual(self.js("document.querySelectorAll('[data-reply]').length"), 0)


if __name__ == "__main__":
    unittest.main()
