# Implementation Plan: Visual Companion

> Planned under: trunk, commit per task, push: ask, no git notes, tests with
> each task, verification at track end. A working spike of the viewer is
> already committed (`258f462`) and recorded as Phase 1; the remaining
> phases harden it, each task with its tests.
> Re-planned 2026-10-19 from the original test-first, checkpoint-per-phase plan.

## Phase 1: Working Spike (already built)

- [x] Task: Local server — stdlib only, `127.0.0.1`, live updates, feedback API, port reuse, `--open`, `--export` 258f462
- [x] Task: Viewer — tracks, phase rail, plan, spec, feedback composer, approve / request changes, light/dark 258f462
- [x] Task: World-map diagrams — pan, zoom at cursor, minimap, fly-to, guided tour, deep links 258f462
- [x] Task: Draft `SKILL.md` for agents, the every-turn feedback check and `--watch` 258f462
- [x] Task: Workflow settings page and header chips (with track `workflow_settings_20261017`) 258f462

## Phase 2: File Contract & Parsers (diagram: architecture)

- [x] Task: Write the file-contract reference (`skills/conductor-view/references/file-contract.md`): `feedback.md` items, `diagrams/*.json`, `(diagram: slug)` references 6a35738
- [x] Task: Plan parser, with tests: phases, `[checkpoint: sha]`, tasks/sub-tasks in all three states, one or more trailing SHAs, notes between tasks 47fdb48
- [x] Task: Registry, metadata, feedback and diagram loaders, with tests: malformed JSON or Markdown shows a visible error, never a crash d0ee84e

## Phase 3: Local Server

- [x] Task: HTTP API, with tests: `/api/state` and `/api/version` shapes, `POST /api/feedback` round-trip, bad track ids and traversal rejected, bad `Content-Length` handled, bound to `127.0.0.1` only eedfe11
- [x] Task: Persistence, with tests: atomic writes, LF on every OS, 10 concurrent posts → 10 distinct ids, nothing lost if the browser posts while an agent edits the file 754c07b
- [x] Task: Port reuse and `--export`, with tests 5091d11
- [x] Task: `--watch`, with tests: already-open items first, then new ones, settings changes; survives a half-written file 4c2278d

## Phase 4: Viewer UI

- [x] Task: Frozen overview and focus mode (FB-002) — the track header, progress groups and tabs stay pinned at the top; clicking a phase or task shows just that phase instead of scrolling a long page, with an "All phases" switch a336d97
- [x] Task: Zero-runtime fallback — open from disk, folder picker, read-only render, "Copy feedback" for chat a1b8f70
- [x] Task: Accessibility and theming pass (keyboard, focus, contrast, light/dark, works with `localStorage` blocked) 84e55b5
- [x] Task: Cross-browser audit — Chrome, Edge, Firefox, Safari: CSS/JS against support tables; wheel, trackpad and touch behaviour b6dc161

## Phase 5: World-Map Diagrams (diagram: world-map)

- [x] Task: Extract auto-layout into a pure function, with tests (layered ranks, cycles, regions, manual coordinates) e705673
- [x] Task: Sandboxed raw-SVG diagrams in the same canvas 5406b3c

## Phase 6: Agent Instructions & Integration (diagram: feedback-loop)

- [x] Task: Finish `skills/conductor-view/SKILL.md` (missing-Python detection and fallback, contract link) 5405f75
- [x] Task: Conditional "Visual companion" hooks in the new-track, implement, review and status skills 4b9acaf
- [x] Task: README — Visual companion section and "Changes from upstream" e470aa0
- [x] Task: CI — browser tests in Chrome, Firefox and Edge on Linux, macOS and Windows, with standard-library drivers instead of Playwright (see tech-stack.md); Safari isn't automated 9b00e94

## Phase 7: Track Verification

- [~] Task: Run the full suite, locally and in CI on Linux, macOS and Windows (needs a push — ask first)
    - [x] Locally on Linux: 139 tests pass in Chrome; in Firefox all pass except 7 skipped Chrome-only checks
    - [ ] CI on Linux, macOS and Windows (waiting for permission to push)
- [x] Task: End-to-end run with Codex CLI and Claude Code: start, diagram, feedback round-trip (Codex uses your account — ask first)
    - [x] Codex CLI 0.150 in a throwaway project: couldn't open a socket in its sandbox, so it gave the start command as the skill says; resolved a `revise` item correctly; drew a valid 7-node diagram with a tour and linked it from the plan
    - [x] Claude Code: the scenario agents and this session
- [x] Task: Feedback round 1 — edge labels no longer run under nodes (column gaps fit the longest label; labels slide along the curve to clear nodes); big maps open at a readable zoom from their left edge; Codex's diagram kept as a test fixture 69d704b
- [ ] Task: Manual smoke test on real Windows (Edge, `py -3`) — needs you or a machine. No Mac is available, so Safari stays audited but untested (README says so)
- [~] Task: Try it with the user, iterate on feedback, sign-off (Refer to workflow.md)
