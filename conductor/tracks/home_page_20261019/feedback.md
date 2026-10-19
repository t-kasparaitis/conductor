# Feedback

### FB-001 · resolved · comment
- **Target:** plan › Phase 1: Track summaries and the archive › Load archived tracks from `conductor/archive/` and mark them read-only, with loader tests
- **When:** 2026-10-19 18:59

Note, with introduction of projects/repos we have no idea how many different repos could be going on at once. Some things like tracks need to be per-repo, and also workflow settings need to be applied either for conductor overall or set per-repo as well.

> **Agent:** Agreed, added to the spec as section 4 and to the plan. Tracks, archive and feedback stay strictly per repo, and every link names the project, since track ids can repeat. Workflow settings get two layers: Conductor-wide defaults (personal, in your config folder) and per-repo overrides (committed, shared with the repo), resolved per key, with the settings page showing where each value comes from and a reset-to-inherit. For many repos at once: no project limit, per-project caching so only changed projects are re-read, and `--watch --all` follows every project.
