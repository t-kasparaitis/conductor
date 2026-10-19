# Conductor View: File Contract

Files are the interface between agents and the viewer. Agents write files;
the viewer reads them and redraws within about two seconds. The browser
writes exactly two kinds of change, both through the local server: appended
items in a track's `feedback.md`, and values in `conductor/settings.json`.
Nothing else under `conductor/` is ever written by the viewer.

All paths are relative to the project root.

## What the viewer reads

| Path | Used for | If missing or malformed |
| --- | --- | --- |
| `conductor/index.md` | Detecting an initialized project | "No Conductor project here yet" |
| `conductor/tracks.md` | Track order, status, description | Tracks are listed from the folder, alphabetically |
| `conductor/tracks/<id>/metadata.json` | Type, status, dates | Shown as a warning chip; the track still renders |
| `conductor/tracks/<id>/spec.md` | Spec tab | "No spec yet" |
| `conductor/tracks/<id>/plan.md` | Plan tab, progress | "No plan yet" |
| `conductor/tracks/<id>/feedback.md` | Feedback tab, badges | No feedback |
| `conductor/tracks/<id>/diagrams/*.json`, `*.svg` | Diagrams tab, `(diagram: slug)` chips | An error card for that diagram only |
| `conductor/settings.json` | Workflow settings page, header chips | Schema defaults |

`<id>` must match `[A-Za-z0-9._-]+`.

## `tracks.md` (registry)

Each entry is a checkbox line followed by a link to the track's `index.md`.
The track id is the link's parent folder name.

```markdown
- [~] **Track: Short description**
*Link: [./tracks/<id>/index.md](./tracks/<id>/index.md)*
```

Status marks: `[ ]` pending, `[~]` in progress, `[x]` done. The legacy
`## [ ] Track: description` heading form is also read.

## `plan.md`

```markdown
# Implementation Plan: Title

> Anything before the first phase is the preamble.

## Phase 1: Name (diagram: slug) [checkpoint: abc1234]

- [x] Task: Did the thing abc1234
    - [x] A sub-task
    Free text under a task becomes that task's notes.
- [~] Task: Doing this
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
```

-   The first `#` heading is the title. Every later heading starts a phase.
-   `[checkpoint: <sha>]` in a phase heading records its checkpoint commit.
-   A checkbox line at column 0 is a task; an indented one is a sub-task of
    the task above it.
-   One or more 7–40 character hex SHAs at the end of a task or sub-task
    line are its commits (`abc1234`, `` `abc1234` `` or `[abc1234]`).
-   A task whose text mentions "sign-off", or both "verification" and
    "checkpoint", is drawn as a checkpoint.
-   A phase is done when all its tasks are done, in progress when any task
    has started, and pending otherwise.

## `feedback.md`

Written by the browser, answered by agents. One item per `###` heading:

```markdown
### FB-004 · open · comment
- **Target:** plan › Phase 2: Local Server › Port reuse
- **When:** 2026-10-07 14:02

The user's text, as Markdown.

> **Agent:** What the agent changed, or why not.
```

-   `FB-NNN` ids increase by one per file and are never reused.
-   Status is `open` or `resolved`. Kind is `comment`, `revise` (request
    changes) or `approve`; `revise` and `approve` target `spec` or `plan`.
-   `Target` is a path through the documents: `plan`, `plan › Phase N: Name`,
    `plan › Phase N: Name › Task text`, `spec`, or `spec › Section`.
-   Lines starting with `>` are the agent's reply. User text that would start
    with `###` or `>` is escaped by the server, so it can't fake a heading or
    a reply.
-   **Agents:** change `open` to `resolved` and add a `> **Agent:** …` line.
    Never delete items or edit the user's text.

The server appends with an atomic replace (write a temporary file, then
rename) under a lock, with LF line endings on every OS.

## `diagrams/<slug>.json` (world map)

```json
{
  "title": "Short title",
  "summary": "One sentence: what to take away.",
  "regions": [{ "id": "disk", "label": "Disk", "tone": "amber" }],
  "nodes": [
    { "id": "plan", "label": "plan.md", "kind": "file", "region": "disk",
      "detail": "Markdown shown when the node is clicked.", "x": 0, "y": 0 }
  ],
  "edges": [{ "from": "plan", "to": "server", "label": "parsed", "style": "dashed" }],
  "tour": ["plan", "server"]
}
```

| Field | Values |
| --- | --- |
| `kind` | `agent`, `person`, `file`, `doc`, `process`, `ui`, `store`, `external`, `note` |
| `tone` | `teal`, `amber`, `violet`, `rose`, `blue`, `green` |
| `style` | `solid` (default), `dashed` |
| `x`, `y` | Pixels. Give them to **every** node or to none; with none, regions become left-to-right columns and nodes are ranked by their edges. |
| `tour` | Node ids in walkthrough order. |

`<slug>` must match `[\w.-]+`. A raw `diagrams/<slug>.svg` is shown as an
image (scripts inside it never run). `(diagram: <slug>)` anywhere in
`spec.md` or `plan.md` becomes a chip that opens the diagram.

## `conductor/settings.json`

Defined by `skills/conductor-setup/assets/settings.schema.json`, which lists
every key, its options and its default. The viewer only writes keys and
values from that schema, keeps any other content, and refuses to touch a
file that isn't valid JSON.

## Links

| Link | Opens |
| --- | --- |
| `#/settings` | Workflow settings |
| `#/<id>/plan/phase-<n>` | One phase (`phase-all` for the whole plan) |
| `#/<id>/spec/section-<n>` | One spec section (`section-all` for all) |
| `#/<id>/diagrams/<slug>/<node>` | A diagram, focused on a node |
| `#/<id>/feedback` | The track's feedback |
