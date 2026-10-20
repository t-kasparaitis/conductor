# Conductor View: File Contract

Files are the interface between agents and the viewer. Agents write files;
the viewer reads them and redraws within about two seconds. Inside a
project, the browser writes exactly two kinds of change, both through the
local server: appended items in a track's `feedback.md` (and marking its own
archive/restore/delete request withdrawn), and values in
`conductor/settings.json`. Nothing else under `conductor/` is ever written,
moved or deleted by the viewer. Outside every project it keeps its own files
in the [viewer config folder](#viewer-config-folder).

Paths are relative to the project root unless they say otherwise.

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
| `conductor/archive/<id>/…` | Archived tracks (same files as above), read-only | Not listed |
| `conductor/settings.json` | This repo's workflow exceptions | The main rules, then schema defaults |
| git (read-only) | Each track's branch, last activity and safety badge | "no git" |

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
-   Kinds `archive`, `restore` and `delete` are track requests (target
    `track`). The server writes their text, not the browser: what to do, the
    git state when asked, and an optional one-line note from the user. There
    is at most one open request of each kind per track. Archive is offered
    for live tracks, restore for archived ones, delete for both (after the
    user types the track id). Archived tracks take no other feedback.
-   A request the user takes back is marked `resolved` with the reply
    `> **Withdrawn** in the viewer before the agent acted on it.`
-   `Target` is a path through the documents: `plan`, `plan › Phase N: Name`,
    `plan › Phase N: Name › Task text`, `spec`, or `spec › Section`.
-   Lines starting with `>` are the agent's reply. User text that would start
    with `###` or `>` is escaped by the server, so it can't fake a heading or
    a reply.
-   **Agents:** change `open` to `resolved` and add a `> **Agent:** …` line.
    Never delete items or edit the user's text.

The server appends with an atomic replace (write a temporary file, then
rename) under a lock, with LF line endings on every OS. Just before
replacing, it re-reads the file; if an agent saved it in the meantime, the
server starts over from the agent's version, so neither edit is lost.
Agents should likewise re-read `feedback.md` right before editing it.

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

Node ids must be unique, every edge must join two node ids, and every tour
stop must be a node id; otherwise the diagram shows as an error card.
`<slug>` must match `[\w.-]+`. A raw `diagrams/<slug>.svg` is shown as an
image (scripts inside it never run). `(diagram: <slug>)` anywhere in
`spec.md` or `plan.md` becomes a chip that opens the diagram.

## Workflow settings: main rules and exceptions

Keys, options and defaults are defined by
`skills/conductor-setup/assets/settings.schema.json`. Two files can set them:

1.  **This repo's exceptions:** `conductor/settings.json`, committed with the
    repo and shared by everyone who works on it. It only needs the keys that
    differ from the main rules.
2.  **The user's main rules:** `settings.json` in the
    [viewer config folder](#viewer-config-folder), on this machine only.

**Each key resolves to:** the repo's value if it is a valid option, else the
main rule if valid, else the schema default. A repo value equal to the main
rule is "same as main rule"; the viewer's Tidy removes those. An agent that
can't read outside the repo (a sandbox) uses the repo file and the schema
defaults, and says so.

The viewer only writes keys and values from the schema, keeps any other
content, refuses to touch a repo file that isn't valid JSON, and removes a
key (and any group it empties) when the user picks "use main rule".

## Viewer config folder

| OS | Folder |
| --- | --- |
| Linux | `$XDG_CONFIG_HOME/conductor-view/` (default `~/.config/conductor-view/`) |
| macOS | `~/Library/Application Support/conductor-view/` |
| Windows | `%APPDATA%\conductor-view\` |

`CONDUCTOR_VIEW_HOME` overrides it. It holds:

| File | Contents |
| --- | --- |
| `projects.json` | `{"version": 1, "projects": [{"id": "my-app", "path": "/abs/path", "added_at": "…"}]}`: registered projects. Ids are the folder name, lower-cased, made unique. |
| `config.json` | `{"port": 5000}`: the saved port. Priority: `--port`, then `CONDUCTOR_VIEW_PORT`, then this, then 4177. |
| `settings.json` | The main workflow rules, same shape as a repo's `conductor/settings.json`. |

All three are written atomically. One that can't be read is renamed to
`<name>.bad-<time>` (never overwritten), the viewer starts that file fresh,
and every page shows a banner with the error and a Restore button. Restore
puts the fixed copy back and keeps whatever it replaces as
`<name>.replaced-<time>`. Nothing is deleted.

## Links

`<project>` is a project id from `projects.json`; `<id>` a track id. A link
without the project (`#/<id>/…`) still works when only one project has that
track, or the viewer was started in the one that does.

| Link | Opens |
| --- | --- |
| `#/` | Home. Filters: `?q=<search>`, and comma lists `status=now,open,done,archived`, `project=<ids>`, `type=<types>`, `git=uncommitted,unpushed,committed,nogit,pushed,landed`. Without `status`, archived tracks are hidden. `?layout=table\|cards` picks the layout (remembered per browser). |
| `#/<project>` | Home, showing only that project |
| `#/settings` | Main workflow rules and every project's exceptions |
| `#/<project>/settings` | One project's workflow settings |
| `#/<project>/<id>/plan/phase-<n>` | One phase (`phase-all` for the whole plan) |
| `#/<project>/<id>/spec/section-<n>` | One spec section (`section-all` for all) |
| `#/<project>/<id>/diagrams/<slug>/<node>` | A diagram, focused on a node |
| `#/<project>/<id>/feedback` | The track's feedback |
