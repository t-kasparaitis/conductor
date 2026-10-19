# Spec: Home page and multi-project viewer

## Overview

Today the viewer serves one project, `http://127.0.0.1:4177/` jumps straight
into the first track, and archived tracks are invisible. This track adds a
**home page** at that root URL that lists **every Conductor project you have
registered** and each project's tracks: what's being worked on now, what's
new, what's done and what's archived. From there you open any track, or ask
the agent to archive, restore or delete one.

It has to work for anyone who clones the repo: no install step, no config to
write by hand, and it keeps working with one project or many.
(diagram: home-architecture)

## Functional Requirements

### 1. One viewer, many projects

-   **One viewer per machine.** A single `serve.py` serves every registered
    project. Starting it with `--root <project>` when a viewer is already
    running doesn't start a second one: it registers that project with the
    running viewer, prints the project's URL and exits.
-   **Project registry**, a user-level file `projects.json` in the viewer's
    config folder (not inside any repo):
    -   Linux: `$XDG_CONFIG_HOME/conductor-view/` (default `~/.config/conductor-view/`)
    -   macOS: `~/Library/Application Support/conductor-view/`
    -   Windows: `%APPDATA%\conductor-view\`
    -   Overridable with the `CONDUCTOR_VIEW_HOME` environment variable (also
        how tests stay out of your real registry).
-   **Finding projects automatically:**
    -   Every time the viewer is started for a project (`--root`), that
        project is registered. Agents start it through the `conductor-view`
        skill, so projects you use Conductor in show up on their own.
    -   **Find projects** on the home page scans folders you choose (default:
        your home folder) for `conductor/index.md`, a few levels deep,
        skipping `.git`, `node_modules`, virtualenvs and hidden folders. It
        lists what it found; you tick the ones to add.
    -   **Add by path:** paste a folder path on the home page, or run
        `serve.py --add <path>`.
-   **Removing** a project only forgets it (`serve.py --forget <path>` or
    the home page). Its files are never touched. A registered project whose
    folder has gone missing stays listed as "not found" with a Forget
    button, instead of silently disappearing.
-   A folder is accepted only if it contains `conductor/index.md`.

### 2. Home page (`#/`)

-   **Project cards**, the active project first, then by most recent
    activity. Each card shows the name (folder name), path, current git
    branch, a one-line settings summary (e.g. `trunk · commit per task ·
    tests with each task`), and counts of tracks by status.
-   **Tracks inside each card**, grouped:
    1.  **Now:** tracks with a task in progress (`[~]`), highlighted, with
        the current task's name.
    2.  **In progress / New:** the rest of the registry's open tracks.
    3.  **Done:** tracks marked `[x]` in the registry.
    4.  **Archived:** that project's own `conductor/archive/`, collapsed by
        default. Archives are per repo and are never pooled across projects;
        the Archived filter on the home page still shows each one under its
        project.
-   **Each track row:** title, type, a progress bar split by phase (the same
    one the track page uses), done/total tasks, open feedback count, spec and
    plan approval state (approved / changes requested / waiting), the track's
    branch if it exists, and last activity (the newest commit touching the
    track folder, or the newest file change when git isn't available).
    Clicking the row opens the track.
-   **Search and filters:** one search box (track title or id, across all
    projects) and status chips (Now, Open, Done, Archived). The filter lives
    in the URL, so `#/?status=archived` is a link you can keep.
-   **Archived tracks open read-only** (no comment buttons), with a banner.
-   A **project switcher** in the header on every page; track URLs carry the
    project: `#/<project>/<track_id>/plan/phase-2`. Old links without a
    project (`#/<track_id>/...`) still work when the track id is unique.

### 3. Git safety state

Deleting a committed track folder doesn't lose history (git keeps it), but
uncommitted or unpushed work can be lost. So every track shows where its
work stands in git:

-   **Saved state badge** on each row, worst case shown:
    -   **Uncommitted:** files in the track folder have changes not yet
        committed (`git status --porcelain -- <folder>`).
    -   **Not pushed:** the track's branch has commits that are on no remote
        branch, or has never been pushed.
    -   **Pushed:** everything is committed and on the remote.
    -   **Landed:** the branch is merged into `main`.
    -   **No git:** the project isn't a git repo; nothing is protected.
-   **Before a delete or archive**, the confirm dialog asks the server for
    the track's full git state (on demand, not on every refresh) and spells
    it out: e.g. "2 uncommitted files in this track would be lost",
    "branch `x` has 4 commits that exist only on this machine", or "Safe:
    committed, pushed and landed; history stays in git". Unsafe states turn
    the Delete button into "Delete anyway".
-   **The agent checks again** before acting on a delete or archive request,
    reports the same facts in chat, and won't delete uncommitted work
    without your explicit OK.
-   Cost: one `git status` and one `git for-each-ref` per changed project per
    refresh; the detailed per-track check only runs when a dialog opens.
    Git is read-only here: the viewer never commits, pushes or fetches.
    "Pushed" is as of the last fetch, and the dialog shows when that was.

### 4. Archive, restore and delete: the viewer asks, the agent does

-   Each track row has a menu: **Archive**, **Restore** (archived tracks) and
    **Delete**.
-   The button adds a request item to that track's `feedback.md` (kinds
    `archive`, `restore`, `delete`, target `track`). The browser never moves
    or deletes folders.
-   Delete first asks you to type the track id to confirm.
-   Until the agent acts, the row shows "Archive requested, waiting for the
    agent", and you can withdraw the request.
-   The agent processes it on your next message, using the same steps as the
    review skill's Track Cleanup: move to `conductor/archive/<track_id>/` (or
    back), update `tracks.md`, commit. For **delete** it asks once more in
    chat before deleting, because deletion can't be undone.

### 5. What is per-repo, and what is shared

-   **Always per-repo:** tracks, the archive, feedback, diagrams and the
    project's context files. They live inside each repo's `conductor/` and
    are never mixed. Track ids can repeat across repos, so every URL, API
    call and request names the project as well as the track.
-   **Workflow settings in two layers:**
    1.  **Conductor-wide defaults:** `settings.json` in the viewer's config
        folder (next to `projects.json`). Personal: it applies to every
        project on this machine and never goes into a repo.
    2.  **Per-repo:** `conductor/settings.json`, committed with the repo, so
        everyone working on it shares it. It only needs the keys that differ.
    -   **Resolution, per key:** the repo's value, else the Conductor-wide
        default, else the built-in default from the schema.
-   **Main rules and exceptions:** the settings page is built around one
    set of **main rules** (the Conductor-wide defaults) and an **exception
    list**.
    -   **Main rules:** edit once, apply to every project that follows them.
    -   **Each project has a toggle:** **Follows main rules** (its repo file
        has no workflow keys) or **Has exceptions** (its repo file sets some
        keys).
    -   **The exception list** shows only the projects that deviate, and for
        each one only the settings that differ, side by side with the main
        rule, e.g. `baseline-os · git.strategy: feature-branch (main rule:
        trunk)`. Each exception has **Use main rule**, which removes that
        key; the last one removed turns the project back to Follows main
        rules.
    -   **Adding an exception:** from a project's settings, change any value;
        only that key is written to the repo file.
    -   **Existing repos with a full `settings.json`** (every repo set up
        before this track, this one included): keys that equal the main rule
        are shown as "same as main rule" with a one-click **Tidy** that
        removes them, so only real exceptions remain. Nothing is removed
        without that click, because the file may be shared with
        collaborators.
    -   Every value on a track or project page shows where it comes from
        ("this repo's exception", "main rules", "built-in"). The home page
        card shows "follows main rules" or "N exceptions".
-   **For agents:** skills read `conductor/settings.json` first, then the
    Conductor-wide file for missing keys, then the schema defaults. The
    paths per OS go in the file contract. An agent that can't read outside
    the repo (a sandbox) uses the repo file and the built-in defaults, and
    says so. `conductor-setup` offers the Conductor-wide defaults as the
    starting choice for a new repo: **follow the main rules** (writes no
    workflow keys) or **set exceptions** (writes only the keys you change).
-   **Workflow settings changes are still announced:** `--watch` reports a
    change in either layer, naming the project(s) it affects.

### 6. Port

-   **Default stays 4177.** Nothing common uses it.
-   **Changing it**, highest priority first:
    1.  `serve.py --port 5000`
    2.  `CONDUCTOR_VIEW_PORT=5000`
    3.  `"port": 5000` in `config.json` next to `projects.json`
    4.  4177
-   **In the viewer:** the settings page shows the port in use and where it
    came from, and lets you set the saved port (written to `config.json`).
    The change applies the next time the viewer starts; the page says so and
    gives the restart command.
-   If the chosen port is busy, it still moves to the next free one and says
    so.

## Non-Functional Requirements

-   Same rules as the visual companion: Python 3.9+ standard library only,
    vanilla JS, Linux/macOS/Windows, Chrome preferred and Firefox second.
-   **Security:** still bound to `127.0.0.1` only, with the Host and
    same-origin checks. The browser refers to projects by an id the server
    gave it, never by path, except in "Add by path". The server only reads
    inside registered projects' `conductor/` folders, and only writes
    `feedback.md`, `conductor/settings.json` and its own `projects.json` and
    `config.json`.
-   **Persistence:** the viewer's own files (`projects.json`, `config.json`
    and the main-rules `settings.json`) survive restarts and are written
    atomically: the new content goes to a temporary file that then replaces
    the old one in one step, so a crash or power cut mid-write leaves the
    old file or the new one, never half of each.
-   **When one of those files can't be read** (for example you edited it
    by hand and left a stray comma, so it isn't valid JSON any more):
    -   The viewer doesn't overwrite it. If it did, the next save would
        replace your list of projects with an empty one and they'd be gone.
    -   Instead it renames the file, e.g. `projects.json` →
        `projects.json.bad-2026-10-19T1902`, starts with an empty list (or
        default config), and shows a banner on every page: "Couldn't read
        projects.json (line 4: expected ',' ). Your old file is saved as
        projects.json.bad-…; fix it and click Restore, or re-add projects."
    -   **Restore** re-reads the `.bad` file and, if it is valid now, puts it
        back. Nothing is ever deleted; old `.bad` copies stay until you
        remove them.
    -   The same rule covers `config.json` and the main-rules
        `settings.json`. A repo's own `conductor/settings.json` is not
        renamed: the viewer shows its error and leaves the file for you or
        the agent to fix, as it does today.
-   **Many repos at once:** there is no limit on how many projects are
    registered, and agents may be working in several at the same time.
    -   The home page loads within a second for 50 projects of 20 tracks
        each. Each project's summary is cached and rebuilt only when that
        project's files change.
    -   The live poll only re-reads the project you're looking at (on the
        home page: only projects whose files changed). Git is called at most
        once per changed project, and the page still works without git.
    -   Writes from several agents and tabs to different repos never block
        each other. Writes to the same file keep today's
        re-read-and-compare rule.
    -   `--watch` can follow one project (`--root`) or all registered
        projects (`--all`), labelling every line with the project.
-   **No-Python mode** (`index.html` opened directly): the home page shows
    the one picked project, including its archive; requests are copied for
    pasting to the agent, like comments. `--export` includes the home page
    for the exported project.

## Acceptance Criteria

1.  Starting the viewer in project A, then running the start command in
    project B, leaves one viewer running whose home page lists both.
2.  **Find projects** in a folder containing three Conductor projects lists
    all three and adds the ticked ones.
3.  A track moved to `conductor/archive/` shows under Archived, opens
    read-only, and Restore files a `restore` request.
4.  Clicking Archive writes an `archive` request to `feedback.md`; after the
    agent archives the track and resolves it, the home page moves the track
    to Archived within about two seconds.
5.  `--port`, `CONDUCTOR_VIEW_PORT` and `config.json` each change the port,
    in that order of priority, and the settings page shows which one won.
6.  Old `#/<track_id>/...` links still open the right track.
7.  A main rule applies to every project without that key; a project with
    an exception shows up in the exception list with only the differing
    keys; "Use main rule" removes the key; Tidy removes keys equal to the
    main rule and nothing else. The settings page shows the source of each
    value.
8.  Ten registered projects with agents editing two of them at once: the
    home page shows both sets of changes within about two seconds and only
    re-reads those two projects.
9.  A track with an uncommitted file, one with an unpushed branch and one
    that is pushed and landed each show the right badge, and the delete
    dialog for the first two warns and names what would be lost.
10. Every new parser and loader in `serve.py` has a matching `local.js`
    version, checked by the parity tests.

## Out of Scope

-   Running more than one viewer on purpose, or reaching it from another
    machine.
-   The browser starting agents, running git, or deleting files itself.
-   Creating new tracks from the home page (that stays a chat with the
    agent).
