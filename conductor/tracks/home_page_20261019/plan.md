# Plan: Home page and multi-project viewer

> Planned under: trunk, commit per task, tests with each task, verification at track end.
> Stacked on `visual_companion_20261007`: this branch starts from it, not from `main`, because it extends the viewer that isn't on `main` yet. Land that track first.

## Phase 1: Track summaries and the archive

- [x] Task: Load archived tracks from `conductor/archive/` and mark them read-only, with loader tests 9c83865
- [x] Task: Track summary for the home page: status group (Now/Open/Done/Archived), current task, per-phase progress, open feedback, spec/plan approval, with parser tests 9da3cd5
- [x] Task: Last activity and branch: one `git log` per project, falling back to file times without git, with tests for both f9f1c4b
- [x] Task: Git safety state per track: uncommitted, not pushed, pushed, landed, no git (one `git status` and `git for-each-ref` per project), plus an on-demand detailed check with last-fetch time, with tests on throwaway repos with a bare remote f9f1c4b
- [x] Task: Mirror the new loaders in `local.js`, with parity tests — done inside the archive and summary tasks; git facts are server-only (the no-Python view shows no badges) 9c83865 9da3cd5

## Phase 2: Project registry and port

- [x] Task: Config folder per OS and `CONDUCTOR_VIEW_HOME`; atomic `projects.json` and `config.json`; an unreadable file is renamed to `.bad-<time>` instead of overwritten, with a banner and Restore, with tests 97971b6
- [x] Task: Port priority `--port` > `CONDUCTOR_VIEW_PORT` > `config.json` > 4177, reported with its source, with tests 224099f
- [x] Task: Serve many projects: `/api/projects` and per-project `/api/state`; every path resolved inside a registered project; track ids always scoped by project, with HTTP and path-escape tests ced83b4
- [x] Task: Per-project summary cache keyed on each project's file versions; the poll re-reads only changed projects, with tests for 50 projects and two changing at once 4006dfc
- [x] Task: Layered workflow settings: Conductor-wide `settings.json` + repo file + schema defaults, per-key resolution with its source, exceptions = keys that differ, remove-key and tidy, with tests (server and `local.js`) 7efea4d
- [x] Task: `--watch --all`: feedback and settings changes across every registered project, labelled by project, with tests ec656d3
- [x] Task: Start command registers its project; a second start hands the project to the running viewer and exits; `--add`, `--forget`, `--list`, with CLI tests 8bce88a
- [x] Task: Find projects: depth-limited scan with skip list and a time cap, add selected; add by path, with tests 3f4e2df

## Phase 3: Home page

- [x] Task: Routes with a project prefix, home at `#/`, old track links redirected, with browser tests 015030b
- [x] Task: Home layout: project cards, grouped track rows, highlighted "Now", collapsed Archived, missing projects shown as not found, with browser tests 015030b
- [x] Task: Search and status chips kept in the URL, with browser tests 015030b
- [x] Task: Project switcher in the header; archived tracks open read-only with a banner, with browser tests 50051f1
- [x] Task: Find projects and Add by path dialogs, with browser tests f57a386
- [x] Task: Settings page as main rules + exception list: per-project toggle, differing keys only, Use main rule, Tidy for keys equal to the main rule, value sources everywhere, with browser tests bff6e0b
- [x] Task: Port in the settings page: value, source, save to `config.json`, restart hint, with tests 3442ffa
- [x] Task: Light/dark contrast and keyboard access for the new controls, with the existing contrast and accessibility tests 155284c

## Phase 4: Archive, restore and delete requests

- [x] Task: `archive`, `restore` and `delete` request items in `feedback.md` (server and `local.js`), withdraw, typed confirmation for delete, with tests ba98942
- [x] Task: Confirm dialog shows the git safety check and "Delete anyway" when work would be lost, with browser tests 97bcb40
- [x] Task: "Requested, waiting for the agent" state on rows and track pages, with browser tests 97bcb40
- [x] Task: Agent side: re-check git state before acting and report it; never delete uncommitted work without an explicit OK; request processing in `conductor-view/SKILL.md`, formats in `file-contract.md`, aligned with `conductor-review` Track Cleanup, with skill-doc tests 6729cbd

## Phase 5: Docs

- [x] Task: Settings layers in the skills: setup offers the Conductor-wide defaults; new-track, implement, review and status read both layers; paths per OS in the file contract, with skill-doc tests 2700a2c
- [x] Task: README (home page, registering projects, per-repo vs Conductor-wide settings, changing the port), SKILL.md start section, tech-stack note on the config folder 22db5ec

## Phase 6: Track Verification

- [x] Task: Run the full suite in Chrome and Firefox — 256 tests; Chrome OK (1 Windows-only skip), Firefox OK (9 skips: Chrome-only key checks and the Windows test); Firefox found a phone-width overflow, fixed 0d6ccd9
- [~] Task: Try it with the user across this repo and the user's other Conductor projects, iterate on feedback, sign-off (Refer to workflow.md)

## Phase 7: Feedback round 1 (FB-006)

- [x] Task: Pinned tracks: `pins.json` in the config folder (pinned and unpinned lists), `/api/pins`, in the home payload and home version; new and open tracks are pinned automatically, done and archived ones drop off unless pinned by hand, with tests 38d9324
- [x] Task: Sidebar shows pinned tracks across projects with a status badge (Now, Open, Done, Archived) and pin/unpin; a project's own track list gets the same badges, with browser tests b02cfd7
- [x] Task: Home page as a table: one row per track across projects; sortable columns; Excel-style filters on Project, Status, Type and Git; show/hide columns; filters in the URL, sort and columns remembered in the browser; Cards kept as a second view, with browser tests 83b82d4
- [x] Task: Each track once in the sidebar: pinned tracks only under Pinned, the project's list holds the rest (FB-007), with browser tests d1880f8
- [x] Task: Remove pinning (user decision after trying it): no pins.json, /api/pins or ☆; the sidebar lists unfinished tracks (Now, Open) grouped by project, the open project first; done and archived tracks only in the home table, with browser tests e56c4bf
- [x] Task: Archive/delete buttons always visible; no status badges in the sidebar (the % ring says enough); "Now" renamed "In progress" in the table, chips and cards, with browser tests ff9dfe7

## Phase 8: Feedback as a conversation

- [x] Task: Threads in `feedback.md`: replies as `> **Agent · <when>:**` / `> **You · <when>:**` entries (old `> **Agent:**` still reads), a `waiting` status for "the agent asked you something", `/api/feedback/reply` that appends your reply and reopens the item, `--watch` announces replies; server and `local.js`, with tests 21031bc
- [x] Task: Feedback tab as a log: each item a thread with who and when, Reply on any item, "Needs you" filter and counts on the tab, home table and sidebar, with browser tests 5e81f88
- [x] Task: Agent side: SKILL.md and file-contract describe threads, asking with `waiting`, and reading the whole thread; the four core skills' feedback steps match, with skill-doc tests aace6cb
- [x] Task: One home view (user decision): project cards whose tracks sit in aligned columns, grouped by status; status toggles (archived off by default), Project and Git filters, sort by activity/progress/name; the table, column picker and layout switch removed, with browser tests a61fd40
- [x] Task: Sidebar sections Active tracks (with its count) and Projects both collapse, remembered per browser, with browser tests b07e8a7
- [x] Task: In-progress colour (user decision): blue for in progress, as in Jira and Notion; a separate amethyst `--warn` for things that need you (needs you, not pushed, changes requested, warning banners, questions); both pass the contrast test in both themes a6d74f6
