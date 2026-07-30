#!/usr/bin/env bash
#
# link-skills.sh — Canonical skill linker for the talk project (bmad hub).
#
# Claude Code only discovers skills under `.claude/skills/`. This script
# populates `.claude/skills/` in the CURRENT directory with one symlink per
# skill folder, drawing from:
#   1. the bmad hub skills (always: talk-bmad/.agents/skills/*)
#   2. any extra `.agents/skills` roots passed as arguments (repo-local skills)
#
# Linking per-skill (not the whole skills/ dir) lets a repo combine the shared
# bmad skills with its own local skills in a single `.claude/skills/`.
#
# Usage (run from the target repo root):
#   talk-bmad     : bash ../talk-bmad/scripts/link-skills.sh            # bmad only
#   talk-backend  : bash ../talk-bmad/scripts/link-skills.sh .agents/skills   # bmad + golang
#   talk-ui       : bash ../talk-bmad/scripts/link-skills.sh .agents/skills   # bmad + typescript
#
# `.claude/skills/` is machine-local (symlinks) and must stay gitignored.
# Windows users: run link-skills.ps1 instead.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# On Windows (Git Bash / MSYS / Cygwin), `ln -s` is unreliable (MSYS often copies
# instead of linking). Delegate to the PowerShell version, which uses junctions.
case "$(uname -s 2>/dev/null)" in
  MINGW*|MSYS*|CYGWIN*)
    exec powershell -NoProfile -ExecutionPolicy Bypass \
      -File "$SCRIPT_DIR/link-skills.ps1" ${1:+-ExtraRoots "$1"}
    ;;
esac

BMAD_SKILLS="$SCRIPT_DIR/../.agents/skills"
DEST=".claude/skills"

mkdir -p "$DEST"

link_from() {
  local src="$1"
  if [ ! -d "$src" ]; then
    echo "skip (missing): $src"
    return
  fi
  src="$(cd "$src" && pwd)"
  local skill name target
  for skill in "$src"/*/; do
    [ -d "$skill" ] || continue
    name="$(basename "$skill")"
    target="$DEST/$name"
    rm -rf "$target"
    ln -s "$skill" "$target"
    echo "linked: $name -> $skill"
  done
}

# 1. bmad hub skills (always)
link_from "$BMAD_SKILLS"

# 2. repo-local skill roots (extra arguments)
for root in "$@"; do
  link_from "$root"
done

echo "Done. $DEST populated. Reload the Claude Code window to pick up new skills."
