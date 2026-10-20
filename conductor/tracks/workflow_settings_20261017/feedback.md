# Feedback: workflow_settings_20261017

<!-- Written by the Conductor viewer. Agents: address each `open` item, then
     change `open` to `resolved` in its heading and add a `> **Agent:** ...` reply. -->

### FB-001 · resolved · approve
- **Target:** plan
- **When:** 2026-10-17 21:19

_(no message)_

> **Agent:** Plan approval received. Implementation waits until the user says to start in chat, because no commits are allowed while this is a draft.

### FB-002 · resolved · comment
- **Target:** plan › Phase 1: Branch & Schema › Create the track branch from `origin/main` (`git switch -c workflow_settings_20261017 origin/main`)
- **When:** 2026-10-17 21:49

Just a test comment. Reply if you are able to see it.

> **Agent:** Seen. Picked up by the every-turn check; the live watch detected it too but its notification had not reached the chat yet.

### FB-003 · resolved · revise
- **Target:** plan
- **When:** 2026-10-19 16:18

Where it says 16 of 18 tasks done and it has color-coding for the steps it would be nice to be able to click on the inidividual steps and go there to argue about spec etc. It would also be nice to know what falls into a larger sequence of steps. So for example maybe 5 little bars fall into a bigger bar etc., having an overhead bar for the smaller ones with color coding as well might be nice, or somehow incorporating the 1-2-3-4-5 things as wlel. But good job so far

> **Agent:** Done. The bar is now grouped by phase: each group has a numbered bar on top (green done, amber in progress, grey pending, with the name) and one segment per task below, sized by task count. Click a phase bar to jump to the phase, or a segment to jump to that task, which flashes so you can comment on it right there. Hover shows the task. Also, a change request now shows as a badge only while it's open.

### FB-004 · resolved · comment
- **Target:** plan › Phase 5: Track Verification › You try it, leave feedback in the viewer, we iterate; sign-off (Refer to workflow.md)
- **When:** 2026-10-20 02:29

I think this branch looks okay, we just need the fully autoamted part worked out and it will be good to merge once complete. But i guess we might need the 2 other tracks to go with it

> **Agent:** Thanks. The remaining automated step is CI on Linux, macOS and Windows, which only runs once the branches are on GitHub, and I'm waiting for your OK to push. And yes, ship it together with the other two: `home_page_20261019` already contains both this branch and `visual_companion_20261007`. So the simplest landing is to push `home_page_20261019`, let CI run there, and merge that one branch, which lands all three tracks at once. Locally, all 274 tests pass in Chrome and Firefox. Once CI is green I'll mark the three tracks done and stop at "branch ready"; merging to main stays with you.
