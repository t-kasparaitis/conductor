# Feedback

### FB-001 · resolved · comment
- **Target:** plan › Phase 1: Track summaries and the archive › Load archived tracks from `conductor/archive/` and mark them read-only, with loader tests
- **When:** 2026-10-19 18:59

Note, with introduction of projects/repos we have no idea how many different repos could be going on at once. Some things like tracks need to be per-repo, and also workflow settings need to be applied either for conductor overall or set per-repo as well.

> **Agent:** Agreed, added to the spec as section 4 and to the plan. Tracks, archive and feedback stay strictly per repo, and every link names the project, since track ids can repeat. Workflow settings get two layers: Conductor-wide defaults (personal, in your config folder) and per-repo overrides (committed, shared with the repo), resolved per key, with the settings page showing where each value comes from and a reset-to-inherit. For many repos at once: no project limit, per-project caching so only changed projects are re-read, and `--watch --all` follows every project.

### FB-002 · resolved · comment
- **Target:** plan › Phase 1: Track summaries and the archive › Last activity and branch: one `git log` per project, falling back to file times without git, with tests for both
- **When:** 2026-10-19 19:00

I think git tracking would be good, like if we are about to delete an archived project for example. Is it already in git and commited/pushed or not, because then we'd be losing some history would be good to know.

> **Agent:** Added as spec section 3, "Git safety state". Every track row gets a badge (Uncommitted / Not pushed / Pushed / Landed / No git), and the archive and delete dialogs run a detailed check and spell out what would be lost (uncommitted files, commits that exist only on this machine), switching to "Delete anyway" when it's unsafe. The agent re-checks before acting and won't delete uncommitted work without your OK. A committed and pushed track loses nothing on delete: its history stays in git. The viewer only reads git; it never commits, pushes or fetches.

### FB-003 · resolved · comment
- **Target:** plan › Phase 1: Track summaries and the archive › Load archived tracks from `conductor/archive/` and mark them read-only, with loader tests
- **When:** 2026-10-19 19:01

Archived tracks should be per project/repo, and we have to keep in mind workflow settings in general now may need a toggle of if you apply them to all conductor repos or have specific per-repo/project settings that people tune. I think an exception list here would work well for anything that doens't follow the main rules.

> **Agent:** Yes to both. Archives are per repo (each project's own `conductor/archive/`), never pooled; the home page's Archived filter still shows them under their project. Settings are now framed exactly as you describe: one set of **main rules** for all Conductor repos, a per-project toggle **Follows main rules / Has exceptions**, and an **exception list** that shows only the projects and keys that differ from the main rules, each with "Use main rule". Repos that already have a full `settings.json` (like this one) get a one-click Tidy that strips keys equal to the main rules, never automatic, since the file may be shared. Spec section 5 and the plan are updated.

### FB-004 · resolved · comment
- **Target:** plan › Phase 2: Project registry and port › Config folder per OS and `CONDUCTOR_VIEW_HOME`; atomic `projects.json` and `config.json`; corrupt files kept as `.bad`, with tests
- **When:** 2026-10-19 19:02

What does corrupt files kept as .bad mean? elaborate in the spec

> **Agent:** Spelled out in the spec's Persistence section. If one of the viewer's own files (`projects.json`, `config.json`, main-rules `settings.json`) can't be read, say after a hand edit left invalid JSON, the viewer must not save over it, or your project list would be replaced by an empty one. So it renames it to `projects.json.bad-<time>`, starts empty, and shows a banner with the exact error and a Restore button that puts the fixed file back. Nothing is deleted. A repo's own `conductor/settings.json` is never renamed; its error is just shown, as today.

### FB-005 · resolved · approve
- **Target:** plan
- **When:** 2026-10-19 19:03

looks good, we can iterate more after it is fleshed out and it's easy to see what needs work

> **Agent:** Thanks, starting implementation with Phase 1. I'll commit task by task and come back once the home page is usable enough to iterate on.

### FB-006 · resolved · comment
- **Target:** plan › Phase 6: Track Verification › Try it with the user across this repo and the user's other Conductor projects, iterate on feedback, sign-off (Refer to workflow.md)
- **When:** 2026-10-20 01:46

I like how tracks appear on the left-hand side, and maybe we can have some way to make it clear whether they are archived etc. Obviously if you have a lot of projects it doesn't work well. But how they are listed on the main page i don't like. is there other ways of listing them out we could try? Even a table format more like excel with filters so you can show hide ones you want to see works. And then left-hand side can be something like where we have ones we 'bookmark' or save to show for quick reference. By default any new track we start shows up there and any complete track disappears, something like that.

> **Agent:** Done, try it now. **Home is a table**: one row per track across all projects, Now first. Click a header to sort; the funnel icons on Project, Status and Git (and Type, if you show that column) open spreadsheet-style checkbox filters with counts. **Columns** shows or hides columns (Spec/plan, Branch and Type start hidden to fit a laptop screen). Archived tracks are hidden until you tick Archived under Status or click the Archived chip. Filters are in the link, so they survive a reload; sort and columns are remembered by the browser. **Cards** (top right) is the old layout if you want to compare. **Sidebar = pinned tracks**: new and open tracks are pinned automatically and drop off once done or archived. The ☆ on any row, sidebar entry or track page pins or unpins it, and that choice sticks (in `pins.json` in your config folder). Each sidebar entry has a Now/Open/Done/Archived badge, and so does each track in a project's own list. Commits 38d9324, b02cfd7, 83b82d4.

### FB-007 · resolved · comment
- **Target:** plan › Phase 6: Track Verification › Try it with the user across this repo and the user's other Conductor projects, iterate on feedback, sign-off (Refer to workflow.md)
- **When:** 2026-10-20 02:30

Looks okay, just an issue with the pinned stuff is duplicating tracks showing now, so that's a bit weird, have to fix that

> **Agent:** Fixed in d1880f8. Inside a project, the sidebar listed pinned tracks under Pinned and then again in the project's track list. Now each track appears once: pinned ones under Pinned, and the project's list (now called "Other tracks") holds only the rest, with archived ones collapsed. Note: your three Conductor tracks are currently *unpinned* (saved in `pins.json`), probably from working around the duplicates, so Pinned looks empty. Click ☆ on each one to pin it again, or tell me and I'll clear those three entries.
