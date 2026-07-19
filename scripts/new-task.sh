#!/usr/bin/env bash
# new-task.sh <task-name>
# Create a worktree + feature branch off origin/develop, normalizing everything.
# Stack-agnostic: installs nothing stack-specific. If you need per-worktree
# port/DB isolation, add it under "ENVIRONMENT HOOK" at the end (project-specific).

set -euo pipefail

task="${1:?Need a task-name. Usage: ./scripts/new-task.sh <task-name>}"

# Sanitize task name: letters (upper/lower), digits, hyphen.
# Allow uppercase so it matches ids like 'T-101' in the registry -> branch feature/T-101.
if [[ ! "$task" =~ ^[A-Za-z0-9][A-Za-z0-9-]*$ ]]; then
  echo "✗ invalid task-name: '$task' (only A-Z, a-z, 0-9, '-')." >&2
  exit 1
fi

# Main repo dir = where the script runs (assumes run from repo root)
MAIN_REPO="$(git rev-parse --show-toplevel)"
BRANCH="feature/${task}"
WT_DIR="${WORKTREE_ROOT:-${MAIN_REPO}/../wt}/${task}"
BASE="${BASE_BRANCH:-origin/develop}"

cd "$MAIN_REPO"

# Make sure hooks are enabled repo-wide (applies to worktrees too)
git config core.hooksPath .githooks

# Fetch if an 'origin' remote exists; skip quietly if not (local dev / practice)
if git remote get-url origin >/dev/null 2>&1; then
  git fetch origin
else
  echo "ℹ No 'origin' remote — skipping fetch (local dev)."
  # If BASE points at origin/* but there is no origin, fall back to a local branch of the same name
  if [[ "$BASE" == origin/* ]]; then
    local_base="${BASE#origin/}"
    if git show-ref --verify --quiet "refs/heads/${local_base}"; then
      BASE="$local_base"
      echo "ℹ Using local base: $BASE"
    fi
  fi
fi

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "✗ Branch ${BRANCH} already exists. Pick another task-name or clean up the old one." >&2
  exit 1
fi

git worktree add "$WT_DIR" -b "$BRANCH" "$BASE"

echo "✓ Worktree: $WT_DIR"
echo "✓ Branch:   $BRANCH  (off $BASE)"
echo ""
echo "Next steps:"
echo "  cd \"$WT_DIR\""
echo "  export GIT_AUTHOR_NAME=\"agent-${task}\""
echo "  export GIT_AUTHOR_EMAIL=\"agent-${task}@local\""
echo "  export GIT_COMMITTER_NAME=\"agent-${task}\""
echo "  export GIT_COMMITTER_EMAIL=\"agent-${task}@local\""

# ── ENVIRONMENT HOOK (project-specific, NOT stack-bound) ─────────────────────
# If an agent runs a dev server / DB / migrations, isolate the runtime here so two
# worktrees don't collide on port/DB. For example, write to .env.local:
#
#   PORT=$(( 3000 + RANDOM % 1000 ))
#   echo "APP_PORT=${PORT}"        >> "$WT_DIR/.env.local"
#   echo "DB_SCHEMA=agent_${task}" >> "$WT_DIR/.env.local"
#
# Install dependencies (each worktree installs its own — files outside git aren't shared):
#   ( cd "$WT_DIR" && just bootstrap )   # 'just bootstrap' is defined by the repo
# ─────────────────────────────────────────────────────────────────────────────
