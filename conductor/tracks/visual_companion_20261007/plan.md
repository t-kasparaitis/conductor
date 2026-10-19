# Implementation Plan: Visual Companion

> A throwaway spike of the viewer already exists (uncommitted) so this plan can
> be reviewed *in* the viewer. Tasks below harden it properly, test-first.

## Phase 1: File Contract & Parser (diagram: architecture)

- [ ] Task: Write the file-contract reference (`skills/conductor-view/references/file-contract.md`)
    - [ ] Document `feedback.md` item format (id, status, kind, target, body, agent reply)
    - [ ] Document `diagrams/*.json` schema and `(diagram: slug)` references
- [ ] Task: Write failing tests for the plan parser
    - [ ] Phases from `##` headings, including `[checkpoint: sha]`
    - [ ] Tasks and sub-tasks with `[ ]`, `[~]`, `[x]` and trailing SHAs
    - [ ] Notes and blank lines between tasks are preserved, not mis-parsed
- [ ] Task: Implement the plan parser to pass the tests
- [ ] Task: Write failing tests for registry, metadata, feedback and diagram loading
    - [ ] Malformed `metadata.json` / diagram JSON degrades to a visible error, never a crash
- [ ] Task: Implement the loaders to pass the tests
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Local Server

- [ ] Task: Write failing tests for the HTTP API
    - [ ] `GET /api/state` and `GET /api/version` shapes
    - [ ] `POST /api/feedback` appends a well-formed item
    - [ ] Path traversal and unknown track ids are rejected with 400/404
    - [ ] Server refuses to bind anything but `127.0.0.1`
- [ ] Task: Implement `serve.py` (stdlib `http.server`) to pass the tests
- [ ] Task: Write failing tests for persistence: atomic write, LF on all OSes, 10 concurrent POSTs → 10 distinct ids
- [ ] Task: Implement locked, atomic, LF-only feedback writes to pass the tests
- [ ] Task: Port reuse — detect an existing viewer for the same root via `/api/ping`
- [ ] Task: `--export` single-file read-only snapshot, with test
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Viewer UI

- [ ] Task: Track list, header and phase rail with live polling of `/api/version`
- [ ] Task: Plan tab — phases, tasks, sub-tasks, SHAs, checkpoints
- [ ] Task: Spec tab — safe Markdown renderer (escape first), per-section comments
- [ ] Task: Feedback composer on phases/tasks/sections; Approve / Request changes
- [ ] Task: Feedback tab — open/resolved items with agent replies
- [ ] Task: Workflow settings page and header chips (shared with track `workflow_settings_20261017`)
- [ ] Task: Zero-runtime fallback — open from disk, folder picker, read-only render, "Copy feedback" for chat
- [ ] Task: Accessibility & theming pass (keyboard, focus, contrast, light/dark)
- [ ] Task: Cross-browser pass — Chrome, Edge, Firefox, Safari
    - [ ] Audit CSS/JS against support tables; remove anything not in all four
    - [ ] Wheel/trackpad/touch behaviour on each browser (Firefox line-mode deltas, Safari pinch)
    - [ ] Page works with `localStorage` blocked (private windows)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: World-Map Diagrams (diagram: world-map)

- [ ] Task: Write failing tests for auto-layout (layered ranks, cycles, regions)
- [ ] Task: Implement auto-layout to pass the tests
- [ ] Task: Canvas modal — pan (drag/keys), zoom at cursor, fit, grid background
- [ ] Task: Minimap with viewport rectangle and click/drag travel
- [ ] Task: Node detail panel, connection fly-to, guided tour controls
- [ ] Task: Sandboxed raw-SVG diagrams in the same canvas
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5: Agent Instructions & Integration (diagram: feedback-loop)

- [ ] Task: Write `skills/conductor-view/SKILL.md` (start/reuse server, missing-Python detection and fallback, contract, when to diagram, feedback processing)
- [ ] Task: Add conditional "Visual companion" hooks to new-track, implement, review and status skills
- [ ] Task: README — Visual companion section and update "Changes from upstream"
- [ ] Task: CI — Python tests on Ubuntu, macOS, Windows × Python 3.9 and latest; assert new skill links
- [ ] Task: CI — Playwright e2e (Chromium, Firefox, WebKit; Edge on Windows): load plan, live update, comment round-trip, open map, pan/zoom, tour
- [ ] Task: Manual smoke test on real macOS (Safari) and Windows (Edge, `py -3`) before release
- [ ] Task: End-to-end run with Codex CLI and Claude Code (start, diagram, feedback round-trip)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
