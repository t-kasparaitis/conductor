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
-   **Support targets:** Linux, macOS, Windows; Python 3.9+. Browsers:
    Chrome (preferred), then Firefox; others untested.
-   **Browser tests:** small standard-library drivers in `tests/browser.py` —
    the Chrome DevTools protocol for Chrome, Chromium and Edge, and WebDriver
    BiDi for Firefox. Run locally when a browser is installed, and in CI.

> **2026-10-19:** Replaced the proposed Playwright (CI-only) with the
> standard-library drivers above. Playwright needs Node and npm, which this
> repo otherwise never touches; the drivers cover Chromium, Edge and Firefox
> with nothing to install. Safari isn't automated: it needs `safaridriver` on
> a Mac, so Safari support rests on the feature audit and manual checks.

> **2026-10-19:** Narrowed browser support to Chrome (preferred) and Firefox
> (second). Edge, Safari and other browsers are untested; the code still
> avoids Chromium-only APIs, so they will probably work. Edge left the CI
> matrix.

> **2026-10-19:** The viewer keeps its own files (registered projects, the
> saved port and the main workflow rules) in a per-user config folder:
> `$XDG_CONFIG_HOME/conductor-view/` (default `~/.config/conductor-view/`) on
> Linux, `~/Library/Application Support/conductor-view/` on macOS,
> `%APPDATA%\conductor-view\` on Windows, overridable with
> `CONDUCTOR_VIEW_HOME`. Still standard library only; git is read through
> the `git` command when it's installed (read-only, no locks, 5 s timeouts)
> and the viewer works without it.
