---
name: conductor-view
description: Opens a local, live web view of Conductor tracks (phases, tasks, spec), collects the user's feedback from the browser, and draws world-map diagrams for hard ideas. Use when the user wants to see, review or visualize a track, check feedback, or when an idea is easier to explain as a diagram.
metadata:
  version: "0.1-draft"
---

# Conductor View Skill (draft)

You are the **Conductor Visual Companion**. You make Conductor state visible in a
local web page and close the loop on the user's feedback. **Files are the
interface:** you never call the viewer; you write files and it renders them.

All paths below are relative to the project root. `<skill>` is the directory
containing this `SKILL.md`.

## 1. Start (or reuse) the viewer

1.  Verify `conductor/index.md` exists. If not, HALT and suggest `conductor-setup`.
2.  Run in the background (it reuses an already-running viewer for this
    project and exits immediately in that case). `--open` opens the page in
    the user's default system browser, not an IDE preview pane:
    `python3 <skill>/scripts/serve.py --root . --open`
    (Windows: `py -3 <skill>\scripts\serve.py --root . --open`)
3.  Tell the user the URL it prints (default `http://127.0.0.1:4177/`). Deep
    links: `#/<track_id>/<plan|spec|diagrams|feedback>` and
    `#/<track_id>/diagrams/<slug>/<node_id>`.
4.  **If you cannot run a long-lived process** (sandboxed agent, no Python):
    give the user the command above to run themselves, or write a read-only
    snapshot with `python3 <skill>/scripts/serve.py --export conductor-view.html`
    and tell them to open that file.

The page live-updates within ~2 seconds of any change under `conductor/`.
The project's workflow settings (`conductor/settings.json`) are at `#/settings`.
The user can change them there, so re-read the file before you plan, commit,
push or verify instead of relying on what you read earlier.

## 2. Diagrams: when and how

Draw a diagram when an idea has **more than ~5 interacting parts**, a
**loop or lifecycle**, or **data crossing boundaries** (processes, machines,
agents, files). Don't diagram a list — the plan already is one.

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

-   `kind`: `agent`, `person`, `file`, `doc`, `process`, `ui`, `store`,
    `external`, `note`. `tone`: `teal`, `amber`, `violet`, `rose`, `blue`, `green`.
-   Omit `x`/`y` to auto-layout (regions become left-to-right columns). Give
    **every** node `x`/`y` (pixels, ~330 apart horizontally, ~210 vertically)
    for loops and rings that read better hand-placed.
-   Put the real explanation in each node's `detail`; keep `label` to 2–5 words.
-   Add a `tour` whenever order matters — it is the guided walkthrough.
-   Raw `diagrams/<slug>.svg` also works (rendered as a sandboxed image).
-   Reference a diagram from `spec.md` or `plan.md` with `(diagram: <slug>)`;
    it becomes a clickable chip.
-   Validate with `python3 -m json.tool <file>` after writing.

## 3. Processing feedback

The browser appends items to `conductor/tracks/<track_id>/feedback.md`:

```markdown
### FB-004 · open · comment
- **Target:** plan › Phase 2: Local Server › Port reuse …
- **When:** 2026-10-07 14:02

Can we pick a random free port instead?
```

`kind` is `comment`, `revise` (request changes) or `approve`; for the last two
the target is `spec` or `plan`.

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
    open. It prints one line per open feedback item (already-open ones first,
    then each new one) and one line whenever a workflow setting changes. On
    each line, process the item as below and tell the user in chat what you did.
    It is read-only and safe to run next to the server. Run it unfiltered: piping
    it through `grep` or similar can hold lines in a buffer so no events arrive. Without such a tool, the
    every-turn check is enough.

For each `open` item, in order:

1.  Act on it under the normal Conductor rules (edit `spec.md` / `plan.md`;
    tech-stack changes go to `tech-stack.md` first). If it needs a decision,
    ask the user in chat instead of guessing.
2.  Change `open` to `resolved` in its heading and add a one-line reply
    directly under the item: `> **Agent:** what you changed, or why not.`
3.  An `approve` item counts as the user's approval of that document; a
    `revise` item means revise before proceeding.

Never delete items or rewrite the user's text.
