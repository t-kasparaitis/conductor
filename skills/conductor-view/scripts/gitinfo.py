"""Read-only git facts for the viewer: each track's last activity, branch, and
whether its work is safe (committed, pushed, landed). Never commits, pushes,
fetches or takes git's locks. Every call has a timeout, and a project that
isn't a git repo (or a machine without git) gives "nogit" instead of an error.

Safety, worst first:
    uncommitted  files in the track folder have changes that aren't committed
    unpushed     commits for the track exist on no remote branch
    committed    everything is committed, but the repo has no remote
    pushed       everything is committed and on a remote
    landed       the track's branch is merged into main (and pushed)
    nogit        not a git repo: nothing protects the files
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

TIMEOUT = 5
_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"}


def git(root: Path, *args: str) -> str | None:
    """Run git in root; its stdout, or None on any failure."""
    if not shutil.which("git"):
        return None
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=TIMEOUT, env=_ENV,
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def repo_info(root: Path) -> dict | None:
    """Where the repo is, relative to the project root. None if root isn't in a git repo."""
    out = git(root, "rev-parse", "--show-toplevel", "--git-dir", "--git-common-dir", "--show-prefix")
    if out is None:
        return None
    lines = out.split("\n")
    if len(lines) < 4:
        return None
    top, gitdir, common, prefix = lines[:4]

    def absolute(p: str) -> Path:
        q = Path(p)
        return q if q.is_absolute() else (root / q).resolve()

    return {"top": Path(top), "gitdir": absolute(gitdir), "common": absolute(common), "prefix": prefix}


def git_version(info: dict | None) -> str:
    """Changes whenever a commit, checkout, push or fetch could change what we report."""
    if not info:
        return "nogit"
    parts = []
    for base, names in ((info["gitdir"], ("HEAD", "index", "FETCH_HEAD", "ORIG_HEAD")),
                        (info["common"], ("packed-refs",))):
        for name in names:
            try:
                st = os.stat(base / name)
                parts.append(f"{name}:{st.st_mtime_ns}:{st.st_size}")
            except OSError:
                parts.append(f"{name}:-")
    for dirpath, dirnames, filenames in os.walk(info["common"] / "refs"):
        dirnames.sort()
        for name in sorted(filenames):
            try:
                st = os.stat(os.path.join(dirpath, name))
                parts.append(f"{dirpath}/{name}:{st.st_mtime_ns}")
            except OSError:
                pass
    return str(hash(";".join(parts)))


def _track_of(path: str, prefix: str) -> tuple[str, str] | None:
    """'<prefix>conductor/tracks/x/plan.md' -> ('x', 'tracks')."""
    if not path.startswith(prefix):
        return None
    parts = path[len(prefix):].split("/")
    if len(parts) >= 4 and parts[0] == "conductor" and parts[1] in ("tracks", "archive"):
        return parts[2], parts[1]
    return None


def _uncommitted(root: Path, info: dict) -> dict[str, list[str]]:
    """Track id -> changed or untracked paths (relative to the repo top)."""
    out = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", "conductor")
    files: dict[str, list[str]] = {}
    if not out:
        return files
    entries = out.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        if "R" in xy or "C" in xy:
            i += 1  # the original path of a rename or copy follows
        hit = _track_of(path, info["prefix"])
        if hit:
            files.setdefault(hit[0], []).append(path)
    return files


def _newest_mtime(d: Path) -> float | None:
    newest = None
    for dirpath, _, filenames in os.walk(d):
        for name in filenames:
            try:
                m = os.stat(os.path.join(dirpath, name)).st_mtime
            except OSError:
                continue
            newest = m if newest is None or m > newest else newest
    return newest


def _folder(root: Path, tid: str, archived: bool) -> Path:
    return root / "conductor" / ("archive" if archived else "tracks") / tid


def project_git(root: Path, tracks: list[tuple[str, bool]]) -> dict:
    """Git facts for a project and each (track_id, archived). A handful of git
    calls per project plus one per track, so callers cache it."""
    info = repo_info(root)
    if not info:
        return {"git": False, "branch": None, "main": None, "remote": False, "last_fetch": None,
                "tracks": {tid: {"safety": "nogit", "branch": None, "uncommitted": 0, "unpushed": 0, "landed": False,
                                 "last_activity": _newest_mtime(_folder(root, tid, arch))} for tid, arch in tracks}}
    head = (git(root, "rev-parse", "--abbrev-ref", "HEAD") or "").strip() or None
    heads = set((git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads") or "").split())
    remote = bool((git(root, "for-each-ref", "--count=1", "--format=%(refname)", "refs/remotes") or "").strip())
    main = "main" if "main" in heads else "master" if "master" in heads else None
    merged = set((git(root, "branch", "--merged", main, "--format=%(refname:short)") or "").split()) if main else set()
    dirty = _uncommitted(root, info)

    # Newest commit per track folder: one log over both folders, first hit wins.
    last_commit: dict[str, int] = {}
    log = git(root, "log", "-n", "400", "--format=%x01%ct", "--name-only", "--", "conductor/tracks", "conductor/archive")
    when = None
    for line in (log or "").split("\n"):
        if line.startswith("\x01"):
            when = int(line[1:]) if line[1:].isdigit() else None
        elif line and when is not None:
            hit = _track_of(line, info["prefix"])
            if hit and hit[0] not in last_commit:
                last_commit[hit[0]] = when

    try:
        last_fetch = os.stat(info["gitdir"] / "FETCH_HEAD").st_mtime
    except OSError:
        try:
            last_fetch = os.stat(info["common"] / "FETCH_HEAD").st_mtime
        except OSError:
            last_fetch = None

    out = {}
    for tid, archived in tracks:
        branch = tid if tid in heads else None
        if branch:
            count = git(root, "rev-list", "--count", branch, "--not", "--remotes")
        else:
            rel = f"conductor/{'archive' if archived else 'tracks'}/{tid}"
            count = git(root, "rev-list", "--count", "HEAD", "--not", "--remotes", "--", rel)
        unpushed = int(count.strip()) if count and count.strip().isdigit() else 0
        landed = bool(branch and branch != main and branch in merged)
        n_dirty = len(dirty.get(tid, []))
        if n_dirty:
            safety = "uncommitted"
        elif not remote:
            safety = "committed"
        elif unpushed:
            safety = "unpushed"
        elif landed:
            safety = "landed"
        else:
            safety = "pushed"
        activity = last_commit.get(tid)
        if n_dirty or activity is None:
            mtime = _newest_mtime(_folder(root, tid, archived))
            activity = max(x for x in (activity, mtime) if x is not None) if (activity or mtime) else None
        out[tid] = {"safety": safety, "branch": branch, "uncommitted": n_dirty, "unpushed": unpushed,
                    "landed": landed, "last_activity": activity}
    return {"git": True, "branch": head, "main": main, "remote": remote, "last_fetch": last_fetch, "tracks": out}


def track_detail(root: Path, tid: str, archived: bool) -> dict:
    """Everything the archive/delete dialog spells out for one track."""
    summary = project_git(root, [(tid, archived)])
    t = summary["tracks"][tid]
    detail = {**t, "git": summary["git"], "remote": summary["remote"], "main": summary["main"],
              "last_fetch": summary["last_fetch"], "uncommitted_files": [], "unpushed_commits": []}
    if not summary["git"]:
        return detail
    info = repo_info(root)
    detail["uncommitted_files"] = _uncommitted(root, info).get(tid, [])[:50]
    rel = f"conductor/{'archive' if archived else 'tracks'}/{tid}"
    args = [t["branch"]] if t["branch"] else ["HEAD"]
    args += ["--not", "--remotes"]
    if not t["branch"]:
        args += ["--", rel]
    log = git(root, "log", "-n", "20", "--format=%h %s", *args) if t["unpushed"] else ""
    detail["unpushed_commits"] = [line for line in (log or "").split("\n") if line]
    return detail
