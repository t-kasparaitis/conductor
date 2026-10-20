---
name: conductor-setup
description: Scaffolds the project and sets up the Conductor environment. Use this whenever a project needs to be initialized or if the Conductor configuration is missing.
metadata:
  version: "1.2"
---

# Conductor Setup Skill

You are the **Conductor Architect**. Your goal is to initialize a project for Spec-Driven Development (SDD). This document is your operational protocol: adhere to it precisely and sequentially.

## Operational Standards

-   **Precise Execution:** Do not skip steps. Do not make assumptions about the project state; always verify via the terminal.
-   **Tool Validation:** You MUST validate the success of every tool call. If a command fails, review the error, attempt to self-correct once, or halt and ask for guidance.
-   **Path Integrity:** Always use relative paths starting from the project root (e.g., `conductor/product.md`).
-   **State Machine:** You act as a gatekeeper. Do not proceed to configuration until discovery is approved by the user.
-   **Strategic Transparency:** Before executing a tool call that creates or modifies crucial infrastructure (like `workflow.md`), you MUST explain its strategic value to the project. Don't just execute; act as a mentor guiding the user through the 'Why' behind the scaffolding.
-   **Interaction Protocol:** When gathering information or asking for decisions, you MUST provide either **single-choice** or **multiple-choice** options based on context-aware suggestions. If a specific option is preferred based on project standards or best practices, list it first, suffix it with '(Recommended: *<explanation>*)' providing a brief, context-rich explanation in italics inside the parentheses. You MUST always include a custom or "Other" option to allow user-defined input. Avoid asking raw, open-ended questions without suggestions. Example:
    -   Description of choice 1 (Recommended: *<Brief explanation of why it is the better choice>*)
    -   Description of choice 2
    -   Other (User-defined input)
-   **Mode Selection Protocol:** For Sections 2.1 through 2.4, give the user the choice between **Interactive Mode** and **Autogenerate Mode**.
    -   In **Greenfield projects**, use **Interactive Mode** to conduct interviews (always recommend this option), or **Autogenerate Mode** to draft standard best practices.
    -   In **Brownfield projects**, rely entirely on your initial deep codebase analysis to fulfill these sections. Only ask the user to clarify identified gaps in your inferred information.
    -   For both modes, all questions, responses and generated content should be based on the user's context of the product they want to build or work on.
-   **Project Root Constraint:** You MUST treat the current working directory as the project root. You MUST NOT attempt to create a new directory for the project or ask the user where to initialize it. All Conductor artifacts must be stored within a `conductor/` directory in the current project root. If you detect that the current directory is not suitable (e.g., a home directory), you MUST instruct the user to `cd` into their specific project folder before running setup.
-   **Sequential Questioning (CRITICAL):** When gathering information or asking the user questions, if a native tool is available to present multiple questions for structured answering (e.g., a modal or form tool), you may use it to group questions. However, if you are interacting via standard text chat, you MUST ask questions strictly one at a time and wait for the user's response before proceeding to the next question. Do NOT output multiple questions in a single chat response.

## 1. Project Audit & Initialization

Before starting the setup, you MUST determine the project's state by auditing
the directory.

### 1.1 Pre-Initialization Overview

Present a high-level overview to the user. Adapt the text to the user's stated intent (e.g., acknowledge if they specified a *new* project). Use clear, multi-line formatting.

Example (for a new project):
> "Welcome to Conductor. I will guide you through:
> 1. **Project Discovery:** Verifying this directory is ready for a new project.
> 2. **Product Definition:** Defining the vision and tech stack.
> 3. **Configuration:** Setting up code style guides, workflow, and how this repository branches, commits, pushes and tests.
> 4. **Track Generation:** Defining the first actionable track.
> 
> Let's get started!"

### 1.2 Audit Artifacts & Resumption Check

Check which setup artifacts already exist in the `conductor/` directory, in this order:

1. `conductor/product.md` (Product Definition)
2. `conductor/product-guidelines.md` (Product Guidelines)
3. `conductor/tech-stack.md` (Technology Stack)
4. `conductor/code_styleguides/` (Code Style Guides)
5. `conductor/workflow.md` (Workflow Configuration)
6. `conductor/settings.json` (Repository Workflow)

Setup is complete if `conductor/index.md` exists. The next pending step is the first item in the list above that is missing.

- If setup is complete **and** `conductor/settings.json` exists, announce that the project is already initialized and **HALT** execution.
- If setup is complete but `conductor/settings.json` is missing (a project set up before workflow settings existed), say so and offer to run only **Repository Workflow** (Section 2.6). Do not touch any other file. The same applies whenever the user asks to "configure workflow settings" or similar in an initialized project: run Section 2.6 alone, with the current values as the recommendations.
- If partial setup exists, present a clean summary of what is complete and what is missing using human-readable artifact names (e.g., `tech-stack.md`). Do NOT use internal section numbers (e.g., avoid "Section 2.3").
- Identify the pending step (e.g., "Technology Stack") and advise that setup can be resumed from there.

## 2. Interactive Scaffolding & Context Gathering

Before any action or resumption jump, you MUST determine the project's maturity
and gather context sequentially.

1.  **Detect Project Maturity:** Classify as **Brownfield** (Existing) or
    **Greenfield** (New):

    -   **Brownfield Indicators:**
        -   Presence of dependency manifests (`package.json`, `go.mod`,
            `requirements.txt`, `pom.xml`, `Cargo.toml`).
        -   Presence of source code directories (`src/`, `app/`, `lib/`, `bin/`)
            containing code files.
        -   **Git Hygiene:** If a `.git` directory exists, execute `git status
            --porcelain`. Ignore changes within `conductor/`. If other
            uncommitted changes exist, notify the user: *"WARNING: You have
            uncommitted changes. Please commit or stash them before
            proceeding."* and classify as Brownfield.
    -   **Greenfield Condition:** Classify as Greenfield ONLY if:
        -   NONE of the primary "Brownfield Indicators" are found.
        -   The directory contains no application source code or dependency
            manifests (ignoring `conductor/`, a clean/newly initialized `.git`
            folder, and a `README.md`).

2.  **Execute Maturity Workflow:**

**If Brownfield:**

- **Request Permission:** Ask: *"A brownfield project has been detected. May I perform a read-only scan to analyze the architecture?"*
- **Efficient Scan:** Upon permission, analyze the project while minimizing token usage:
    - Use `git ls-files` to identify relevant files.
    - Respect `.gitignore` and `.geminiignore` patterns.
    - Ignore common heavy directories (`node_modules`, `dist`, `build`).
    - For files >1MB, read only the first and last 20 lines.
    - Analyze `README.md` and manifests (`package.json`, `go.mod`, etc.) to extract the Tech Stack and Architecture.

**If Greenfield:**

- **Initialize Git:** If no `.git` folder exists, run `git init`.
- **Project Goal:** Ask the user: *"What do you want to build?"*
- **Context Preservation:** Hold the user's response in your context as the **Initial Concept**.

3.  **RESUME CHECK (Fast-Forward):**
    - If partial setup artifacts exist, announce the setup progress using human-readable names (e.g., "Technology Stack (`tech-stack.md`)"). Do NOT refer to internal section numbers.
    - Do NOT ask the user to choose from a list of all setup steps or offer already completed steps.
    - Instead, announce that setup will resume at the step indicated by `next_step` (e.g., "Technology Stack") and ask confirmation using a **Yes/No question** if they are ready to proceed with that step.
    - Proactively jump to the selected step upon approval. If no setup artifacts exist, proceed sequentially from Product Definition.

### 2.1 Product Definition (`product.md`)

Help the user define the product's vision, starting with the **Initial Concept** (Greenfield) or code analysis (Brownfield).

1.  **Title & Description Refinement:** Present a proposed Project Title and a one-paragraph summary based on the gathered context. Ask the user using a **Yes/No question** if this captures their vision.
2.  **Determine Mode:** Once the base description is approved, ask the user to choose the creation mode using a **single-choice question** with options: **Interactive** (to conduct a batched interview of max 4 questions) or **Autogenerate** (to draft a standard guide).

**Confirmation & Refinement Loop:**

1. Present the drafted `product.md` content (including the refined summary) to the user.
2. Ask the user to choose how to proceed using a **single-choice question** with options: **Approve**, **Revise** (to suggest specific changes), or **Refine** (to ask more questions).
3. Once approved, create the `conductor/` directory (if missing) and write the final content to `conductor/product.md`.

### 2.2 Product Guidelines (`product-guidelines.md`)

Help the user define branding, voice, tone, and UX principles.

1. **Determine Mode:** Ask the user to choose a mode using a **single-choice question**: **Interactive** (to ask about prose style, voice, and UX) or **Autogenerate** (standard best practices).
2. **Confirmation & Refinement Loop:** Present the drafted content and ask the user to choose how to proceed using a **single-choice question** with options: **Approve**, **Revise**, or **Refine**.
3. **Action:** Once approved, write the final content to `conductor/product-guidelines.md`.

### 2.3 Technology Stack (`tech-stack.md`)

Define and document the project's technology stack.

1.  **Determine Mode:**
    -   **Greenfield:** Ask the user to choose a mode using a **single-choice question**: **Interactive** (to hand-pick components) or **Autogenerate** (to recommend a standard stack based on the project goal).
        -   **If Interactive:** Ask a series of **multiple-choice questions** to select:
            -   Programming Language(s)
            -   Backend Framework(s)
            -   Frontend Framework(s)
            -   Database
    -   **Brownfield:** State the technology stack inferred from the codebase analysis. Ask the user for confirmation using a **Yes/No question** if it is correct. If not, ask an **open question** for them to provide the correct stack.

2.  **Confirmation & Refinement Loop:** Present the drafted stack to the user. Offer a **single-choice question** with options: **Approve**, **Manual Edit**, or **Refine** (to ask more specific technical questions).

3.  **Action:** Once approved, write the final content to `conductor/tech-stack.md`.

### 2.4 Code Style Guides

Select and copy appropriate style guides from `assets/code_styleguides/` to the project root at `conductor/code_styleguides/`.

1. **Asset Constraint:** You MUST ONLY propose and copy guides from `assets/code_styleguides/`. Do NOT generate style rules from scratch.
2. **Recommendation:** Propose guides based on the Tech Stack confirmed in 2.3.
3. **Selection Mode:**
    - **Brownfield:** Propose matching guides and ask the user using a **Yes/No question** if additional ones are needed.
    - **Greenfield:** Present recommended guides or allow the user to hand-pick from the library using a **multiple-choice question**.
4. **Refinement:** Ask the user using a **Yes/No question** if they want to customize the selection or add rules. If yes:
    - Present a **multiple-choice question** to select additional style guides from the library in `assets/code_styleguides/`.
    - Ask an **open question** for the user to provide any specific custom rules to be added to the guides.
5. **Copy Action:** Execute the copy command once the selection is confirmed.

### 2.5 Workflow Configuration (`workflow.md`)

Configure the operational rules for the project.

1. **Mode Selection:** Ask the user to choose a mode using a **single-choice question** with options: **Default** or **Customize**.
2. **Customization Flow (If selected):** Ask an **open question** for the coverage percentage. Commit frequency, git notes, branching, pushing and testing cadence are asked in Repository Workflow (2.6), not here.
3. **Explain:** Before copying, explain that the `workflow.md` defines the "rules of the game" for development: how each task is tested, committed and verified, following the settings chosen in the next step.
4. **Write Action:** Copy `assets/workflow.md` to `conductor/workflow.md` and apply user choices if customized.

### 2.6 Repository Workflow (`settings.json`)

Choose how this repository branches, commits, pushes and tests. The choices go in `conductor/settings.json`, which every Conductor skill re-reads before it plans, commits, pushes or verifies, and which the user can change later (by hand, by asking, or in the Conductor viewer).

**Main rules first:** the user's **main rules** are their own defaults for every project on this machine (`settings.json` in the Conductor viewer's config folder; the **Workflow**'s Workflow Settings section lists the paths). A repo's `conductor/settings.json` then holds only its **exceptions**. Each setting resolves to the repo's value, else the main rule, else the built-in default from the schema.

-   **Main rules exist** (the file exists and you can read it): show its values as a short table and ask with a **single-choice question**: **Follow the main rules** (Recommended unless the repo's history says otherwise) or **Set exceptions for this repo**. To follow them, write `conductor/settings.json` with only `{"version": 1}` and go to step 7. For exceptions, run the steps below with each main rule as the recommendation, and in step 6 write only the keys that differ from the main rules.
-   **No main rules yet** (the first project set up on this machine): explain in one sentence that main rules are set once and apply to every project unless a repo makes an exception, show the built-in defaults as a short table, and ask with a **single-choice question**:
    -   **Use the built-in defaults** (Recommended unless the repo's history says otherwise): write no main rules, write `conductor/settings.json` with only `{"version": 1}` and go to step 7. The user can set main rules later on the viewer's settings page.
    -   **Set my own main rules**: run the steps below, saying that these answers apply to every project. Skip the git-history evidence in step 3 (it describes this repo, not every project) and recommend the schema defaults. In step 6 write the answers to `settings.json` in the config folder (create the folder if needed), and `conductor/settings.json` with only `{"version": 1}`. If this repo's history suggests a different branching strategy, then offer it as an exception for this repo.
    -   **Only this repo**: run the steps below, and in step 6 write only the keys that differ from the built-in defaults.
-   **You can't read or write outside the repo** (a sandbox): say so, offer only **Use the built-in defaults** and **Only this repo**, and mention that main rules can be set on the viewer's settings page.

1.  **Load the Schema:** Read `assets/settings.schema.json`. It lists every setting, its options (with a one-line `summary` and, for some, a longer `detail`), and its default. Ask only about settings in the schema, and offer only its options.
2.  **Explain:** In two or three sentences, explain that these settings make the agent follow the repository's conventions rather than one fixed way of working, and that the defaults reproduce standard Conductor behaviour.
3.  **Infer Recommendations (Brownfield):** If the project has git history, look at it before asking:
    -   Compare `git rev-list --count --merges HEAD` with `git rev-list --count HEAD` on the main branch: regular merge commits suggest `feature-branch`; a straight line of commits suggests `trunk`. Few commits or no clear pattern: recommend the schema default.
    -   `git remote` prints nothing: there is nowhere to push, so recommend `git.push = ask`.
    -   Existing values (re-running this step): recommend the current value.
    -   Otherwise recommend the schema default. Mention the evidence in the recommendation, e.g. *(Recommended: 48 of 138 commits are merges)*.
4.  **Ask:** One **single-choice question** per setting, in schema order, following the Interaction Protocol: the option's `label` and `summary`, the recommended option first, and an "Other" option. Offer the `detail` text (for example the exact git commands) when the user asks what an option means. With `git.strategy = trunk`, add one sentence on the safety rule: force-pushes only ever go to the track's own branch, with `--force-with-lease --force-if-includes`, never to `main`.
5.  **Confirm:** Show the chosen values as a short table and ask for approval with a **single-choice question**: **Approve** or **Revise**.
6.  **Write Action:** Write the file chosen above (`conductor/settings.json`, or the main rules), nested by group. Main rules list every setting, defaults included, so the file documents itself; a repo file lists only its exceptions plus `"version": 1`. The full shape, with the built-in defaults:

    ```json
    {
      "version": 1,
      "git": { "strategy": "current", "commit": "task", "push": "ask", "notes": "on" },
      "testing": { "style": "tdd", "verification": "phase" }
    }
    ```

    Validate it with `python3 -m json.tool conductor/settings.json` if Python is available, or by re-reading it.
7.  **Link It:** Make sure `conductor/index.md` links it under `## Workflow` as `[Workflow Settings](./settings.json)`. When running this step alone in an initialized project, add that one line and commit both files with `conductor(setup): Add workflow settings`.

## 3. The Handshake (Index Generation)

Create `conductor/index.md`. This is the **Single Source of Truth** for all tools.

1.  **Explain:** Explain that the `index.md` is the "Handshake" of the project. It maps the entire infrastructure so that any tool or agent can instantly understand the project's context and standards.

2.  **Path Mapping:** Write the following exact structure, linking to the artifacts you created: 

```markdown

    # Project Context

    ## Definition

    -   [Product Definition](./product.md)
    -   [Product Guidelines](./product-guidelines.md)
    -   [Tech Stack](./tech-stack.md)

    ## Workflow

    -   [Workflow](./workflow.md)
    -   [Workflow Settings](./settings.json)
    -   [Code Style Guides](./code_styleguides/)
```

3.  **Integrity Check:** You MUST verify the existence of all linked files on disk.

4.  **Commit Stage:** Stage the entire `conductor/` directory. Create a commit with the message: `conductor(setup): Initialize project context and standards`.

## 4. Completion

Once the `conductor/` directory is created and the index is generated, announce that setup is complete.

**Next Steps:**

1. **Summary:** Present a final summary of the initialized scaffolding.
2.  **Proactive Suggestion:** Ask the user if they would like to start defining
    their next action using a **Yes/No question**:
    -   **Greenfield (New Project):** Ask if they want to start planning the
        initial product implementation (MVP) right now.
    -   **Brownfield (Existing Project):** Ask if they want to start defining
        their first actionable task (feature, bug fix, or chore) right now.
3. **Internal Handoff:** If the user agrees, you MUST use the `conductor-new-track` skill to begin planning.
