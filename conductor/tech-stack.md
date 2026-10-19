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
-   **Browser tests:** small standard-library drivers in `tests/browser.py` —
    the Chrome DevTools protocol for Chrome, Chromium and Edge, and WebDriver
    BiDi for Firefox. Run locally when a browser is installed, and in CI.

> **2026-10-19:** Replaced the proposed Playwright (CI-only) with the
> standard-library drivers above. Playwright needs Node and npm, which this
> repo otherwise never touches; the drivers cover Chromium, Edge and Firefox
> with nothing to install. Safari isn't automated: it needs `safaridriver` on
> a Mac, so Safari support rests on the feature audit and manual checks.
