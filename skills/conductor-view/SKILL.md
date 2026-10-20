---
name: conductor-view
description: Opens a local, live web view of Conductor tracks (phases, tasks, spec), collects the user's feedback from the browser, and draws world-map diagrams for hard ideas. Use when the user wants to see, review or visualize a track, check feedback, or when an idea is easier to explain as a diagram.
metadata:
  version: "1.1"
---

# Conductor View Skill

You are the **Conductor Visual Companion**. You make Conductor state visible in a
local web page and close the loop on the user's feedback. **Files are the
interface:** you never call the viewer; you write files and it renders them.
Every file it reads or writes, and their exact formats, are in
`<skill>/references/file-contract.md`.

All paths below are relative to the project root. `<skill>` is the directory
containing this `SKILL.md`.

## 1. Start (or reuse) the viewer

1.  Verify `conductor/index.md` exists. If not, HALT and suggest `conductor-setup`.
2.  **Find Python 3.9+:** `python3 --version` (Windows: `py -3 --version`).
    Standard library only; nothing to install.
3.  **With Python**, run this in the background:
    `python3 <skill>/scripts/serve.py --root . --open`
    (Windows: `py -3 <skill>\scripts\serve.py --root . --open`)
    -   **One viewer serves every project on the machine.** Starting it
        registers this project. If a viewer is already running, the command
        adds this project to it, prints the project's link and exits straight
        away; nothing else to do.
    -   The port is 4177 unless the user chose another (`--port`, the
        `CONDUCTOR_VIEW_PORT` environment variable, or the port saved on the
        viewer's settings page). If it's taken by something else, the viewer
        moves to the next free port and prints which.
    -   `--open` opens the user's default system browser, not an IDE preview.
    -   Tell the user the URL it prints. The home page (`#/`) is a table of
        every registered project's tracks, and the sidebar holds pinned
        tracks (new and open ones automatically).
4.  **If you can't run a long-lived process** (sandboxed agent): give the user
    that command to run themselves.
5.  **Without Python:** tell the user to open `<skill>/assets/viewer/index.html`
    directly in their browser and pick the project folder. That view is
    read-only and doesn't live-update; comments are copied for them to paste to
    you (see section 3).
6.  **A file to send someone:** `python3 <skill>/scripts/serve.py --export conductor-view.html`
    writes a single read-only HTML snapshot.

The page updates within about two seconds of any change under `conductor/`.

**Links you can give the user.** `<project>` is the id the start command
prints (`serve.py --list` shows them all); links without it still work when
the track id is unique.

| Link | Opens |
| --- | --- |
| `#/` | Home: every project and its tracks |
| `#/settings` | The main workflow rules, and every project's exceptions |
| `#/<project>/settings` | This project's workflow settings |
| `#/<project>/<track_id>/plan/phase-<n>` | One phase of the plan (`phase-all` for every phase) |
| `#/<project>/<track_id>/spec/section-<n>` | One spec section (`section-all` for the whole spec) |
| `#/<project>/<track_id>/diagrams/<slug>/<node_id>` | A diagram, focused on a node |
| `#/<project>/<track_id>/feedback` | The track's feedback |

The user can change workflow settings in the viewer at any time, so re-read
them before you plan, commit, push or verify instead of relying on what you
read earlier. Settings come in two layers: the repo's
`conductor/settings.json` (exceptions for this repo) over the user's main
rules for every project. The file contract has the paths and the rule.

## 2. Diagrams: when and how

Draw a diagram when an idea has **more than ~5 interacting parts**, a
**loop or lifecycle**, or **data crossing boundaries** (processes, machines,
agents, files). Don't diagram a list; the plan already is one.

Write `conductor/tracks/<track_id>/diagrams/<slug>.json`:

```json
{
  "title": "Short title",
  "summary": "One sentence: what to take away.",
  "regions": [ { "id": "disk", "label": "Disk", "tone": "amber" } ],
  "nodes": [
    { "id": "plan", "label": "plan.md", "kind": "file", "region": "disk",
      "detail": "Markdown shown when the node is clicked." }
  ],
  "edges": [ { "from": "plan", "to": "server", "label": "parsed", "style": "dashed" } ],
  "tour": ["plan", "server"]
}
```

-   Put the real explanation in each node's `detail`; keep node labels to 2–5
    words and edge labels to 1–4 (long edge labels widen every column).
-   Omit `x`/`y` to auto-layout (regions become left-to-right columns). Give
    **every** node `x`/`y` (pixels, ~330 apart horizontally, ~210 vertically)
    for loops and rings that read better hand-placed.
-   Add a `tour` whenever order matters: it is the guided walkthrough.
-   Node ids must be unique and every edge and tour stop must name a node, or
    the diagram shows as an error card. Kinds, tones and the rest are in the
    file contract.
-   A raw `diagrams/<slug>.svg` also works; it's shown as an image, so scripts
    in it never run.
-   Reference a diagram from `spec.md` or `plan.md` with `(diagram: <slug>)`;
    it becomes a clickable chip.
-   Validate with `python3 -m json.tool <file>` after writing, if Python is
    available.

## 3. Processing feedback

The browser appends items to `conductor/tracks/<track_id>/feedback.md`:

```markdown
### FB-004 · open · comment
- **Target:** plan › Phase 2: Local Server › Port reuse …
- **When:** 2026-10-07 14:02

Can we pick a random free port instead?
```

`kind` is `comment`, `revise` (request changes) or `approve`; for the last two
the target is `spec` or `plan`. `archive`, `restore` and `delete` are track
requests from the home page; see section 4.

The browser cannot message you. It only writes this file, and the viewer
shows "waiting for the agent" until you resolve the item. So:

-   **Every turn:** whenever the viewer is in use for this project, start every
    reply by checking each track's `feedback.md` for `open` items. That way
    anything the user posts is picked up the next time they say anything,
    including "check feedback". Checking is cheap: look for `· open ·` in the
    headings.
-   **Optional live watch:** if your harness can stream a background command's
    output as events (Claude Code's Monitor tool, for example), run
    `python3 <skill>/scripts/serve.py --root . --watch` while the session is
    open (`--watch --all` follows every registered project and names it on
    each line). It prints one line per open feedback item (already-open ones
    first, then each new one) and one line whenever a workflow setting
    changes. On
    each line, process the item as below and tell the user in chat what you did.
    It is read-only and safe to run next to the server. Run it unfiltered: piping
    it through `grep` or similar can hold lines in a buffer so no events arrive.
    Without such a tool, the every-turn check is enough.
-   **Pasted feedback:** a user of the no-Python view pastes an item headed
    `### FB-NEW · open · …`. Add it to that track's `feedback.md` with the
    next free id, then process it like any other.

For each `open` item, in order:

1.  Act on it under the normal Conductor rules (edit `spec.md` / `plan.md`;
    tech-stack changes go to `tech-stack.md` first). If it needs a decision,
    ask the user in chat instead of guessing.
2.  Change `open` to `resolved` in its heading and add a one-line reply
    directly under the item: `> **Agent:** what you changed, or why not.`
3.  An `approve` item counts as the user's approval of that document; a
    `revise` item means revise before proceeding.

**Re-read `feedback.md` right before you edit it.** The browser may have
appended an item since you last read it; editing an old copy would delete
the user's new comment. Never delete items or rewrite the user's text.

## 4. Archive, restore and delete requests

The home page never moves or deletes a track itself. It adds a request item
(kind `archive`, `restore` or `delete`, target `track`) to the track's
`feedback.md`, written by the viewer: what to do, plus the track's git state
when it was asked. Handle it like other feedback, in order, with the same
steps as `conductor-review`'s Track Cleanup:

1.  **Check git first,** for the track's folder: `git status --porcelain --
    <folder>` (uncommitted files) and, if the repo has a remote, commits not
    on any remote (`git log --oneline <track branch or HEAD> --not --remotes
    -- <folder>`). Tell the user what you found in one line.
2.  **Archive:** `git mv conductor/tracks/<id> conductor/archive/<id>`
    (create `conductor/archive/` if needed), remove the track's entry from
    `conductor/tracks.md`, resolve the item in its new place
    (`conductor/archive/<id>/feedback.md`), and commit everything together
    with `chore(conductor): Archive track '<name>'`. Uncommitted files move
    with the folder and are committed with it.
3.  **Restore:** the reverse: `git mv` it back to `conductor/tracks/<id>`,
    add its registry entry back (status `[ ]`, `[~]` or `[x]` from its plan),
    resolve the item, and commit with `chore(conductor): Restore track
    '<name>'`.
4.  **Delete:** cannot be undone. Ask the user in chat to confirm with a
    **Yes/No question**, naming what would be lost (uncommitted files,
    commits only on this machine, or "nothing: it's committed and pushed").
    **Never delete uncommitted work without an explicit yes to that.** On
    yes: `git rm -r` the folder (plain removal if it isn't tracked), remove
    its registry entry, and commit with `chore(conductor): Delete track
    '<name>'`. The item goes with the folder, so tell the user in chat that
    it's done. On no: resolve the item with your reason.
5.  An item the user withdrew is already `resolved` with a "Withdrawn" line:
    skip it.
