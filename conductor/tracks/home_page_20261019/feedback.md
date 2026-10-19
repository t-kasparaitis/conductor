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
