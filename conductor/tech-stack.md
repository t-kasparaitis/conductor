# Tech Stack

-   **Skills:** Markdown (`SKILL.md` + `assets/`), Agent Skills open standard.
-   **Installers:** POSIX `sh`/bash (`link.sh`), Windows PowerShell 5.1+
    (`link.ps1`).
-   **CI:** GitHub Actions (`.github/workflows/test-install.yml`) on Ubuntu,
    macOS and Windows.
-   **Runtime dependencies:** none. The core skills are pure Markdown.

## Optional tooling (proposed by track `visual_companion_20261007`)

-   **Python 3.9+ standard library only** for an optional local viewer server
    (`http.server`, `json`, `pathlib`). No pip installs.
-   **Vanilla HTML/CSS/JS** for the viewer UI — no build step, no CDN, works
    offline.
-   **Tests:** Python `unittest` (stdlib) for the parser/server.
-   **Support targets:** Linux, macOS, Windows; Python 3.9+; current Chrome,
    Edge, Firefox and Safari.
-   **CI-only (proposed):** Playwright for cross-browser end-to-end tests. Never
    required by users.
