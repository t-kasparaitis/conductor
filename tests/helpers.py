"""Shared test helpers. Every test works in a fresh temporary project and never
touches this repo's own conductor/ directory."""

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
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
        self.root = Path(tempfile.mkdtemp(prefix="conductor-test-"))
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
