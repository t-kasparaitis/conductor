# Implementation Plan: Workflow Settings

> Planned under this repo's own settings: trunk-based, commit per task, no git
> notes, tests written with each task, and trying it out / feedback /
> iteration once at the end. That is why there are no per-phase checkpoints.
> Tests run with `python3 -m unittest discover -s tests`.

## Phase 1: Branch & Schema

- [x] Task: Create the track branch from `origin/main` and unset its upstream
- [x] Task: Commit the project context, both tracks and the viewer spike as the starting point 5cc6deb 258f462
- [x] Task: Finalise `settings.schema.json` — `current` strategy as default, `git.notes`, `with-task` testing; tests that the schema is well-formed and this repo's `settings.json` is valid fb29360
- [x] Task: Settings loading in `serve.py` with tests (missing file → defaults, unknown value → default and flagged, broken JSON → error, never overwritten) f988e3f
- [x] Task: Describe the settings in `workflow.md` (template and this repo's copy): what each value changes, safety rules 1e65287

## Phase 2: Setup Asks (diagram: git-strategies)

- [x] Task: "Repository Workflow" step in `conductor-setup` — one question per setting, driven by the schema ffd388c
    - [x] Brownfield inference: merge commits → feature-branch; linear history → trunk
    - [x] Write `conductor/settings.json` and link it from `conductor/index.md`
- [x] Task: Add settings to an already-initialised project without re-running full setup ffd388c

## Phase 3: Skills Obey

- [x] Task: `conductor-new-track` — plan shape from `testing.*`; creates the track branch before writing its files 3925285
- [x] Task: `conductor-implement` — branch, commit, notes and push per `git.*`; verification at the set cadence; stop at "branch ready" 3925285
- [x] Task: `conductor-review` — check the work against the settings 3925285
- [x] Task: `conductor-status` — show the active settings 3925285

## Phase 4: Viewer

- [x] Task: `POST /api/settings` with tests (valid, unknown key/value, non-object, cross-origin, broken file, missing file) 7e8b395
- [x] Task: Settings page — option cards, defaults, source flags, option details; workflow chips in every track header 9fb7efd

## Phase 5: Track Verification

- [ ] Task: Full automated suite on Linux, macOS and Windows CI (needs a push — ask first)
- [x] Task: Scenario run in a scratch repo: trunk + tests with each task + verification at track end (plan shape, branch, commits, no pushes)
- [x] Task: Backward-compatibility run: a project with no `settings.json` behaves exactly as upstream
- [x] Task: Fix the instructions the scenario agents found unclear (branch creation, rebase points, when `ask` asks, checkpoint SHA, metadata status, settings path) 1a74344
- [x] Task: Feedback round 1 — progress bar grouped by phase with clickable phase bars and task segments; change requests badge only while open (FB-003) fba2a93
- [~] Task: You try it, leave feedback in the viewer, we iterate; sign-off (Refer to workflow.md)
