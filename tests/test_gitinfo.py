"""gitinfo: each track's last activity and safety badge, read from throwaway
repos (one with a bare 'remote' next to it). Skipped without git."""

import os
import shutil
import subprocess
import unittest

from helpers import TempProject, serve  # noqa: F401  (serve puts gitinfo on sys.path)
import gitinfo

ENV = {**os.environ, "GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "T",
       "GIT_COMMITTER_EMAIL": "t@example.com", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


@unittest.skipUnless(shutil.which("git"), "git not installed")
class GitInfoTest(TempProject):
    def setUp(self):
        super().setUp()
        self.g("init", "-q", "-b", "main")
        self.write("conductor/tracks/t_1/plan.md", "# P\n")
        self.write("conductor/archive/old_1/plan.md", "# Old\n")
        self.commit("init", date="2026-01-02T03:04:05Z")

    def g(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd or self.root, env=ENV, check=True,
                              capture_output=True, text=True).stdout

    def commit(self, msg, date=None):
        env = {**ENV, **({"GIT_COMMITTER_DATE": date, "GIT_AUTHOR_DATE": date} if date else {})}
        subprocess.run(["git", "add", "-A"], cwd=self.root, env=env, check=True)
        subprocess.run(["git", "commit", "-q", "-m", msg], cwd=self.root, env=env, check=True)

    def add_remote(self):
        bare = self.root.parent / (self.root.name + "-remote.git")
        self.addCleanup(shutil.rmtree, bare, True)
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], env=ENV, check=True)
        self.g("remote", "add", "origin", str(bare))
        self.g("push", "-q", "origin", "main")

    def info(self, *tracks):
        return gitinfo.project_git(self.root, list(tracks or [("t_1", False), ("old_1", True)]))

    def test_no_remote_means_committed(self):
        r = self.info()
        self.assertEqual((r["git"], r["branch"], r["main"], r["remote"]), (True, "main", "main", False))
        self.assertEqual(r["tracks"]["t_1"]["safety"], "committed")

    def test_last_activity_is_the_newest_commit_touching_the_folder(self):
        r = self.info()
        self.assertEqual(r["tracks"]["t_1"]["last_activity"], 1767323045)
        self.assertEqual(r["tracks"]["old_1"]["last_activity"], 1767323045)

    def test_uncommitted_files_win(self):
        self.add_remote()
        self.write("conductor/tracks/t_1/spec.md", "new\n")
        self.write("conductor/tracks/t_1/plan.md", "changed\n")
        t = self.info()["tracks"]["t_1"]
        self.assertEqual((t["safety"], t["uncommitted"]), ("uncommitted", 2))
        self.assertGreater(t["last_activity"], 1767323045)  # the edit is newer than the commit
        self.assertEqual(self.info()["tracks"]["old_1"]["safety"], "pushed")

    def test_a_renamed_file_is_counted_once(self):
        self.g("mv", "conductor/tracks/t_1/plan.md", "conductor/tracks/t_1/plan2.md")
        self.assertEqual(self.info()["tracks"]["t_1"]["uncommitted"], 1)

    def test_pushed_unpushed_and_landed_branches(self):
        self.add_remote()
        self.assertEqual(self.info()["tracks"]["t_1"]["safety"], "pushed")
        self.g("switch", "-q", "-c", "t_2")
        self.write("conductor/tracks/t_2/plan.md", "# 2\n")
        self.commit("t2")
        t = self.info(("t_2", False))["tracks"]["t_2"]
        self.assertEqual((t["safety"], t["branch"], t["unpushed"]), ("unpushed", "t_2", 1))
        self.g("push", "-q", "origin", "t_2")
        self.assertEqual(self.info(("t_2", False))["tracks"]["t_2"]["safety"], "pushed")
        self.g("switch", "-q", "main")
        self.g("merge", "-q", "--no-ff", "-m", "land", "t_2")
        # Landed as soon as it's merged: the track's own commits are already on the remote.
        self.assertEqual(self.info(("t_2", False))["tracks"]["t_2"]["safety"], "landed")
        self.g("push", "-q", "origin", "main")
        self.assertEqual(self.info(("t_2", False))["tracks"]["t_2"]["safety"], "landed")

    def test_unpushed_commit_on_the_current_branch(self):
        self.add_remote()
        self.write("conductor/tracks/t_1/plan.md", "more\n")
        self.commit("more")
        t = self.info()["tracks"]["t_1"]
        self.assertEqual((t["safety"], t["unpushed"]), ("unpushed", 1))
        self.assertEqual(self.info()["tracks"]["old_1"]["safety"], "pushed")

    def test_detail_lists_files_and_commits(self):
        self.add_remote()
        self.write("conductor/tracks/t_1/plan.md", "more\n")
        self.commit("Add more to the plan")
        self.write("conductor/tracks/t_1/new.md", "x\n")
        d = gitinfo.track_detail(self.root, "t_1", False)
        self.assertEqual(d["uncommitted_files"], ["conductor/tracks/t_1/new.md"])
        self.assertEqual(len(d["unpushed_commits"]), 1)
        self.assertIn("Add more to the plan", d["unpushed_commits"][0])
        self.assertTrue(d["remote"])

    def test_project_in_a_subfolder_of_the_repo(self):
        sub = self.root / "pkg"
        (sub / "conductor/tracks/s_1").mkdir(parents=True)
        (sub / "conductor/tracks/s_1/plan.md").write_text("x\n")
        self.commit("sub", date="2026-02-01T00:00:00Z")
        (sub / "conductor/tracks/s_1/plan.md").write_text("y\n")
        t = gitinfo.project_git(sub, [("s_1", False)])["tracks"]["s_1"]
        self.assertEqual((t["safety"], t["uncommitted"]), ("uncommitted", 1))

    def test_version_changes_on_commit(self):
        info = gitinfo.repo_info(self.root)
        v1 = gitinfo.git_version(info)
        self.write("conductor/tracks/t_1/plan.md", "v2\n")
        self.commit("v2")
        self.assertNotEqual(v1, gitinfo.git_version(info))


class NoGitTest(TempProject):
    def test_not_a_repo(self):
        self.write("conductor/tracks/t_1/plan.md", "x")
        r = gitinfo.project_git(self.root, [("t_1", False)])
        self.assertFalse(r["git"])
        self.assertEqual(r["tracks"]["t_1"]["safety"], "nogit")
        self.assertIsNotNone(r["tracks"]["t_1"]["last_activity"])
        self.assertEqual(gitinfo.git_version(gitinfo.repo_info(self.root)), "nogit")


if __name__ == "__main__":
    unittest.main()
