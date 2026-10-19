# Visual Companion for Conductor

## Overview

Conductor's state already lives in plain files (`tracks.md`, `spec.md`,
`plan.md`, `metadata.json`). Reading those in a terminal works, but it is a poor
way to *review* a plan, see where a track stands, or understand a hard idea.

This track adds an optional **visual companion**: a local web page, served from
the user's own machine, that renders the Conductor tracks live as the agent
edits them, lets the user leave feedback that the agent picks up from disk, and
opens **world-map diagrams** — full-screen, pannable, zoomable canvases for
ideas too big for a list (diagram: architecture).

It is the Claude-Artifacts experience, without the cloud and without tying
Conductor to one agent: **files are the interface**. Any agent that can write
Markdown/JSON and read a file can drive it — Codex CLI and Claude Code are the
minimum bar (diagram: feedback-loop).

## Functional Requirements

### FR1 — File contract (the only thing agents need to know)

-   The viewer reads the existing Conductor files unchanged: `conductor/tracks.md`,
    and per track `metadata.json`, `spec.md`, `plan.md`.
-   Two new, optional per-track files:
    -   `feedback.md` — written by the viewer, read and resolved by the agent.
    -   `diagrams/<slug>.json` (world-map format, see FR4) or
        `diagrams/<slug>.svg` (raw SVG, rendered sandboxed as an image).
-   Text anywhere in a spec or plan of the form `(diagram: <slug>)` becomes a
    clickable chip that opens that diagram.

### FR2 — Local server

-   `skills/conductor-view/scripts/serve.py`, Python 3.9+ **standard library
    only**. Run from the project root; serves the viewer and a JSON API.
-   Binds to `127.0.0.1` only. Default port `4177`; if the port is already
    serving this project, reuse it instead of failing.
-   `GET /api/state` — parsed tracks (registry entry, metadata, spec Markdown,
    plan as phases → tasks → sub-tasks with status/SHA/checkpoint, feedback
    items, diagrams).
-   `GET /api/version` — cheap change token so the page live-updates within
    ~2 s of the agent editing a file.
-   `POST /api/feedback` — appends one item to the track's `feedback.md`. Only
    writes inside an existing `conductor/tracks/<id>/`; rejects anything else.
-   `POST /api/settings` — sets one project workflow setting in
    `conductor/settings.json`, validated against the schema (track
    `workflow_settings_20261017`). These two are the **only** writes the
    browser can make.
-   `--export <file.html>` — writes a single self-contained, read-only HTML
    snapshot (for sharing, or when an agent sandbox cannot run a server).

### FR3 — Viewer

-   Track list with progress; track header with type, status and a **phase
    rail** (phases as stations on a line, showing done/total).
-   **Plan** tab: phases and tasks with status (`[ ]` pending, `[~]` in
    progress, `[x]` done), commit SHAs and phase checkpoints.
-   **Spec** tab: rendered Markdown, one comment affordance per section.
-   **Diagrams** tab: thumbnails; click opens the world map.
-   **Feedback** tab: open/resolved items with the agent's replies.
-   Comment on any phase, task or spec section; **Approve** or **Request
    changes** on the spec and on the plan.
-   **Workflow settings** page plus workflow chips in every track header
    (see track `workflow_settings_20261017`).
-   Dark and light themes; keyboard accessible; works offline (no CDN).

### FR4 — World-map diagrams

-   A full-screen modal canvas: drag / arrow keys / WASD to pan in any
    direction, wheel / pinch / `+` `-` to zoom around the cursor, `F` to fit,
    `Esc` to close.
-   **Minimap** with the current viewport; click or drag it to travel.
-   JSON format: `nodes` (id, label, kind, detail Markdown, optional region and
    x/y), `edges` (from, to, label, optional dashed style), `regions`
    ("continents" that group nodes), optional `tour` (ordered node ids).
-   Nodes without coordinates are auto-laid out (layered, left → right).
-   Clicking a node opens a side panel with its detail and its connections;
    clicking a connection flies the camera there.
-   A **tour** steps the camera through the idea in order — the way to explain
    something difficult one stop at a time.

### FR5 — Agent instructions

-   New skill `skills/conductor-view/SKILL.md`: how to start/reuse the server,
    the file contract, the diagram format, when a diagram is worth drawing, and
    how to process `feedback.md`.
-   Short "Visual companion" hooks in `conductor-new-track` (offer review in the
    viewer, read approvals/feedback), `conductor-implement` (check feedback at
    phase checkpoints), `conductor-review` and `conductor-status`.
-   Hooks are conditional: if the skill or Python is unavailable, every
    existing skill behaves exactly as today.

## Non-Functional Requirements

-   **Agent-agnostic:** no agent-specific APIs; verified end-to-end with Codex
    CLI and Claude Code.
-   **Optional:** the core skills remain pure Markdown with no runtime
    dependency. Python is only needed to *view*.
-   **Local & private:** nothing leaves the machine; no external requests.
-   **Safe:** localhost only; feedback writes are path-checked; SVG is rendered
    as an image so embedded scripts cannot run; all Markdown is escaped before
    formatting.
-   **No build step:** vanilla HTML/CSS/JS, installable by `link.sh`
    unchanged (the new folder under `skills/` is linked automatically).

### Runtime decision

-   **Python 3.9+ standard library is the only runtime**, kept to a single file
    (`serve.py`). No bash, PowerShell or zsh in the viewer path, so the same
    command works on every OS. No pip, no Node, no build step.
-   Not every machine ships it (macOS only ships a stub that installs the
    Xcode Command Line Tools; Windows has a Store stub), so the skill detects
    a missing Python and says how to get it instead of failing silently.
-   **Rejected: a compiled binary (Rust/Go).** No runtime needed, but users
    would be running an opaque executable from a public repo. It would need
    builds for every OS and CPU, macOS notarization and Windows SmartScreen
    reputation, and a release pipeline, and it breaks the "clone, link,
    read every line" install model. A short, readable Python file is easier to
    audit than a binary is to trust.
-   **Zero-runtime fallback (read-only):** `viewer/index.html` opened straight
    from disk lets the user pick the project folder (a directory file input,
    which works in all four browsers) and renders it. With no server it cannot
    write `feedback.md`, so comments are collected into a "Copy feedback"
    block to paste into the agent chat.

### Compatibility (public release)

The repository is public, so the companion must work for anyone who clones it.

-   **Operating systems:** Linux, macOS and Windows. Python 3.9+ (3.9 is
    macOS's bundled `python3`); on Windows the launcher is `py -3`. No
    POSIX-only calls; paths via `pathlib`; `--open` uses the system default
    browser on every OS.
-   **Browsers:** current Chrome is preferred and Firefox is the second
    choice; both are tested. Other browsers (Edge, Safari, ...) are untested,
    but the code sticks to standard web-platform features (no Chromium-only
    APIs) so they have a fair chance of working.
    Pointer events for mouse/touch/pen; wheel handling copes with both pixel
    and line `deltaMode` (Firefox).
-   **Persistence:** everything that matters is a file under `conductor/` and
    survives restarts, reboots and agent switches. `feedback.md` and
    `diagrams/` are committed alongside the track, so the review history is
    kept in git. Writes are atomic (temp file + rename) and serialised, so two
    tabs or a crash can't corrupt or duplicate items. Always UTF-8 and LF line
    endings, enforced by `.gitattributes`. Per-viewer conveniences (theme,
    current tab) live in `localStorage` and the URL, and the page works if
    storage is blocked.

## Acceptance Criteria

1.  Running `python3 <skill>/scripts/serve.py` in a project with `conductor/`
    shows every track with correct phase/task status.
2.  Editing `plan.md` (e.g. `[ ]` → `[~]`) is reflected in the open page
    within ~2 seconds, no manual refresh.
3.  A comment left on a task appears in that track's `feedback.md` with its
    target; after the agent marks it resolved and replies, the page shows it.
4.  A diagram JSON with no coordinates opens as a pannable, zoomable map with
    minimap, node details and a working tour.
5.  Codex CLI, given only the skill, can start the viewer (or export a
    snapshot), draw a diagram and resolve feedback.
6.  `link.sh` / `link.ps1` install the new skill with no changes; CI passes.
7.  CI runs the Python tests on Ubuntu, macOS and Windows (Python 3.9 and
    latest), and browser end-to-end tests in Chrome and Firefox on all three.
8.  Feedback written on Windows round-trips byte-identical (UTF-8, LF) on
    Linux/macOS, and ten simultaneous submissions yield ten distinct IDs.

## Out of Scope

-   Hosting, sharing links, or any cloud sync (that is what Artifacts are for).
-   Editing spec/plan text from the browser — the agent owns those files.
-   Real-time multi-user collaboration.
-   A Mermaid/Graphviz dependency; may be revisited later.

## Open Questions

-   **Feedback format:** Markdown (`feedback.md`, agent-friendly, proposed) or
    JSON (`feedback.json`, easier to machine-edit)?
-   **Who starts the server:** the agent in the background (proposed, with a
    printed fallback command for sandboxed agents) or always the user?
-   **Diagram authoring:** JSON world-map only, or also accept Mermaid text
    (needs a vendored renderer, ~2 MB)?
-   **Dogfooding in public:** commit this repo's own `conductor/` folder
    (this track, as a live example) or keep it local/ignored?
-   **Browser test tooling:** Playwright as a CI-only dev dependency (proposed;
    end users still need nothing but Python), or manual checks per release?
-   **Name:** `conductor-view`, `conductor-companion`, or `conductor-canvas`?
