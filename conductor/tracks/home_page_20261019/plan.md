# Plan: Home page and multi-project viewer

> Planned under: trunk, commit per task, tests with each task, verification at track end.
> Stacked on `visual_companion_20261007`: this branch starts from it, not from `main`, because it extends the viewer that isn't on `main` yet. Land that track first.

## Phase 1: Track summaries and the archive

- [ ] Task: Load archived tracks from `conductor/archive/` and mark them read-only, with loader tests
- [ ] Task: Track summary for the home page: status group (Now/Open/Done/Archived), current task, per-phase progress, open feedback, spec/plan approval, with parser tests
- [ ] Task: Last activity and branch: one `git log` per project, falling back to file times without git, with tests for both
- [ ] Task: Mirror the new loaders in `local.js`, with parity tests

## Phase 2: Project registry and port

- [ ] Task: Config folder per OS and `CONDUCTOR_VIEW_HOME`; atomic `projects.json` and `config.json`; corrupt files kept as `.bad`, with tests
- [ ] Task: Port priority `--port` > `CONDUCTOR_VIEW_PORT` > `config.json` > 4177, reported with its source, with tests
- [ ] Task: Serve many projects: `/api/projects` and per-project `/api/state`; every path resolved inside a registered project, with HTTP and path-escape tests
- [ ] Task: Start command registers its project; a second start hands the project to the running viewer and exits; `--add`, `--forget`, `--list`, with CLI tests
- [ ] Task: Find projects: depth-limited scan with skip list and a time cap, add selected; add by path, with tests

## Phase 3: Home page

- [ ] Task: Routes with a project prefix, home at `#/`, old track links redirected, with browser tests
- [ ] Task: Home layout: project cards, grouped track rows, highlighted "Now", collapsed Archived, missing projects shown as not found, with browser tests
- [ ] Task: Search and status chips kept in the URL, with browser tests
- [ ] Task: Project switcher in the header; archived tracks open read-only with a banner, with browser tests
- [ ] Task: Find projects and Add by path dialogs, with browser tests
- [ ] Task: Port in the settings page: value, source, save to `config.json`, restart hint, with tests
- [ ] Task: Light/dark contrast and keyboard access for the new controls, with the existing contrast and accessibility tests

## Phase 4: Archive, restore and delete requests

- [ ] Task: `archive`, `restore` and `delete` request items in `feedback.md` (server and `local.js`), withdraw, typed confirmation for delete, with tests
- [ ] Task: "Requested, waiting for the agent" state on rows and track pages, with browser tests
- [ ] Task: Agent side: request processing in `conductor-view/SKILL.md`, formats in `file-contract.md`, aligned with `conductor-review` Track Cleanup, with skill-doc tests

## Phase 5: Docs

- [ ] Task: README (home page, registering projects, changing the port), SKILL.md start section, tech-stack note on the config folder

## Phase 6: Track Verification

- [ ] Task: Run the full suite in Chrome and Firefox
- [ ] Task: Try it with the user across this repo and the user's other Conductor projects, iterate on feedback, sign-off (Refer to workflow.md)
