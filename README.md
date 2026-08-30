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

Generated artifacts: `conductor/product.md`, `conductor/product-guidelines.md`,
`conductor/tech-stack.md`, `conductor/workflow.md`,
`conductor/code_styleguides/`, `conductor/tracks.md`

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
    the repo is now pure markdown with no runtime dependencies.
-   Removed Google's `CONTRIBUTING.md`/CLA and `VERSION`.
-   Added `link.sh` (Linux/macOS) and `link.ps1` (Windows junctions) and
    rewrote this README for agent-agnostic use.

--------------------------------------------------------------------------------

## Credits & License

-   Forked from [gemini-cli-extensions/conductor](https://github.com/gemini-cli-extensions/conductor),
    Copyright Google LLC.
-   Upstream in turn acknowledges Keith Ballinger's original
    [.conductor](https://github.com/keithballinger/.conductor) project as its
    groundwork.
-   License: [Apache License 2.0](LICENSE) (unchanged from upstream; see
    [NOTICE](NOTICE)).
