"""The viewer's own files: where they live, the project registry, config.json,
and what happens when one of them can't be read."""

import json
import os
import unittest
from pathlib import Path
from unittest import mock

from helpers import TempProject, UserHome, serve


class ConfigHomeTest(unittest.TestCase):
    def home_for(self, env, platform="linux"):
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(serve.sys, "platform", platform), \
                mock.patch.object(Path, "home", return_value=Path("/h")):
            return serve.config_home()

    @unittest.skipIf(os.name == "nt", "POSIX layouts")
    def test_override(self):
        self.assertEqual(self.home_for({"CONDUCTOR_VIEW_HOME": "/x/y"}), Path("/x/y"))

    @unittest.skipIf(os.name == "nt", "POSIX layouts")
    def test_linux(self):
        self.assertEqual(self.home_for({}), Path("/h/.config/conductor-view"))
        self.assertEqual(self.home_for({"XDG_CONFIG_HOME": "/xdg"}), Path("/xdg/conductor-view"))

    @unittest.skipIf(os.name == "nt", "POSIX layouts")
    def test_macos(self):
        self.assertEqual(self.home_for({}, "darwin"), Path("/h/Library/Application Support/conductor-view"))

    @unittest.skipUnless(os.name == "nt", "Windows paths only exist on Windows")
    def test_windows(self):
        with mock.patch.dict(os.environ, {"APPDATA": r"C:\Users\u\AppData\Roaming"}, clear=True):
            self.assertEqual(serve.config_home(), Path(r"C:\Users\u\AppData\Roaming\conductor-view"))


class RegistryTest(UserHome):
    def project(self, name="proj", index=True):
        p = TempProject("run")
        p.setUp()
        self.addCleanup(p.doCleanups)
        root = p.root.parent / name if name else p.root
        if name:
            os.rename(p.root, root)
            self.addCleanup(lambda: root.exists() and __import__("shutil").rmtree(root, True))
        if index:
            (root / "conductor" / "index.md").write_text("# P\n")
        return root

    def test_add_list_forget(self):
        a = self.project("Alpha Repo")
        e = serve.add_project(a)
        self.assertEqual((e["id"], e["path"], e["added"]), ("alpha-repo", str(a.resolve()), True))
        self.assertFalse(serve.add_project(a)["added"])  # idempotent
        self.assertEqual([p["id"] for p in serve.registered_projects()], ["alpha-repo"])
        serve.forget_project("alpha-repo")
        self.assertEqual(serve.registered_projects(), [])
        self.assertTrue((a / "conductor" / "index.md").exists())  # files untouched

    def test_same_folder_name_gets_a_unique_id(self):
        a, b = self.project("same"), self.project(None)
        os.rename(b, b.parent / "x")
        b = b.parent / "x"
        (b / "same").mkdir()
        (b / "same" / "conductor").mkdir()
        (b / "same" / "conductor" / "index.md").write_text("# P\n")
        self.addCleanup(__import__("shutil").rmtree, b, True)
        self.assertEqual([serve.add_project(a)["id"], serve.add_project(b / "same")["id"]], ["same", "same-2"])

    def test_reserved_and_odd_names(self):
        self.assertEqual(serve._project_id(Path("/x/settings"), set()), "project-settings")
        self.assertEqual(serve._project_id(Path("/x/.hidden"), set()), "hidden")
        self.assertEqual(serve._project_id(Path("/x/ünï cødé!"), set()), "n-c-d")
        self.assertEqual(serve._project_id(Path("/x/!!!"), set()), "project")

    def test_only_conductor_projects_can_be_added(self):
        with self.assertRaisesRegex(ValueError, "conductor/index.md"):
            serve.add_project(self.project("bare", index=False))
        with self.assertRaisesRegex(ValueError, "full path"):
            serve.add_project("relative/path")

    def test_forget_unknown(self):
        with self.assertRaises(LookupError):
            serve.forget_project("nope")

    def test_file_is_written_atomically_as_json(self):
        serve.add_project(self.project("a"))
        data = json.loads((self.home / "projects.json").read_text())
        self.assertEqual(data["version"], 1)
        self.assertEqual(len(data["projects"]), 1)
        self.assertEqual([p.name for p in self.home.iterdir()], ["projects.json"])  # no temp files left


class ConfigTest(UserHome):
    def test_port(self):
        serve.set_config("port", 5000)
        self.assertEqual(serve.load_config(), {"port": 5000})
        serve.set_config("port", None)
        self.assertEqual(serve.load_config(), {})

    def test_bad_values(self):
        for bad in (80, 70000, "5000", True, 50.5):
            with self.assertRaises(ValueError, msg=bad):
                serve.set_config("port", bad)
        with self.assertRaises(ValueError):
            serve.set_config("colour", "red")


class UnreadableFileTest(UserHome):
    def break_file(self, name="projects.json", text='{"projects": [,]}'):
        (self.home / name).write_text(text)

    def test_unreadable_file_is_set_aside_not_overwritten(self):
        self.break_file()
        self.assertEqual(serve.registered_projects(), [])
        problem = serve.CONFIG_PROBLEMS["projects.json"]
        self.assertIn("line 1", problem["error"])
        saved = Path(problem["saved_as"])
        self.assertTrue(saved.name.startswith("projects.json.bad-"))
        self.assertEqual(saved.read_text(), '{"projects": [,]}')
        self.assertFalse((self.home / "projects.json").exists())

    def test_wrong_shape_counts_as_unreadable(self):
        self.break_file(text='{"projects": [{"path": 3}]}')
        serve.registered_projects()
        self.assertIn("projects.json", serve.CONFIG_PROBLEMS)
        self.break_file("config.json", "[1]")
        serve.load_config()
        self.assertIn("config.json", serve.CONFIG_PROBLEMS)

    def test_saving_after_a_bad_file_keeps_the_bad_copy(self):
        self.break_file()
        p = self.home / "work"
        (p / "conductor").mkdir(parents=True)
        (p / "conductor" / "index.md").write_text("# P\n")
        serve.add_project(p)
        bad = Path(serve.CONFIG_PROBLEMS["projects.json"]["saved_as"])
        self.assertEqual(bad.read_text(), '{"projects": [,]}')
        self.assertEqual(len(serve.registered_projects()), 1)

    def test_restore_after_fixing(self):
        self.break_file()
        serve.registered_projects()
        bad = Path(serve.CONFIG_PROBLEMS["projects.json"]["saved_as"])
        with self.assertRaisesRegex(ValueError, "still"):
            serve.restore_user_json("projects.json")
        bad.write_text('{"version": 1, "projects": [{"id": "x", "path": "/nowhere/x"}]}')
        (self.home / "projects.json").write_text('{"projects": []}')  # started again meanwhile
        serve.restore_user_json("projects.json")
        self.assertEqual([p["id"] for p in serve.registered_projects()], ["x"])
        self.assertNotIn("projects.json", serve.CONFIG_PROBLEMS)
        self.assertEqual(len(list(self.home.glob("projects.json.replaced-*"))), 1)  # nothing deleted

    def test_dismiss(self):
        self.break_file()
        serve.registered_projects()
        serve.dismiss_problem("projects.json")
        self.assertEqual(serve.CONFIG_PROBLEMS, {})
        with self.assertRaises(LookupError):
            serve.restore_user_json("projects.json")


if __name__ == "__main__":
    unittest.main()
