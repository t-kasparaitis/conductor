#!/usr/bin/env bash
# Symlink each skill into the agents' skill directories so they are
# discovered by Claude Code (~/.claude/skills) and Codex CLI (~/.agents/skills).
# Run with --remove to delete the symlinks instead.
set -euo pipefail

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--remove" ) ]]; then
  echo "usage: ${0##*/} [--remove]" >&2
  exit 1
fi

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    echo "On Windows, ln -s usually copies instead of linking." >&2
    echo "Use: powershell -ExecutionPolicy Bypass -File link.ps1" >&2
    exit 1
    ;;
esac

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_HOME="${CONDUCTOR_HOME:-$HOME}"
TARGET_DIRS=("$INSTALL_HOME/.claude/skills" "$INSTALL_HOME/.agents/skills")

SKILLS=("$REPO_DIR"/skills/*/)
if [[ ! -d "${SKILLS[0]}" ]]; then
  echo "error: no skills found in $REPO_DIR/skills (incomplete checkout?)" >&2
  exit 1
fi

for target in "${TARGET_DIRS[@]}"; do
  mkdir -p "$target"
  for skill in "${SKILLS[@]}"; do
    name="$(basename "$skill")"
    link="$target/$name"
    expected="${skill%/}"
    if [[ "${1:-}" == "--remove" ]]; then
      if [[ -L "$link" && "$(readlink "$link")" == "$expected" ]]; then
        rm "$link"
        echo "removed $link"
      elif [[ -L "$link" ]]; then
        echo "skipped $link (link is not managed by this checkout)" >&2
      fi
    elif [[ -L "$link" && "$(readlink "$link")" != "$expected" ]]; then
      echo "skipped $link (link is not managed by this checkout)" >&2
    elif [[ -e "$link" && ! -L "$link" ]]; then
      echo "skipped $link (exists and is not a link)" >&2
    else
      ln -sfn "$expected" "$link"
      echo "linked $link -> $expected"
    fi
  done
done
