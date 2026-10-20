# Feedback: visual_companion_20261007

<!-- Written by the Conductor viewer. Agents: address each `open` item, then
     change `open` to `resolved` in its heading and add a `> **Agent:** ...` reply. -->

### FB-001 · resolved · revise
- **Target:** plan
- **When:** 2026-10-19 16:19

Can you tell me why visual companion for conductor doesn't show as implemented or is that an example track that is just there? in which case we could remove it now that we have a real one.

> **Agent:** It's the real track for this viewer, not an example. It read 0% because I re-planned it to list only the remaining hardening work, and the spike you're using wasn't credited anywhere. The plan now opens with Phase 1: Working Spike (already built), 5 tasks done at 258f462, so it shows 5 of 25. The rest is hardening: tests, the zero-runtime fallback, cross-browser work, Playwright CI and the Codex run. Worth keeping.

### FB-002 · resolved · approve
- **Target:** plan
- **When:** 2026-10-19 16:34

Looks good. let's implement. One additional thing that is general - I think i prefer being able to click on the tasks and being able to swap to that piece instead of having the webpage scroll down to it (gets to be too much scrolling for later tasks and easy to get lost). It's like the high-level task pieces and overview should almost be like an always on header, similar to say a freeze panes option in excel if that makes sense.

> **Agent:** Plan approved; implementation started on branch `visual_companion_20261007`. The frozen overview and focus mode are now a task in Phase 4, done first because it changes the screen you review from.

### FB-003 · resolved · comment
- **Target:** plan › Phase 7: Track Verification › End-to-end run with Codex CLI and Claude Code: start, diagram, feedback round-trip (Codex uses your account — ask first)
- **When:** 2026-10-19 17:16

Yes we can now start the codex CLI review

> **Agent:** Done. Codex CLI 0.150 ran on a throwaway copy of a small project with the skills installed there. Its sandbox blocks listening sockets, so it gave the start command instead, exactly as the skill says. It resolved a planted `revise` item correctly and drew a valid 7-node diagram with a tour, linked from the plan. That diagram showed edge labels running under nodes; fixed in 69d704b, with Codex's diagram kept as a test fixture.

### FB-004 · resolved · comment
- **Target:** plan › Phase 7: Track Verification › Manual smoke test on real macOS (Safari) and Windows (Edge, `py -3`) — needs you or a machine
- **When:** 2026-10-19 17:16

You can use edge here, but we should prefer firefox or chrome when possible.

> **Agent:** Edge isn't installed on this machine, so I didn't install it; that's your call. The CI job runs the full browser suite in Edge on Windows once the branch is pushed. Local tests default to Chrome and also run in Firefox; I'll keep preferring those two.

### FB-005 · resolved · comment
- **Target:** plan › Phase 7: Track Verification › Manual smoke test on real macOS (Safari) and Windows (Edge, `py -3`) — needs you or a machine
- **When:** 2026-10-19 17:17

I do not have a mac so unfortunately this is a difficult test for now.

> **Agent:** Understood. Safari stays audited but untested: its missing `-webkit-` prefixes were added and the README now says Safari isn't tested on a real Mac. The plan's smoke test now covers only Windows.
