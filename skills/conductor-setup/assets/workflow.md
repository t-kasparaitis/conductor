# Project Workflow

## Guiding Principles

1.  **The Plan is the Source of Truth:** All work must be tracked in `plan.md`
2.  **The Tech Stack is Deliberate:** Changes to the tech stack must be
    documented in `tech-stack.md` *before* implementation
3.  **Tested Work:** Every change is covered by tests, written when
    `testing.style` says (test-first by default)
4.  **High Code Coverage:** Aim for >80% code coverage for all modules
5.  **User Experience First:** Every decision should prioritize user experience
6.  **Non-Interactive & CI-Aware:** Prefer non-interactive commands. Use
    `CI=true` for watch-mode tools (tests, linters) to ensure single execution.

## Workflow Settings

Settings come in two layers. **Re-read them before you plan, commit, push or
verify**: the user can change either at any time, for example from the
Conductor viewer.

1.  `conductor/settings.json`: this repo's choices, committed and shared
    (read it from there even if `conductor/index.md` doesn't link it).
2.  The user's **main rules** for every project: `settings.json` in the
    Conductor viewer's config folder, on their machine only:
    `~/.config/conductor-view/` on Linux (or `$XDG_CONFIG_HOME/conductor-view/`),
    `~/Library/Application Support/conductor-view/` on macOS,
    `%APPDATA%\conductor-view\` on Windows, or `$CONDUCTOR_VIEW_HOME`.

For each key, use the repo's value, else the main rule, else the default
below. If you can't read outside the repo, use the repo file and the
defaults, and say so.

| Setting | Values (default first) | What it changes |
| --- | --- | --- |
| `git.strategy` | `current` · `feature-branch` · `trunk` | Where commits go and how the track's branch is integrated. See [Branching, Pushing and Landing](#branching-pushing-and-landing). |
| `git.commit` | `task` · `phase` · `track` | When you commit: after every task, at the end of each phase, or once for the whole track. |
| `git.push` | `ask` · `phase` · `track` | When you push: only after asking in chat, after each phase, or once when the track is verified. |
| `git.notes` | `on` · `off` | Whether task summaries and verification reports are attached as git notes. |
| `testing.style` | `tdd` · `with-task` · `after` | When tests are written: failing test first, alongside the code in each task, or all together in the final verification phase. |
| `testing.verification` | `phase` · `track` | When the work is tried out with the user (manual checks, feedback, iteration, sign-off): after every phase, or once at the end of the track. |

**Safety rules (always, whatever the settings):**

-   Never force-push `main`, or any branch that wasn't created for the current
    track. Only ever force-push with `--force-with-lease --force-if-includes`.
-   With `git.push = ask`, never push without asking in chat first.
-   Never land work on `main` yourself. When the track is verified, stop at
    "branch ready" and show the user the commands for their strategy.
-   A new track branch must not track `origin/main` as its upstream, so a bare
    `git push` can never reach `main`.

## Task Workflow

All tasks follow a strict lifecycle:

### Standard Task Workflow

1.  **Select Task:** Choose the next available task from `plan.md` in sequential
    order

2.  **Mark In Progress:** Before beginning work, edit `plan.md` and change the
    task from `[ ]` to `[~]`

3.  **Write the Code and Its Tests** as `testing.style` says:

    -   **`tdd`:** follow steps 4–6 below.
    -   **`with-task`:** write the implementation and its tests together in this
        task, then run the whole suite and confirm it passes. No failing-first
        step is required, but the task is not done without its tests.
    -   **`after`:** implement the task, then run the existing suite to confirm
        nothing broke. New tests are written in the Track or Phase Verification
        protocol.

4.  **Write Failing Tests (Red Phase)** *(`tdd` only)*:

    -   Create a new test file for the feature or bug fix.
    -   Write one or more unit tests that clearly define the expected behavior
        and acceptance criteria for the task.
    -   **CRITICAL:** Run the tests and confirm that they fail as expected. This
        is the "Red" phase of TDD. Do not proceed until you have failing tests.

5.  **Implement to Pass Tests (Green Phase)** *(`tdd` only)*:

    -   Write the minimum amount of application code necessary to make the
        failing tests pass.
    -   Run the test suite again and confirm that all tests now pass. This is
        the "Green" phase.

6.  **Refactor (Optional but Recommended):**

    -   With the safety of passing tests, refactor the implementation code and
        the test code to improve clarity, remove duplication, and enhance
        performance without changing the external behavior.
    -   Rerun tests to ensure they still pass after refactoring.

7.  **Verify Coverage:** Run coverage reports using the project's chosen tools.
    For example, in a Python project, this might look like: `bash pytest
    --cov=app --cov-report=html` Target: >80% coverage for new code. The
    specific tools and commands will vary by language and framework.

8.  **Document Deviations:** If implementation differs from tech stack:

    -   **STOP** implementation
    -   Update `tech-stack.md` with new design
    -   Add dated note explaining the change
    -   Resume implementation

9.  **Commit Code Changes** when `git.commit` says:

    -   **`task`:** commit now. Stage the task's files by name (never build
        output or caches such as `__pycache__/`; add them to `.gitignore` if
        missing) and use a clear, concise message, e.g. `feat(ui): Create basic HTML
        structure for calculator`.
    -   **`phase` / `track`:** don't commit yet. Mark the task `[x]` without a
        SHA and continue; the commit happens at the end of the phase or track,
        and its SHA is then appended to every task it covers.
    -   Commit only on the branch `git.strategy` says (see
        [Branching, Pushing and Landing](#branching-pushing-and-landing)).

10. **Attach Task Summary with Git Notes** (only if `git.notes` is `on`):

    -   **Step 10.1: Get Commit Hash:** Obtain the hash of the *just-completed
        commit* (`git log -1 --format="%H"`).
    -   **Step 10.2: Draft Note Content:** Create a detailed summary for the
        completed task. This should include the task name, a summary of changes,
        a list of all created/modified files, and the core "why" for the change.
    -   **Step 10.3: Attach Note:** Use the `git notes` command to attach the
        summary to the commit. `bash # The note content from the previous step
        is passed via the -m flag. git notes add -m "<note content>"
        <commit_hash>`

11. **Get and Record Task Commit SHA:**

    -   **Step 11.1: Update Plan:** Read `plan.md`, find the line for the
        completed task, update its status from `[~]` to `[x]`, and append the
        first 7 characters of the *just-completed commit's* commit hash. A
        task that changed no files (for example "Run the full suite") is
        marked `[x]` without a SHA.
    -   **Step 11.2: Write Plan:** Write the updated content back to `plan.md`.

12. **Commit Plan Update:**

    -   **Action:** Stage the modified `plan.md` file.
    -   **Action:** Commit this change with a descriptive message (e.g.,
        `conductor(plan): Mark task 'Create user model' as complete`), or
        include it in the next task's commit. Either is fine.

### Task Correction & Plan Amendment Workflows

When an implemented task or phase requires corrections, amendments, or additions, follow these standard workflows to maintain plan integrity and avoid untracked code drift:

1.  **In-Flight Refinements:** If minor gaps are found while a task is actively
    in-progress (`[~]`), make the adjustments directly in the active
    implementation stream and ensure passing tests before committing.
2.  **Code Review Corrections (`conductor-review`):** If issues are identified
    during or after a code review, instruct the agent to review your changes
    (e.g., *"run a review"* or triggering the action manually in compatible
    clients). The review agent will automatically append a `Review Fixes` phase
    to `plan.md` so that correction tasks are formally tracked and
    checkpointed.
3.  **Fundamentally Flawed Work:** If a task implementation is fundamentally
    flawed or needs to be redone, discard it with standard git tools instead of
    patching on top of it — abandon the branch (optionally cherry-picking any
    commits worth keeping) or reset to a known-good commit, then set the
    affected task states in `plan.md` back to pending `[ ]` and restart cleanly.

### End of a Phase

When a task completes a phase in `plan.md`:

1.  Run the full automated test suite. If it fails, fix it before going on.
2.  If `git.commit` is `phase`, commit the phase's work now.
3.  With `git.strategy = trunk`, rebase the track branch onto `origin/main`
    and re-run the suite (see [Branching, Pushing and Landing](#branching-pushing-and-landing)).
4.  If `testing.verification` is `phase`, run the **Phase Completion
    Verification and Checkpointing Protocol** below. If it is `track`, tell the
    user the phase is done in one line and continue with the next phase
    without waiting.
5.  If `git.push` is `phase`, push the track branch (after the user's sign-off
    when step 4 ran the protocol) (see
    [Branching, Pushing and Landing](#branching-pushing-and-landing)).

### Phase Completion Verification and Checkpointing Protocol

**Trigger:** A phase has ended and `testing.verification` is `phase`.

1.  **Announce Protocol Start:** Inform the user that the phase is complete and
    the verification and checkpointing protocol has begun.

2.  **Ensure Test Coverage for Phase Changes:**

    -   **Step 2.1: Determine Phase Scope:** To identify the files changed in
        this phase, you must first find the starting point. Read `plan.md` to
        find the Git commit SHA of the *previous* phase's checkpoint. If no
        previous checkpoint exists, the scope is all changes since the
        track's first commit.
    -   **Step 2.2: List Changed Files:** Execute `git diff --name-only
        <previous_checkpoint_sha> HEAD` to get a precise list of all files
        modified during this phase.
    -   **Step 2.3: Verify and Create Tests:** For each file in the list:
        -   **CRITICAL:** First, check its extension. Exclude non-code files
            (e.g., `.json`, `.md`, `.yaml`).
        -   For each remaining code file, verify a corresponding test file
            exists.
        -   If a test file is missing, you **must** create one. Before writing
            the test, **first, analyze other test files in the repository to
            determine the correct naming convention and testing style.** The new
            tests **must** validate the functionality described in this phase's
            tasks (`plan.md`).

3.  **Execute Automated Tests with Proactive Debugging:**

    -   Before execution, you **must** announce the exact shell command you will
        use to run the tests.
    -   **Example Announcement:** "I will now run the automated test suite to
        verify the phase. **Command:** `CI=true npm test`"
    -   Execute the announced command.
    -   If tests fail, you **must** inform the user and begin debugging. You may
        attempt to propose a fix a **maximum of two times**. If the tests still
        fail after your second proposed fix, you **must stop**, report the
        persistent failure, and ask the user for guidance.

4.  **Propose a Detailed, Actionable Manual Verification Plan:**

    -   **CRITICAL:** To generate the plan, first analyze `product.md`,
        `product-guidelines.md`, and `plan.md` to determine the user-facing
        goals of the completed phase.
    -   You **must** generate a step-by-step plan that walks the user through
        the verification process, including any necessary commands and specific,
        expected outcomes.
    -   The plan you present to the user **must** follow this format:

        **For a Frontend Change:** ``` The automated tests have passed. For
        manual verification, please follow these steps:

        **Manual Verification Steps:** 1. **Start the development server with
        the command:** `npm run dev` 2. **Open your browser to:**
        `http://localhost:3000` 3. **Confirm that you see:** The new user
        profile page, with the user's name and email displayed correctly. ```

        **For a Backend Change:** ``` The automated tests have passed. For
        manual verification, please follow these steps:

        **Manual Verification Steps:** 1. **Ensure the server is running.** 2.
        **Execute the following command in your terminal:** `curl -X POST
        http://localhost:8080/api/v1/users -d '{"name": "test"}'` 3. **Confirm
        that you receive:** A JSON response with a status of `201 Created`. ```

5.  **Await Explicit User Feedback:**

    -   After presenting the detailed plan, ask the user for confirmation:
        "**Does this meet your expectations? Please confirm with yes or provide
        feedback on what needs to be changed.**"
    -   **PAUSE** and await the user's response. Do not proceed without an
        explicit yes or confirmation.

6.  **Identify Target Commit for Report:**

    -   Do NOT create a new empty commit for checkpointing.
    -   Identify the hash of the last functional commit made during this phase. This will be the target for the verification report.

7.  **Attach Auditable Verification Report using Git Notes** (only if
    `git.notes` is `on`):

    -   **Step 7.1: Draft Note Content:** Create a detailed verification report
        including the automated test command, the manual verification steps, and
        the user's confirmation.
    -   **Step 7.2: Attach Note:** Use the `git notes` command to attach the full report to the target commit identified in step 6.

8.  **Get and Record Phase Checkpoint SHA:**

    -   **Step 8.1: Get Commit Hash:** Use the hash of the commit identified
        in step 6 (the last functional commit of the phase).
    -   **Step 8.2: Update Plan:** Read `plan.md`, find the heading for the
        completed phase, and append the first 7 characters of the commit hash in
        the format `[checkpoint: <sha>]`.
    -   **Step 8.3: Write Plan:** Write the updated content back to `plan.md`.

9.  **Commit Plan Update:**

    -   **Action:** Stage the modified `plan.md` file.
    -   **Action:** Commit this change with a descriptive message following the
        format `conductor(plan): Mark phase '<PHASE NAME>' as complete`.

10. **Announce Completion:** Inform the user that the phase is complete and the
    checkpoint has been created (with the verification report attached as a
    git note, if notes are on).

### Track Verification Protocol

**Trigger:** `testing.verification` is `track` and every phase before the
final **Track Verification** phase is done. Plans written under this setting
end with that phase; this protocol is how its tasks are carried out.

It is the Phase Completion protocol above, scoped to the whole track:

1.  **Scope:** every file changed since the track's branch point
    (`git merge-base HEAD origin/main`, or the first commit of the track with
    `git.strategy = current`).
2.  **Tests:** if `testing.style` is `after`, write the tests for the whole
    track now. With any style, make sure every changed code file has tests.
3.  **Run** the full suite under the same two-attempt rule.
4.  **Try it with the user:** present one manual verification plan for the
    whole track, then wait. The user tries it, gives feedback (in chat, or in
    the Conductor viewer if it is in use) and you iterate: each round of fixes
    gets its own task under the Track Verification phase, tests included, and
    the suite is re-run. Repeat until the user signs off with an explicit yes.
5.  **Record:** commit any remaining work (per `git.commit`), attach the
    verification report as a git note to the last functional commit if
    `git.notes` is `on`, and mark the Track Verification phase with
    `[checkpoint: <sha>]` using that commit's SHA.
6.  **Push and hand off:** push if `git.push` is `phase` or `track`; with
    `ask`, ask once now. This is the only point where `ask` prompts on its
    own. Then stop at "branch ready" and show the user the landing commands
    for their strategy.

## Branching, Pushing and Landing

Follow the section for this project's `git.strategy`. The safety rules in
[Workflow Settings](#workflow-settings) always apply.

### `current` (default)

Commit on whatever branch is checked out. Don't create, rebase or merge
branches. Push only as `git.push` says, with a plain `git push`.

### `feature-branch`

-   **Start:** `git switch -c <track_id> main`, then
    `git branch --unset-upstream` if one was set. `conductor-new-track` does
    this when it creates the track; `conductor-implement` switches to it.
-   **Push:** `git push -u origin <track_id>`. Never force; pushed history is
    permanent.
-   **Keep up to date (optional):** `git merge origin/main` into the track
    branch. Never rebase a branch that has been pushed.
-   **Branch ready:** tell the user to open a PR, or to run
    `git switch main && git pull && git merge --no-ff <track_id> && git push origin main`.

### `trunk`

-   **Start:** `git fetch origin && git switch -c <track_id> origin/main`, then
    `git branch --unset-upstream`. `conductor-new-track` does this when it
    creates the track; `conductor-implement` switches to it. Keep the branch
    short-lived.
-   **Stay current:** when you resume work on the branch, before every push,
    and at the end of each phase:
    `git fetch origin && git rebase origin/main`. Resolve conflicts commit by
    commit and re-run the suite.
-   **Push:** `git push --force-with-lease --force-if-includes origin <track_id>`
    (the rebase rewrote the branch). On the first push add `-u`.
-   **Branch ready:** tell the user to fast-forward or rebase-merge it into
    `main` (or open a PR), then delete the branch.

### Quality Gates

Before marking any task complete, verify:

-   [ ] All tests pass
-   [ ] Code coverage meets requirements (>80%)
-   [ ] Code follows project's code style guidelines (as defined in
    `code_styleguides/`)
-   [ ] All public functions/methods are documented (e.g., docstrings, JSDoc,
    GoDoc)
-   [ ] Type safety is enforced (e.g., type hints, TypeScript types, Go types)
-   [ ] No linting or static analysis errors (using the project's configured
    tools)
-   [ ] Works correctly on mobile (if applicable)
-   [ ] Documentation updated if needed
-   [ ] No security vulnerabilities introduced

## Development Commands

**AI AGENT INSTRUCTION: This section should be adapted to the project's specific
language, framework, and build tools.**

### Setup

```bash
# Example: Commands to set up the development environment (e.g., install dependencies, configure database)
# e.g., for a Node.js project: npm install
# e.g., for a Go project: go mod tidy
```

### Daily Development

```bash
# Example: Commands for common daily tasks (e.g., start dev server, run tests, lint, format)
# e.g., for a Node.js project: npm run dev, npm test, npm run lint
# e.g., for a Go project: go run main.go, go test ./..., go fmt ./...
```

### Before Committing

```bash
# Example: Commands to run all pre-commit checks (e.g., format, lint, type check, run tests)
# e.g., for a Node.js project: npm run check
# e.g., for a Go project: make check (if a Makefile exists)
```

## Testing Requirements

### Unit Testing

-   Every module must have corresponding tests.
-   Use appropriate test setup/teardown mechanisms (e.g., fixtures,
    beforeEach/afterEach).
-   Mock external dependencies.
-   Test both success and failure cases.

### Integration Testing

-   Test complete user flows
-   Verify database transactions
-   Test authentication and authorization
-   Check form submissions

### Mobile Testing

-   Test on actual iPhone when possible
-   Use Safari developer tools
-   Test touch interactions
-   Verify responsive layouts
-   Check performance on 3G/4G

## Code Review Process

### Self-Review Checklist

Before requesting review:

1.  **Functionality**

    -   Feature works as specified
    -   Edge cases handled
    -   Error messages are user-friendly

2.  **Code Quality**

    -   Follows style guide
    -   DRY principle applied
    -   Clear variable/function names
    -   Appropriate comments

3.  **Testing**

    -   Unit tests comprehensive
    -   Integration tests pass
    -   Coverage adequate (>80%)

4.  **Security**

    -   No hardcoded secrets
    -   Input validation present
    -   SQL injection prevented
    -   XSS protection in place

5.  **Performance**

    -   Database queries optimized
    -   Images optimized
    -   Caching implemented where needed

6.  **Mobile Experience**

    -   Touch targets adequate (44x44px)
    -   Text readable without zooming
    -   Performance acceptable on mobile
    -   Interactions feel native

## Commit Guidelines

### Message Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

-   `feat`: New feature
-   `fix`: Bug fix
-   `docs`: Documentation only
-   `style`: Formatting, missing semicolons, etc.
-   `refactor`: Code change that neither fixes a bug nor adds a feature
-   `test`: Adding missing tests
-   `chore`: Maintenance tasks

### Examples

```bash
git commit -m "feat(auth): Add remember me functionality"
git commit -m "fix(posts): Correct excerpt generation for short posts"
git commit -m "test(comments): Add tests for emoji reaction limits"
git commit -m "style(mobile): Improve button touch targets"
```

## Definition of Done

A task is complete when:

1.  All code implemented to specification
2.  Unit tests written and passing
3.  Code coverage meets project requirements
4.  Documentation complete (if applicable)
5.  Code passes all configured linting and static analysis checks
6.  Works beautifully on mobile (if applicable)
7.  Implementation notes added to `plan.md`
8.  Changes committed with proper message
9.  Git note with task summary attached to the commit (if `git.notes` is `on`)

## Emergency Procedures

### Critical Bug in Production

1.  Create hotfix branch from main
2.  Write failing test for bug
3.  Implement minimal fix
4.  Test thoroughly including mobile
5.  Deploy immediately
6.  Document in plan.md

### Data Loss

1.  Stop all write operations
2.  Restore from latest backup
3.  Verify data integrity
4.  Document incident
5.  Update backup procedures

### Security Breach

1.  Rotate all secrets immediately
2.  Review access logs
3.  Patch vulnerability
4.  Notify affected users (if any)
5.  Document and update security procedures

## Deployment Workflow

### Pre-Deployment Checklist

-   [ ] All tests passing
-   [ ] Coverage >80%
-   [ ] No linting errors
-   [ ] Mobile testing complete
-   [ ] Environment variables configured
-   [ ] Database migrations ready
-   [ ] Backup created

### Deployment Steps

1.  Land the track branch on main as `git.strategy` says (the user does this)
2.  Tag release with version
3.  Push to deployment service
4.  Run database migrations
5.  Verify deployment
6.  Test critical paths
7.  Monitor for errors

### Post-Deployment

1.  Monitor analytics
2.  Check error logs
3.  Gather user feedback
4.  Plan next iteration

## Continuous Improvement

-   Review workflow weekly
-   Update based on pain points
-   Document lessons learned
-   Optimize for user happiness
-   Keep things simple and maintainable
