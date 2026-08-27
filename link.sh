#!/usr/bin/env bash
# Symlink each skill into the agents' skill directories so they are
# discovered by Claude Code (~/.claude/skills) and Codex CLI (~/.agents/skills).
# Run with --remove to delete the symlinks instead.
set -euo pipefail

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    echo "On Windows, ln -s usually copies instead of linking." >&2
    echo "Use: powershell -ExecutionPolicy Bypass -File link.ps1" >&2
    exit 1
    ;;
esac

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIRS=("$HOME/.claude/skills" "$HOME/.agents/skills")

for target in "${TARGET_DIRS[@]}"; do
  mkdir -p "$target"
  for skill in "$REPO_DIR"/skills/*/; do
    name="$(basename "$skill")"
    link="$target/$name"
    if [[ "${1:-}" == "--remove" ]]; then
      if [[ -L "$link" ]]; then
        rm "$link"
        echo "removed $link"
      fi
    elif [[ -e "$link" && ! -L "$link" ]]; then
      echo "skipped $link (exists and is not a link)" >&2
    else
      ln -sfn "${skill%/}" "$link"
      echo "linked $link -> ${skill%/}"
    fi
  done
done
