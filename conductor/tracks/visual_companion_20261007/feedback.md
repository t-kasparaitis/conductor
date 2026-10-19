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
