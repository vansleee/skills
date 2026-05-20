#!/usr/bin/env bash
# Install (symlink) every skill in this repo into ~/.claude/skills/.
#
# A "skill" is any direct subdirectory of this repo that contains a SKILL.md.
# Idempotent: safe to re-run after `git pull`.
#
# Usage:
#   ./install-skills.sh             # install / refresh all skills
#   ./install-skills.sh --dry-run   # show what would happen, change nothing
#   ./install-skills.sh --uninstall # remove only the symlinks this repo owns
#   ./install-skills.sh --help

set -euo pipefail

# Resolve repo root from script location (works regardless of cwd).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$SCRIPT_DIR"
TARGET_DIR="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

DRY_RUN=0
MODE="install"

usage() {
  sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

for arg in "$@"; do
  case "$arg" in
    --dry-run)   DRY_RUN=1 ;;
    --uninstall) MODE="uninstall" ;;
    -h|--help)   usage ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  would: $*"
  else
    eval "$@"
  fi
}

# Refuse to clobber if $TARGET_DIR exists and is a symlink — that's the
# "symlink the whole repo" approach from option 3, and per-skill symlinks
# would land inside the linked repo instead of in ~/.claude/skills/.
if [[ -L "$TARGET_DIR" ]]; then
  echo "error: $TARGET_DIR is a symlink (probably to a whole repo)." >&2
  echo "       Remove it first: rm '$TARGET_DIR'" >&2
  exit 1
fi

# Discover skills: every direct subdir of REPO_ROOT with a SKILL.md.
mapfile -t SKILLS < <(
  find "$REPO_ROOT" -mindepth 2 -maxdepth 2 -name SKILL.md -type f -print0 \
    | xargs -0 -n1 dirname \
    | sort
)

if [[ ${#SKILLS[@]} -eq 0 ]]; then
  echo "no skills found in $REPO_ROOT (expected <repo>/<skill>/SKILL.md)" >&2
  exit 1
fi

echo "repo:   $REPO_ROOT"
echo "target: $TARGET_DIR"
[[ "$DRY_RUN" -eq 1 ]] && DRY_LABEL=" (dry-run)" || DRY_LABEL=""
echo "mode:   $MODE$DRY_LABEL"
echo "skills: ${#SKILLS[@]}"
echo

if [[ "$MODE" == "install" ]]; then
  run "mkdir -p '$TARGET_DIR'"
  for src in "${SKILLS[@]}"; do
    name="$(basename "$src")"
    dest="$TARGET_DIR/$name"

    # If something exists at dest, only replace it if it's a symlink we own
    # (i.e., resolves into this repo). Don't trash unrelated installs.
    if [[ -e "$dest" || -L "$dest" ]]; then
      if [[ -L "$dest" ]]; then
        existing="$(readlink "$dest")"
        case "$existing" in
          "$REPO_ROOT"/*) : ;;  # ours, fine to refresh
          *)
            echo "  skip $name — symlink already points elsewhere: $existing" >&2
            continue
            ;;
        esac
      else
        echo "  skip $name — $dest exists and is not a symlink (won't overwrite)" >&2
        continue
      fi
    fi

    echo "  link $name -> $src"
    run "ln -sfn '$src' '$dest'"
  done
  echo
  echo "done. open a new Claude Code session to pick up the new skills."

else  # uninstall
  for src in "${SKILLS[@]}"; do
    name="$(basename "$src")"
    dest="$TARGET_DIR/$name"

    if [[ ! -L "$dest" ]]; then
      echo "  skip $name — not a symlink (or not present)"
      continue
    fi
    existing="$(readlink "$dest")"
    case "$existing" in
      "$REPO_ROOT"/*)
        echo "  unlink $name"
        run "rm '$dest'"
        ;;
      *)
        echo "  skip $name — symlink points elsewhere: $existing"
        ;;
    esac
  done
  echo
  echo "done. only symlinks pointing into this repo were removed."
fi
