#!/usr/bin/env python3
"""Conductor visual companion: a local, read-mostly web view of conductor/.

Standard library only. Run from the project root (the directory that contains
conductor/):

    python3 serve.py                 # serve on 127.0.0.1:4177
    python3 serve.py --port 0        # any free port
    python3 serve.py --open          # also open the browser
    python3 serve.py --export out.html   # single-file read-only snapshot
    python3 serve.py --watch         # print one line per new open feedback item

The browser can write exactly one kind of file: an appended item in
conductor/tracks/<id>/feedback.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import threading
import time
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gitinfo  # noqa: E402  (sibling module)

VIEWER_DIR = Path(__file__).resolve().parent.parent / "assets" / "viewer"
# The settings schema belongs to conductor-setup (it asks the questions); we only render it.
SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "conductor-setup" / "assets" / "settings.schema.json"
TRACK_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
STATUS = {" ": "pending", "~": "in_progress", "x": "done", "X": "done"}
MAX_BODY = 64 * 1024
WRITE_LOCK = threading.Lock()

# ---------------------------------------------------------------- parsing


def parse_registry(text: str) -> list[dict]:
    """Parse tracks.md entries: `- [ ] **Track: desc**` + `*Link: [..](path)*`."""
    entries: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        m = (re.match(r"^\s*-\s*\[([ ~xX])\]\s*\*\*(?:Track:\s*)?(.+?)\*\*", line)
             or re.match(r"^##\s*\[([ ~xX])\]\s*Track:\s*(.+?)\s*$", line))  # legacy format
        if m:
            current = {"status": STATUS[m.group(1)], "description": m.group(2).strip(), "link": None}
            entries.append(current)
            continue
        link = re.search(r"\[[^\]]*\]\(([^)]+)\)", line)
        if current is not None and link and current["link"] is None:
            current["link"] = link.group(1).strip()
    for e in entries:
        e["track_id"] = Path(e["link"]).parent.name if e["link"] else None
    return entries


_SHA = re.compile(r"\s+`?\[?([0-9a-f]{7,40})\]?`?\s*$")


def _split_shas(body: str):
    """Strip one or more trailing commit SHAs: 'Do it abc1234 def5678' -> ('Do it', [...])."""
    shas = []
    while True:
        m = _SHA.search(body)
        if not m:
            return body, shas[::-1]
        shas.append(m.group(1))
        body = body[: m.start()].rstrip()


def _is_checkpoint(text: str) -> bool:
    low = text.lower()
    return "sign-off" in low or ("verification" in low and "checkpoint" in low)


def parse_plan(text: str) -> dict:
    """Parse plan.md into {title, preamble, phases:[{title, checkpoint, tasks:[...]}]}."""
    plan: dict = {"title": None, "preamble": [], "phases": []}
    phase = task = None
    for raw in text.splitlines():
        line = raw.rstrip()
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            level, title = len(h.group(1)), h.group(2).strip()
            if level == 1 and plan["title"] is None and not plan["phases"]:
                plan["title"] = title
                continue
            cp = re.search(r"\[checkpoint:\s*([0-9a-f]{7,40})\]", title)
            title = re.sub(r"\s*\[checkpoint:[^\]]*\]", "", title).strip()
            phase = {"title": title, "checkpoint": cp.group(1) if cp else None, "tasks": [], "notes": []}
            plan["phases"].append(phase)
            task = None
            continue
        m = re.match(r"^(\s*)[-*]\s+\[([ ~xX])\]\s+(.*)$", line)
        if m and phase is not None:
            indent, mark, body = len(m.group(1).expandtabs(4)), m.group(2), m.group(3)
            body, shas = _split_shas(body)
            sha = shas[-1] if shas else None
            if indent == 0 or task is None:
                task = {
                    "text": re.sub(r"^task:\s*", "", body, flags=re.I),
                    "status": STATUS[mark],
                    "sha": sha,
                    "shas": shas,
                    "is_checkpoint": body.lower().startswith("task:") and _is_checkpoint(body),
                    "subtasks": [],
                    "notes": [],
                }
                phase["tasks"].append(task)
            else:
                task["subtasks"].append({"text": body, "status": STATUS[mark], "sha": sha, "shas": shas})
            continue
        if not line.strip():
            continue
        target = task["notes"] if task else (phase["notes"] if phase else plan["preamble"])
        target.append(line.strip())
    for p in plan["phases"]:
        items = [t["status"] for t in p["tasks"]]
        p["done"] = items.count("done")
        p["total"] = len(items)
        p["status"] = (
            "done" if items and p["done"] == len(items)
            else "in_progress" if any(s != "pending" for s in items)
            else "pending"
        )
    return plan


FB_HEAD = re.compile(r"^###\s+(FB-\d+)\s*·\s*(open|resolved)\s*·\s*([\w-]+)\s*$", re.I)


def parse_feedback(text: str) -> list[dict]:
    """Parse feedback.md items. Lines starting with `>` are agent replies."""
    items: list[dict] = []
    cur: dict | None = None
    for line in text.splitlines():
        h = FB_HEAD.match(line.strip())
        if h:
            cur = {"id": h.group(1), "status": h.group(2).lower(), "kind": h.group(3).lower(),
                   "target": "", "when": "", "body": [], "reply": []}
            items.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^-\s+\*\*(Target|When):\*\*\s*(.*)$", line)
        if m and not cur["body"]:
            cur[m.group(1).lower()] = m.group(2).strip()
        elif line.startswith(">"):
            cur["reply"].append(line[1:].strip())
        else:
            cur["body"].append(line)
    for it in items:
        it["body"] = "\n".join(it["body"]).strip()
        it["reply"] = "\n".join(it["reply"]).strip()
    return items


def next_feedback_id(text: str) -> str:
    nums = [int(n) for n in re.findall(r"^###\s+FB-(\d+)", text, re.M)]
    return f"FB-{(max(nums) if nums else 0) + 1:03d}"


def _read(p: Path) -> str | None:
    # Undecodable bytes show up as U+FFFD instead of the whole file vanishing.
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _diagram_problem(data) -> str | None:
    """Why a world-map diagram can't be drawn, or None if it can."""
    if not isinstance(data, dict):
        return "must be a JSON object"
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list) or not all(isinstance(n, dict) and "id" in n for n in nodes):
        return "`nodes` must be a list of objects, each with an `id`"
    ids = {str(n["id"]) for n in nodes}
    if len(ids) < len(nodes):
        return "node ids must be unique"
    for key in ("edges", "regions", "tour"):
        if not isinstance(data.get(key, []), list):
            return f"`{key}` must be a list"
    for e in data.get("edges", []):
        if not isinstance(e, dict) or str(e.get("from")) not in ids or str(e.get("to")) not in ids:
            return f"edge {json.dumps(e)} must join two node ids"
    missing = [t for t in data.get("tour", []) if str(t) not in ids]
    if missing:
        return f"tour stops {missing} are not node ids"
    return None


def load_diagrams(d: Path) -> list[dict]:
    out: list[dict] = []
    if not d.is_dir():
        return out
    for f in sorted(d.iterdir()):
        if f.suffix == ".json":
            text = _read(f) or ""
            try:
                data = json.loads(text)
                problem = _diagram_problem(data)
            except json.JSONDecodeError as e:
                problem = str(e)
            if problem:
                out.append({"slug": f.stem, "type": "error", "title": f.stem, "error": f"{f.name}: {problem}"})
            else:
                out.append({"slug": f.stem, "type": "map", "data": data, "title": data.get("title") or f.stem})
        elif f.suffix == ".svg":
            out.append({"slug": f.stem, "type": "svg", "title": f.stem, "svg": _read(f) or ""})
    return out


def load_schema() -> dict | None:
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def schema_settings(schema: dict) -> dict:
    """Map 'git.strategy' -> setting definition."""
    return {st["key"]: st for g in schema.get("groups", []) for st in g.get("settings", [])}


def _is_option(setting: dict, value) -> bool:
    # Values are strings; anything else (lists, objects, numbers) is invalid, never a crash.
    return isinstance(value, str) and value in {o["value"] for o in setting["options"]}


def _get(values: dict, key: str):
    cur = values
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def load_settings(root: Path) -> dict:
    """Project settings plus the schema that describes them. Missing keys fall back to defaults."""
    schema = load_schema()
    path = root / "conductor" / "settings.json"
    text = _read(path)
    values, error = {}, None
    if text is not None:
        try:
            values = json.loads(text)
            if not isinstance(values, dict):
                values, error = {}, "settings.json must contain a JSON object"
        except json.JSONDecodeError as e:
            error = f"settings.json: {e}"
    effective = {}
    if schema:
        for key, st in schema_settings(schema).items():
            v = _get(values, key)
            ok = _is_option(st, v)
            effective[key] = {"value": v if ok else st["default"],
                              "source": "file" if ok else ("invalid" if v is not None else "default")}
    return {"schema": schema, "exists": text is not None, "values": values,
            "effective": effective, "error": error}


def update_setting(root: Path, payload: dict) -> dict:
    schema = load_schema()
    if not schema:
        raise LookupError("settings schema not found next to conductor-setup")
    key, value = str(payload.get("key", "")), payload.get("value")
    st = schema_settings(schema).get(key)
    if not st:
        raise ValueError("unknown setting")
    if not _is_option(st, value):
        raise ValueError("invalid value")
    path = root / "conductor" / "settings.json"

    def build(text):
        if text is None:
            values = {"version": schema.get("version", 1)}
        else:
            try:
                values = json.loads(text)
            except json.JSONDecodeError:
                values = None
            if not isinstance(values, dict):
                raise ValueError("settings.json is not valid JSON; fix it by hand first")
        cur = values
        parts = key.split(".")
        for part in parts[:-1]:
            if not isinstance(cur.get(part), dict):
                cur[part] = {}
            cur = cur[part]
        cur[parts[-1]] = value
        return json.dumps(values, indent=2) + "\n", {"key": key, "value": value}

    with WRITE_LOCK:
        return _rewrite(path, build)


def _load_track(tdir: Path, registry_entry: dict | None, archived: bool) -> dict:
    meta_text = _read(tdir / "metadata.json")
    try:
        meta = json.loads(meta_text) if meta_text else {}
        meta_error = None if isinstance(meta, dict) else "must be a JSON object"
    except json.JSONDecodeError as e:
        meta, meta_error = {}, str(e)
    if meta_error:
        meta = {}
    return {
        "id": tdir.name,
        "archived": archived,
        "registry": registry_entry,
        "metadata": meta,
        "metadata_error": meta_error,
        "spec": _read(tdir / "spec.md") or "",
        "plan": parse_plan(_read(tdir / "plan.md") or ""),
        "feedback": parse_feedback(_read(tdir / "feedback.md") or ""),
        "diagrams": load_diagrams(tdir / "diagrams"),
    }


def _track_dirs(d: Path) -> list[Path]:
    if not d.is_dir():
        return []
    return sorted((p for p in d.iterdir() if p.is_dir() and TRACK_ID_RE.match(p.name)), key=lambda p: p.name)


def load_tracks(root: Path) -> list[dict]:
    """Registry order, then unregistered folders, then conductor/archive/ (read-only)."""
    cdir = root / "conductor"
    tracks_dir = cdir / "tracks"
    registry = parse_registry(_read(cdir / "tracks.md") or "")
    # A registry link like ../index.md must not turn conductor/ itself into a "track".
    registry = [e for e in registry if e["track_id"] and TRACK_ID_RE.match(e["track_id"]) and e["track_id"] not in (".", "..")]
    by_id = {e["track_id"]: e for e in registry}
    order = [e["track_id"] for e in registry]
    order += [p.name for p in _track_dirs(tracks_dir) if p.name not in by_id]
    tracks = [_load_track(tracks_dir / tid, by_id.get(tid), False) for tid in order if (tracks_dir / tid).is_dir()]
    seen = {t["id"] for t in tracks}
    # A folder in both places keeps the live copy: ids must stay unique in links.
    tracks += [_load_track(d, by_id.get(d.name), True) for d in _track_dirs(cdir / "archive") if d.name not in seen]
    return tracks


_DIAGRAM_REF = re.compile(r"\s*\(diagram:[^)]*\)")


def _clean_title(text: str) -> str:
    return _DIAGRAM_REF.sub("", re.sub(r"^Phase\s*\d+\s*:\s*", "", text, flags=re.I)).strip()


def _decision(feedback: list[dict], what: str) -> dict | None:
    """The review state of the spec or plan: an open change request wins, else the last approval."""
    items = [f for f in feedback if f["target"] == what]
    revise = [f for f in items if f["kind"] == "revise" and f["status"] == "open"]
    approve = [f for f in items if f["kind"] == "approve"]
    last = (revise or approve or [None])[-1]
    return {"id": last["id"], "kind": last["kind"], "status": last["status"]} if last else None


REQUEST_KINDS = ("archive", "restore", "delete")


def summarize_track(t: dict) -> dict:
    """What the home page shows for one track: small, no spec or diagram bodies."""
    reg = t["registry"] or {}
    meta = t["metadata"]
    phases = t["plan"]["phases"]
    tasks = [task for p in phases for task in p["tasks"]]
    status = reg.get("status") or meta.get("status") or "new"
    current = None
    for i, p in enumerate(phases):
        for task in p["tasks"]:
            if current is None and (task["status"] == "in_progress"
                                    or any(s["status"] == "in_progress" for s in task["subtasks"])):
                current = {"phase": i, "text": _clean_title(task["text"])}
    if t["archived"]:
        group = "archived"
    elif status == "done" or str(meta.get("status", "")).lower() in ("done", "completed", "complete"):
        group = "done"
    elif current:
        group = "now"
    else:
        group = "open"
    spec_title = next((m.group(1).strip() for m in [re.search(r"^#[ \t]+(.+)$", t["spec"], re.M)] if m), None)
    return {
        "id": t["id"],
        "archived": t["archived"],
        "title": spec_title or meta.get("description") or reg.get("description") or t["id"],
        "description": reg.get("description") or meta.get("description") or "",
        "type": meta.get("type") or "track",
        "status": status,
        "group": group,
        "current": current,
        "done": sum(1 for x in tasks if x["status"] == "done"),
        "total": len(tasks),
        "phases": [{"title": _clean_title(p["title"]), "status": p["status"], "done": p["done"], "total": p["total"],
                    "tasks": [x["status"] for x in p["tasks"]]} for p in phases],
        "open_feedback": sum(1 for f in t["feedback"] if f["status"] == "open" and f["kind"] not in REQUEST_KINDS),
        "requests": [{"id": f["id"], "kind": f["kind"]} for f in t["feedback"]
                     if f["status"] == "open" and f["kind"] in REQUEST_KINDS],
        "spec": _decision(t["feedback"], "spec"),
        "plan": _decision(t["feedback"], "plan"),
        "created": str(meta.get("created_at") or "")[:10],
        "metadata_error": bool(t["metadata_error"]),
    }


def load_state(root: Path) -> dict:
    return {
        "project": root.resolve().name,
        "initialized": (root / "conductor" / "index.md").is_file(),
        "tracks": load_tracks(root),
        "settings": load_settings(root),
        "version": state_version(root),
    }


def state_version(root: Path) -> str:
    h = hashlib.sha1()
    cdir = root / "conductor"
    for dirpath, dirnames, filenames in os.walk(cdir):
        dirnames[:] = sorted(d for d in dirnames if d != "code_styleguides")
        for name in sorted(filenames):
            try:
                st = os.stat(os.path.join(dirpath, name))
            except OSError:
                continue
            h.update(f"{dirpath}/{name}:{st.st_mtime_ns}:{st.st_size};".encode())
    return h.hexdigest()[:16]


def append_feedback(root: Path, payload: dict) -> dict:
    tid = str(payload.get("track", ""))
    if not TRACK_ID_RE.match(tid):
        raise ValueError("invalid track id")
    tracks_dir = (root / "conductor" / "tracks").resolve()
    tdir = (tracks_dir / tid).resolve()
    if tdir.parent != tracks_dir or not tdir.is_dir():
        raise LookupError("unknown track")
    kind = str(payload.get("kind", "comment")).lower()
    if kind not in {"comment", "approve", "revise"}:
        raise ValueError("invalid kind")
    target = " ".join(str(payload.get("target", "track")).split())[:300]
    text = str(payload.get("text", "")).strip()[:20000]
    if kind == "comment" and not text:
        raise ValueError("empty comment")
    # Keep user text from forging item headings or agent replies.
    text = "\n".join(("\\" + l if l.startswith(("###", ">")) else l) for l in text.splitlines())
    fb = tdir / "feedback.md"
    with WRITE_LOCK:
        return _append_item(fb, tid, kind, target, text)


def _umask() -> int:
    # Read without a race: only called under WRITE_LOCK, and set straight back.
    current = os.umask(0o022)
    os.umask(current)
    return current


def _write_atomic(path: Path, content: str) -> None:
    """Write via temp file + os.replace so a crash never leaves a truncated file.
    Always LF line endings, on every OS."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".conductor-view-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        # mkstemp creates the file owner-only; keep the target's mode, or the usual default for a new file.
        try:
            mode = path.stat().st_mode & 0o777
        except FileNotFoundError:
            mode = 0o666 & ~_umask()
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _rewrite(path: Path, build, attempts: int = 5):
    """Read-modify-write that never clobbers a concurrent edit (an agent saving
    the same file): re-read just before replacing, and start over if it changed.
    build(old_text_or_None) -> (new_text, result). Call under WRITE_LOCK."""
    for _ in range(attempts):
        before = _read(path)
        content, result = build(before)
        if _read(path) == before:
            _write_atomic(path, content)
            return result
    raise RuntimeError(f"{path.name} kept changing while saving; try again")


def _append_item(fb: Path, tid: str, kind: str, target: str, text: str) -> dict:
    def build(existing):
        if not existing:
            existing = (
                f"# Feedback: {tid}\n\n"
                "<!-- Written by the Conductor viewer. Agents: address each `open` item, then\n"
                "     change `open` to `resolved` in its heading and add a `> **Agent:** ...` reply. -->\n"
            )
        fid = next_feedback_id(existing)
        when = datetime.now().strftime("%Y-%m-%d %H:%M")
        item = f"\n### {fid} · open · {kind}\n- **Target:** {target}\n- **When:** {when}\n\n{text or '_(no message)_'}\n"
        return existing.rstrip("\n") + "\n" + item, {"id": fid}
    return _rewrite(fb, build)


# ---------------------------------------------------------------- user config
#
# The viewer's own files live outside every repo, in one folder per user:
# projects.json (registered projects), config.json (viewer preferences such as
# the port) and settings.json (the main workflow rules). CONDUCTOR_VIEW_HOME
# overrides the folder, which is also how the tests stay out of the real one.

APP = "conductor-view"
DEFAULT_PORT = 4177
PROJECT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
RESERVED_IDS = {"settings", "api"}
# File name -> what went wrong reading it: shown as a banner until restored or dismissed.
CONFIG_PROBLEMS: dict[str, dict] = {}


def config_home() -> Path:
    env = os.environ.get("CONDUCTOR_VIEW_HOME")
    if env:
        return Path(env).expanduser()
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP


def _check_object(data) -> str | None:
    return None if isinstance(data, dict) else "must contain a JSON object"


def _check_projects(data) -> str | None:
    if not isinstance(data, dict) or not isinstance(data.get("projects", []), list):
        return 'must be an object with a "projects" list'
    for e in data.get("projects", []):
        if not (isinstance(e, dict) and isinstance(e.get("path"), str) and isinstance(e.get("id"), str)
                and PROJECT_ID_RE.match(e["id"])):
            return f"project entry {json.dumps(e)} needs a string path and a valid id"
    return None


USER_FILES = {"projects.json": _check_projects, "config.json": _check_object, "settings.json": _check_object}


def _json_problem(text: str, check) -> str | None:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return f"line {e.lineno}, column {e.colno}: {e.msg}"
    return check(data)


def load_user_json(name: str) -> dict:
    """One of the viewer's own files, or {} if missing. An unreadable one is
    renamed to <name>.bad-<time> instead of being overwritten by the next save,
    and reported in CONFIG_PROBLEMS."""
    path = config_home() / name
    text = _read(path)
    if text is None:
        return {}
    problem = _json_problem(text, USER_FILES[name])
    if not problem:
        return json.loads(text)
    with WRITE_LOCK:
        if _read(path) == text:  # still the same broken content
            bad = path.with_name(f"{name}.bad-{datetime.now():%Y-%m-%dT%H%M%S}")
            try:
                os.replace(path, bad)
            except OSError:
                bad = path
            CONFIG_PROBLEMS[name] = {"file": str(path), "saved_as": str(bad), "error": problem}
    return {}


def restore_user_json(name: str) -> dict:
    """Put a fixed .bad copy back. The file it replaces is kept as .replaced-<time>."""
    if name not in USER_FILES:
        raise LookupError("unknown file")
    with WRITE_LOCK:
        problem = CONFIG_PROBLEMS.get(name)
        if not problem:
            raise LookupError(f"nothing to restore for {name}")
        bad, path = Path(problem["saved_as"]), config_home() / name
        text = _read(bad)
        if text is None:
            raise LookupError(f"{bad.name} is gone")
        still = _json_problem(text, USER_FILES[name])
        if still:
            problem["error"] = still
            raise ValueError(f"{bad.name} still can't be read: {still}")
        if path.exists() and path != bad:
            os.replace(path, path.with_name(f"{name}.replaced-{datetime.now():%Y-%m-%dT%H%M%S}"))
        os.replace(bad, path)
        del CONFIG_PROBLEMS[name]
    return {"restored": name}


def dismiss_problem(name: str) -> dict:
    CONFIG_PROBLEMS.pop(name, None)
    return {"dismissed": name}


def _update_user_json(name: str, change) -> dict:
    """Read-modify-write one of the viewer's files: change(data) -> result."""
    home = config_home()
    home.mkdir(parents=True, exist_ok=True)
    load_user_json(name)  # sets an unreadable file aside first, so it is never overwritten

    def build(text):
        if text is None:
            data = {}
        else:
            if _json_problem(text, USER_FILES[name]):
                raise RuntimeError(f"{name} changed into something unreadable while saving; try again")
            data = json.loads(text)
        result = change(data)
        return json.dumps(data, indent=2) + "\n", result

    with WRITE_LOCK:
        return _rewrite(home / name, build)


def _same_path(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def _project_id(path: Path, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9._-]+", "-", path.name.lower()).strip("-.") or "project"
    if base in RESERVED_IDS or not PROJECT_ID_RE.match(base):
        base = f"project-{base}".strip("-")
    pid, n = base, 2
    while pid in taken:
        pid, n = f"{base}-{n}", n + 1
    return pid


def registered_projects() -> list[dict]:
    return [dict(e) for e in load_user_json("projects.json").get("projects", [])]


def add_project(path) -> dict:
    """Register a project folder (one containing conductor/index.md). Idempotent."""
    p = Path(str(path)).expanduser()
    if not p.is_absolute():
        raise ValueError("give the project's full path")
    p = p.resolve()
    if not (p / "conductor" / "index.md").is_file():
        raise ValueError(f"no conductor/index.md in {p}")

    def change(data):
        projects = data.setdefault("projects", [])
        data.setdefault("version", 1)
        for e in projects:
            if _same_path(Path(e["path"]), p):
                return {**e, "added": False}
        entry = {"id": _project_id(p, {e["id"] for e in projects}), "path": str(p),
                 "added_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}
        projects.append(entry)
        return {**entry, "added": True}

    return _update_user_json("projects.json", change)


def forget_project(pid: str) -> dict:
    """Unregister a project. Its files are never touched."""
    def change(data):
        projects = data.get("projects", [])
        keep = [e for e in projects if e["id"] != pid]
        if len(keep) == len(projects):
            raise LookupError("unknown project")
        data["projects"] = keep
        return {"forgotten": pid}

    return _update_user_json("projects.json", change)


def load_config() -> dict:
    return load_user_json("config.json")


def set_config(key: str, value) -> dict:
    if key != "port":
        raise ValueError("unknown config key")
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or not 1024 <= value <= 65535):
        raise ValueError("port must be a whole number from 1024 to 65535")

    def change(data):
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
        return {"key": key, "value": value}

    return _update_user_json("config.json", change)


# ---------------------------------------------------------------- server


class Handler(BaseHTTPRequestHandler):
    root: Path = Path(".")
    server_version = "conductor-view/0.1"
    timeout = 15  # seconds a client may stall mid-request before its connection is dropped

    def log_message(self, fmt, *args):  # quiet
        pass

    def _send(self, status, body: bytes, ctype: str):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=HTTPStatus.OK):
        self._send(status, json.dumps(obj).encode(), "application/json; charset=utf-8")

    def _local_host(self) -> bool:
        # DNS rebinding: a site can point its own domain at 127.0.0.1, and then
        # its Origin and Host match each other. Only serve requests addressed
        # to this machine by name.
        port = self.server.server_address[1]
        return self.headers.get("Host", "") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def do_GET(self):
        if not self._local_host():
            return self._json({"error": "forbidden host"}, HTTPStatus.FORBIDDEN)
        path = self.path.split("?", 1)[0]
        if path == "/api/state":
            return self._json(load_state(self.root))
        if path == "/api/version":
            return self._json({"version": state_version(self.root)})
        if path == "/api/ping":
            return self._json({"app": "conductor-view", "root": str(self.root.resolve())})
        name = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
        if name not in {"index.html", "app.js", "map.js", "local.js", "style.css"}:
            return self._send(HTTPStatus.NOT_FOUND, b"not found", "text/plain")
        ctype = {"html": "text/html", "js": "text/javascript", "css": "text/css"}[name.rsplit(".", 1)[1]]
        self._send(HTTPStatus.OK, (VIEWER_DIR / name).read_bytes(), ctype + "; charset=utf-8")

    def do_POST(self):
        if not self._local_host():
            return self._json({"error": "forbidden host"}, HTTPStatus.FORBIDDEN)
        if self.path not in ("/api/feedback", "/api/settings"):
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        # Same-origin only: browsers send Origin on POST; reject other sites.
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if origin and origin.split("://", 1)[-1] != host:
            return self._json({"error": "cross-origin"}, HTTPStatus.FORBIDDEN)
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0:
            return self._json({"error": "bad Content-Length"}, HTTPStatus.BAD_REQUEST)
        if length > MAX_BODY:
            return self._json({"error": "too large"}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(payload, dict):
                raise ValueError("expected a JSON object")
            if self.path == "/api/settings":
                return self._json(update_setting(self.root, payload))
            return self._json(append_feedback(self.root, payload), HTTPStatus.CREATED)
        except LookupError as e:
            return self._json({"error": str(e)}, HTTPStatus.NOT_FOUND)
        except RuntimeError as e:
            return self._json({"error": str(e)}, HTTPStatus.CONFLICT)
        except (ValueError, json.JSONDecodeError) as e:
            return self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)


class Server(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a second program bind a port that is in use,
    # so a busy port would never be noticed. Elsewhere it only allows a quick restart.
    allow_reuse_address = os.name != "nt"
    daemon_threads = True


def existing_viewer(port: int, root: Path) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=0.5) as r:
            info = json.loads(r.read())
        return info.get("app") == "conductor-view" and info.get("root") == str(root.resolve())
    except (URLError, OSError, ValueError):
        return False


def export(root: Path, out: Path) -> None:
    html = (VIEWER_DIR / "index.html").read_text(encoding="utf-8")
    css = (VIEWER_DIR / "style.css").read_text(encoding="utf-8")
    js = (VIEWER_DIR / "map.js").read_text(encoding="utf-8") + "\n" + (VIEWER_DIR / "app.js").read_text(encoding="utf-8")
    state = json.dumps(load_state(root)).replace("</", "<\\/")
    js = js.replace("</script", "<\\/script")
    html = html.replace('<link rel="stylesheet" href="style.css">', f"<style>{css}</style>")
    html = html.replace('<script src="map.js"></script>', "").replace('<script src="local.js"></script>', "")
    html = html.replace('<script src="app.js"></script>',
                        f"<script>window.CONDUCTOR_SNAPSHOT={state};</script><script>{js}</script>")
    out.write_text(html, encoding="utf-8")


def _open_items(root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    tracks_dir = root / "conductor" / "tracks"
    if not tracks_dir.is_dir():
        return out
    for tdir in sorted(tracks_dir.iterdir()):
        text = _read(tdir / "feedback.md")
        for it in parse_feedback(text or ""):
            if it["status"] == "open":
                out[f"{tdir.name}/{it['id']}"] = {**it, "track": tdir.name}
    return out


def watch(root: Path, interval: float = 1.0) -> None:
    """Print one line per open feedback item (already open ones first), then per
    new one, plus a line whenever a workflow setting changes. Each line is meant
    to be an event for an agent that can stream a command's output."""
    seen: set[str] = set()
    # Take the starting settings before announcing, so every later difference is a real change.
    settings = None
    for _ in range(50):
        loaded = load_settings(root)
        if not loaded["error"]:
            settings = {k: v["value"] for k, v in loaded["effective"].items()}
            break
        time.sleep(0.1)
    print(f"watching {root / 'conductor'} for feedback", flush=True)
    while True:
        try:
            for key, it in _open_items(root).items():
                if key in seen:
                    continue
                body = " ".join(it["body"].split())
                body = body if len(body) <= 100 else body[:97] + "..."
                print(f"feedback {it['id']} · {it['kind']} · track {it['track']} · "
                      f"target {it['target'] or '-'}" + (f" · {body}" if body and body != "_(no message)_" else ""),
                      flush=True)
                seen.add(key)  # only once it was actually reported
            loaded = load_settings(root)
            if loaded["error"]:  # caught mid-save, or broken: keep the last good values
                time.sleep(interval)
                continue
            eff = {k: v["value"] for k, v in loaded["effective"].items()}
            if settings is not None and eff != settings:
                changed = ", ".join(f"{k} = {v}" for k, v in eff.items() if settings.get(k) != v)
                print(f"settings changed: {changed}", flush=True)
            settings = eff
        except Exception as e:  # a half-written file must not stop the watch
            print(f"watch: {e}", file=sys.stderr, flush=True)
        time.sleep(interval)


def main(argv=None) -> int:
    # Windows pipes default to the ANSI code page, which can't encode every
    # comment (emoji, CJK). Agents read this output, so always write UTF-8.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Conductor visual companion")
    ap.add_argument("--root", default=".", help="project root containing conductor/ (default: .)")
    ap.add_argument("--port", type=int, default=4177, help="port on 127.0.0.1 (0 = any free port)")
    ap.add_argument("--open", action="store_true", help="open the browser")
    ap.add_argument("--export", metavar="FILE", help="write a read-only single-file snapshot and exit")
    ap.add_argument("--watch", action="store_true",
                    help="print one line per new open feedback item or settings change (for agents)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    if not (root / "conductor").is_dir():
        print(f"error: no conductor/ directory in {root}", file=sys.stderr)
        return 2
    if args.export:
        export(root, Path(args.export))
        print(f"wrote {args.export}")
        return 0
    if args.watch:
        try:
            watch(root)
        except KeyboardInterrupt:
            pass
        return 0
    Handler.root = root
    httpd = None
    # Walk up from the requested port: reuse this project's viewer if one is
    # already running, otherwise take the first free port.
    for port in ([args.port + i for i in range(20)] if args.port else [0]):
        if port and existing_viewer(port, root):
            url = f"http://127.0.0.1:{port}/"
            print(f"conductor-view already running for this project: {url}", flush=True)
            if args.open:
                webbrowser.open(url)
            return 0
        try:
            httpd = Server(("127.0.0.1", port), Handler)
            break
        except OSError:
            print(f"port {port} is busy; trying {port + 1}", flush=True)
    if httpd is None:
        httpd = Server(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"conductor-view serving {root} at {url}", flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
