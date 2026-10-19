# Conductor

Conductor is a set of agent skills that enable **Spec-Driven Development**. 

This is a stripped-down fork of
[gemini-cli-extensions/conductor](https://github.com/gemini-cli-extensions/conductor)
(by Google, Apache-2.0). See [Changes from upstream](#changes-from-upstream). I've introduced and used conductor (at work) outside of Gemini extensively as an alternative to plan mode that is offered by other harnesses/agents.

A while ago it was a noticeable difference between sending a prompt off, and using plan mode. Conductor to me felt like plan mode elevated and so I wanted to make a personal flavor.

--------------------------------------------------------------------------------

## Install

The skills follow the [Agent Skills](https://agentskills.io) open standard
(`SKILL.md` folders), so they work in any agent that supports it — Claude Code,
Codex CLI, Gemini CLI, Cursor, Copilot, and others. There is nothing to build
or install: the agent just needs to find the `skills/` folders.

Clone it, then link the skills into the agents you use. Both scripts cover
Claude Code (`~/.claude/skills/`) and Codex CLI (`~/.agents/skills/`), and
because they link rather than copy, `git pull` or local edits are live
immediately in every agent.

**Linux (any distro) and macOS:**

```bash
git clone https://github.com/t-kasparaitis/conductor.git
cd conductor
./link.sh              # ./link.sh --remove to uninstall
```

**Windows (PowerShell):**

```powershell
git clone https://github.com/t-kasparaitis/conductor.git
cd conductor
powershell -ExecutionPolicy Bypass -File link.ps1    # add -Remove to uninstall
```

`link.ps1` uses directory junctions, which behave like symlinks but need no
admin rights or Developer Mode. Don't run `link.sh` from Git Bash on Windows —
`ln -s` there silently copies instead of linking (the script detects this and
points you to `link.ps1`).

**Any platform, no scripts:** copy the folders instead. You lose live updates —
re-copy after a `git pull`:

```bash
cp -r skills/* ~/.claude/skills/   # Claude Code
cp -r skills/* ~/.agents/skills/   # Codex CLI
```

For per-project installs, link (or copy) into the project's `.claude/skills/`
or `.agents/skills/` directory instead of the home directory.

--------------------------------------------------------------------------------

## Features

-   **Plan before you build**: Create specs and plans that guide the agent for
    new and existing codebases.
-   **Maintain context**: Ensure AI follows style guides, tech stack choices,
    and product goals.
-   **Iterate safely**: Review plans before code is written, keeping you firmly
    in the loop.
-   **Build on existing projects**: Intelligent initialization for both new
    (Greenfield) and existing (Brownfield) projects.
-   **Your repo's workflow**: trunk-based or feature branches, when to commit,
    push and test — chosen once at setup, switchable any time.
-   **See it in a browser** (optional): a local, live view of every track with
    a feedback box and pannable diagrams for hard ideas.

--------------------------------------------------------------------------------

## Usage & Lifecycle

Invoke skills by name (`/conductor-setup` in Claude Code, `$conductor-setup` in
Codex CLI) or with natural language — agents match your intent against each
skill's description ("Let's start a new track to add a login screen").

### 1. Set Up the Project (Run Once)

`conductor-setup` defines the core project context, used for everything built
afterward:

-   **Product**: users, product goals, high-level features
-   **Product guidelines**: prose style, brand messaging, visual identity
-   **Tech stack**: language, database, frameworks
-   **Workflow**: team preferences (TDD, commit strategy)
-   **Workflow settings**: how this repo branches, commits, pushes and tests
    (see [Workflow settings](#workflow-settings))

Generated artifacts: `conductor/product.md`, `conductor/product-guidelines.md`,
`conductor/tech-stack.md`, `conductor/workflow.md`,
`conductor/code_styleguides/`, `conductor/settings.json`, `conductor/tracks.md`

### 2. Start a New Track (Feature or Bug)

`conductor-new-track` initializes a **track** — a high-level unit of work —
and generates:

-   **Spec**: detailed requirements — what are we building and why?
-   **Plan**: an actionable to-do list of phases, tasks, and sub-tasks.

Generated artifacts: `conductor/tracks/<track_id>/spec.md`, `plan.md`,
`metadata.json`

### 3. Implement the Track

Once you approve the plan, `conductor-implement` works through `plan.md`,
checking off tasks as it completes them.

### Supporting skills

Command              | Description
:------------------- | :----------
`conductor-status`   | High-level overview of project and track progress.
`conductor-review`   | Reviews completed work against guidelines and the plan; appends a `Review Fixes` phase for issues found.

### Task corrections

1.  **In-flight**: notice a gap while the agent is coding — say so in chat; it
    adapts and verifies before finalizing the task.
2.  **After completion**: run `conductor-review` to audit changes, run tests,
    and track fixes in `plan.md`.
3.  **Fundamentally flawed**: discard the work with standard git tools —
    abandon the branch (cherry-picking anything worth keeping) or reset to a
    known-good commit — and start the task fresh.

### Workflow settings

`conductor/settings.json` records how this repository works. Setup asks one
question per setting (on an existing repo it suggests a branching strategy
from the git history), every skill re-reads the file before it plans,
commits, pushes or verifies, and you can change it later by hand, by asking,
or in the viewer.

Setting | Options (default first)
:------ | :----------------------
Branching | **Current branch** (upstream behaviour) · **Feature branch + merge** · **Trunk-based** (short-lived branch, rebased on `origin/main`, `push --force-with-lease --force-if-includes` on that branch only)
Commits | per task · per phase · per track
Pushing | ask first · after each phase · at track end
Git notes | on · off
Writing tests | test-first (TDD) · with each task · after implementation
Verification | after every phase · once, at track end

Whatever the settings, the agent never force-pushes or merges into `main`:
when a track is verified it stops at "branch ready" and shows you the
commands. Without a `settings.json`, Conductor behaves exactly as upstream.

### Visual companion (optional)

`conductor-view` shows your Conductor project in a local web page: tracks,
phases and tasks with live progress, the spec section by section, and
**world-map diagrams** — pannable, zoomable canvases with a guided tour, for
ideas too tangled for a list. Leave comments, request changes or approve a
spec or plan right on the page; they're saved to the track's `feedback.md`,
and the agent answers there.

Ask your agent to "open the conductor view", or run it yourself:

```bash
python3 skills/conductor-view/scripts/serve.py --root /path/to/project --open
# Windows: py -3 skills\conductor-view\scripts\serve.py --root C:\path\to\project --open
```

-   **Local only.** It binds to `127.0.0.1`, uses Python's standard library
    (3.9+), loads nothing from the internet, and writes only feedback items
    and workflow settings.
-   **Agent-agnostic.** Files are the interface: agents write Markdown and
    JSON, the page reads them. It works the same with Claude Code, Codex CLI
    or anything else that can edit files.
-   **No Python?** Open `skills/conductor-view/assets/viewer/index.html` in
    your browser and pick the project folder: a read-only view, with comments
    copied for you to paste to the agent.
-   **Share a snapshot:** `serve.py --export view.html` writes one self-contained
    read-only file.
-   Works in current Chrome, Edge, Firefox and Safari, on Linux, macOS and
    Windows. File formats are in
    [`references/file-contract.md`](skills/conductor-view/references/file-contract.md).

> **Note on token consumption:** the spec-driven approach reads and analyzes
> your project's context, specs, and plans, which increases token usage —
> especially in larger projects.

--------------------------------------------------------------------------------

## Changes from upstream

This fork keeps the core skills intact and removes everything that isn't needed
to run them as plain Agent Skills:

-   Removed Claude Code plugin/marketplace packaging (`plugin.json`,
    `.claude-plugin/`) — install is a symlink instead.
-   Removed the Antigravity-specific UI rules (`rules/`).
-   Removed the skill catalogs (`assets/catalog.md`) and the interactive
    skill-recommendation/installation steps from `conductor-setup` and
    `conductor-new-track` — the catalog was a stale, GCP-centric list with
    mostly dead links, and downloading skills via `curl` at plan time isn't
    something this fork wants.
-   Removed the `conductor-revert` skill. In practice, flawed work is better
    handled with plain git: abandon the branch (cherry-picking what's worth
    keeping) or reset to a known-good commit, then restart the task.
-   Inlined `scripts/resume.py` into the setup skill as plain instructions —
    the core skills are pure Markdown with no runtime dependencies.
-   Removed Google's `CONTRIBUTING.md`/CLA and `VERSION`.
-   Added `link.sh` (Linux/macOS) and `link.ps1` (Windows junctions) and
    rewrote this README for agent-agnostic use.

And adds:

-   **Workflow settings** (`conductor/settings.json`): branching strategy,
    commit and push cadence, git notes, and when tests are written and run,
    asked at setup and followed by every skill. A new "Current branch"
    default keeps upstream behaviour for projects without the file.
-   **Track Verification**: with verification at track end, phases run
    straight through and one final phase tries the work with you.
-   **`conductor-view`**, the optional visual companion above — the only part
    with code, all Python standard library and plain browser JavaScript.
-   **Tests** (`python3 -m unittest discover -s tests`), including real-browser
    tests in Chrome and Firefox through small standard-library drivers, run in
    CI on Linux, macOS and Windows.

--------------------------------------------------------------------------------

## Credits & License

-   Forked from [gemini-cli-extensions/conductor](https://github.com/gemini-cli-extensions/conductor),
    Copyright Google LLC.
-   Upstream in turn acknowledges Keith Ballinger's original
    [.conductor](https://github.com/keithballinger/.conductor) project as its
    groundwork.
-   License: [Apache License 2.0](LICENSE) (unchanged from upstream; see
    [NOTICE](NOTICE)).
