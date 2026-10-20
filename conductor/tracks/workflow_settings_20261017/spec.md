# Workflow Settings for Conductor

## Overview

Conductor currently hard-codes one way of working into `workflow.md`: commit
every task to whatever branch is checked out, attach git notes, never push, and
stop for full verification at the end of every phase. Teams and people differ,
and the agent should follow **the repository's** conventions, not one default.

This track adds a small, machine-readable **`conductor/settings.json`**,
chosen during `conductor-setup`, read by every skill before it plans, commits,
pushes or tests, and shown in the viewer where any setting can be switched
with one click (diagram: git-strategies).

## Functional Requirements

### FR1 — Settings file and schema

-   `conductor/settings.json` holds the project's choices, nested by group:
    `{"version": 1, "git": {...}, "testing": {...}}`.
-   `skills/conductor-setup/assets/settings.schema.json` is the single source of
    truth for every setting: key, label, options, per-option summary and
    detail, and the default. Setup questions, skill behaviour and the viewer
    are all driven by it.
-   A missing file or key means **the default**, and the defaults are exactly
    today's behaviour, so existing projects are unaffected.

### FR2 — Settings

| Key | Options (default first) |
| --- | --- |
| `git.strategy` | `current` — commit on whatever branch is checked out (today's behaviour) · `feature-branch` — branch per track, merge back with a merge commit, never rewrite pushed history · `trunk` — short-lived branch rebased on `origin/main`, `push --force-with-lease --force-if-includes` on the track branch only |
| `git.commit` | `task` · `phase` · `track` |
| `git.push` | `ask` · `phase` · `track` |
| `git.notes` | `on` (task summaries and verification reports as git notes) · `off` |
| `testing.style` | `tdd` (failing test first in every task) · `with-task` (tests written alongside the code in every task) · `after` (tests written in the final verification phase) |
| `testing.verification` | `phase` (checkpoint after every phase) · `track` (one Track Verification phase at the end) |

-   `testing.verification` is about **trying the work**: the manual walkthrough,
    the user's feedback, iterating and sign-off. With either value the automated
    suite still runs before every commit.
-   **Safety rules for every strategy:**
    -   Never force-push `main` or any branch not created for the current track.
    -   Never push when `git.push` is `ask` without asking in chat first.
    -   A new track branch must not track `origin/main` as its upstream
        (`git branch --unset-upstream` after creating it), so a bare `git push`
        can never reach main.
    -   The agent never lands work on `main` itself. When the track is
        verified it stops at "branch ready" and shows the user the merge or PR
        commands for the chosen strategy.

### FR3 — Setup asks

-   `conductor-setup` gains a **Repository Workflow** step after Workflow
    Configuration: one question per setting, options from the schema,
    recommended option first. Brownfield repos: infer from history first
    (merge commits → `feature-branch`, linear history → `trunk`) and offer
    that as the recommendation.
-   Writes `conductor/settings.json` and links it from `conductor/index.md`.
-   Existing projects: running setup again (or asking "configure workflow
    settings") adds the file without touching anything else.

### FR4 — Skills obey

-   **new-track:** plan shape follows `testing.*`. With `phase`, a checkpoint
    task ends every phase (today's behaviour). With `track`, no per-phase
    checkpoints and a final **Track Verification** phase. With `tdd`, tasks
    start with failing tests (today's behaviour). With `with-task`, every task
    names the tests it adds next to the code. With `after`, the final phase
    writes them. With `trunk` or `feature-branch`, new-track creates the
    track branch before writing the track's files, so they are committed on
    the branch, never on `main`.
-   **implement:** commits and pushes per `git.*`; integrates per strategy
    (rebase vs merge); runs verification at the cadence set.
-   **review:** checks the work against the settings (for example "commit
    per task" was honoured, and no force-push to main).
-   `workflow.md` (template and this repo's copy) references the settings
    instead of hard-coding one behaviour.

### FR5 — Viewer

-   A **Workflow settings** page lists every setting as option cards, shows
    the default, flags values that came from the file versus the default, and
    shows each option's detail (for example the exact git commands).
-   Clicking an option saves it immediately to `settings.json` through a
    validated `POST /api/settings`: only schema keys and values are accepted,
    the write is atomic, and a broken file is never overwritten.
-   Every track header shows the active workflow as chips that link to the
    page, so the settings are visible every time the viewer opens.

## Non-Functional Requirements

-   Backward compatible: no settings file means today's behaviour exactly.
-   Agent-agnostic: plain JSON plus prose rules in the skills; no tooling is
    required to read or obey them.
-   Same OS and browser support as the visual companion track.

## Acceptance Criteria

1.  Fresh `conductor-setup` asks the settings questions and writes a valid
    `settings.json`.
2.  With `testing.verification = track`, a new plan has no per-phase
    checkpoint tasks and ends with a Track Verification phase. With `phase`,
    plans are as today.
3.  With `git.strategy = trunk`, implement works on a track branch, rebases
    onto `origin/main` and uses `--force-with-lease --force-if-includes`, and
    never on main.
4.  Switching a setting in the viewer updates `settings.json` within one
    click, and the next skill step honours it.
5.  A project without `settings.json` behaves exactly as before this track.

## Out of Scope

-   Git Flow (long-lived `develop`/`release` branches). It could be added
    later as a third strategy.
-   Per-track overrides of project settings.
-   Configuring hosting (PR templates, branch protection, CI).

## Decisions (2026-10-19)

-   **Testing:** tests are written with the code in every task
    (`testing.style = with-task`); trying it out, feedback and iteration
    happen once at the end (`testing.verification = track`).
-   **Git notes:** a setting, `git.notes`, default `on` (upstream); `off` here.
-   **Landing on main:** the agent never does it; it stops at "branch ready".
-   **Defaults:** `git.strategy` gains a `current` option as the default, so a
    project without settings behaves exactly as upstream.
