# Product Definition

## What it is

Conductor is a set of agent skills (`SKILL.md` folders, Agent Skills open
standard) for **Spec-Driven Development**: set up project context once, then
plan each unit of work as a *track* with a `spec.md` and a `plan.md` before any
code is written, and implement it task by task.

It is a stripped-down personal fork of `gemini-cli-extensions/conductor`, used
daily at work as an elevated alternative to a harness's built-in plan mode.

## Users

-   The author, using it across Claude Code and Codex CLI at work and at home.
-   Anyone who wants agent-agnostic, file-based planning that survives switching
    agents mid-project.

## Goals

-   **Agent-agnostic:** works in any agent that reads `SKILL.md` folders. Codex
    CLI and Claude Code are the minimum bar.
-   **Files are the interface:** all state lives in plain Markdown/JSON under
    `conductor/`, readable by humans, agents and git.
-   **Zero install friction:** clone + symlink; nothing to build.
-   **Human stays in the loop:** specs and plans are reviewed before code.

## Features

-   `conductor-setup`, `conductor-new-track`, `conductor-implement`,
    `conductor-status`, `conductor-review` skills.
-   `link.sh` / `link.ps1` installers (symlinks / junctions).
