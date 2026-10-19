# Implementation Plan: Workflow Settings

> Planned under this repo's own settings: trunk-based, commit per task, no git
> notes, tests written with each task, and trying it out / feedback /
> iteration once at the end. That is why there are no per-phase checkpoints.
> Tests run with `python3 -m unittest discover -s tests`.

## Phase 1: Branch & Schema

- [x] Task: Create the track branch from `origin/main` and unset its upstream
- [x] Task: Commit the project context, both tracks and the viewer spike as the starting point 5cc6deb 258f462
- [x] Task: Finalise `settings.schema.json` — `current` strategy as default, `git.notes`, `with-task` testing; tests that the schema is well-formed and this repo's `settings.json` is valid fb29360
- [ ] Task: Settings loading in `serve.py` with tests (missing file → defaults, unknown value → default and flagged, broken JSON → error, never overwritten)
- [ ] Task: Describe the settings in `workflow.md` (template and this repo's copy): what each value changes, safety rules

## Phase 2: Setup Asks (diagram: git-strategies)

- [ ] Task: "Repository Workflow" step in `conductor-setup` — one question per setting, driven by the schema
    - [ ] Brownfield inference: merge commits → feature-branch; linear history → trunk
    - [ ] Write `conductor/settings.json` and link it from `conductor/index.md`
- [ ] Task: Add settings to an already-initialised project without re-running full setup

## Phase 3: Skills Obey

- [ ] Task: `conductor-new-track` — plan shape from `testing.*`; first task creates the branch
- [ ] Task: `conductor-implement` — branch, commit, notes and push per `git.*`; verification at the set cadence; stop at "branch ready"
- [ ] Task: `conductor-review` — check the work against the settings
- [ ] Task: `conductor-status` — show the active settings

## Phase 4: Viewer

- [ ] Task: `POST /api/settings` with tests (valid, unknown key/value, non-object, cross-origin, broken file, missing file)
- [ ] Task: Settings page — option cards, defaults, source flags, option details; workflow chips in every track header

## Phase 5: Track Verification

- [ ] Task: Full automated suite on Linux, macOS and Windows CI (needs a push — ask first)
- [ ] Task: Scenario runs in a scratch repo: each strategy, `phase` vs `track` verification (plan shape, commits, pushes)
- [ ] Task: Backward-compatibility run: a project with no `settings.json` behaves exactly as upstream
- [ ] Task: You try it, leave feedback in the viewer, we iterate; sign-off (Refer to workflow.md)
