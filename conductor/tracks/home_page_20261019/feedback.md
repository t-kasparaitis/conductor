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
