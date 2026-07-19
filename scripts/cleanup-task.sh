#!/usr/bin/env bash
# cleanup-task.sh <task-name>
# Run FROM the main repo after the PR is merged into develop. Remove worktree + branch.

set -euo pipefail

task="${1:?Need a task-name. Usage: ./scripts/cleanup-task.sh <task-name>}"

if [[ ! "$task" =~ ^[A-Za-z0-9][A-Za-z0-9-]*$ ]]; then
  echo "✗ invalid task-name: '$task' (only A-Z, a-z, 0-9, '-')." >&2
  exit 1
fi

MAIN_REPO="$(git rev-parse --show-toplevel)"
BRANCH="feature/${task}"
WT_DIR="${WORKTREE_ROOT:-${MAIN_REPO}/../wt}/${task}"

cd "$MAIN_REPO"

if [[ -d "$WT_DIR" ]]; then
  git worktree remove "$WT_DIR"   # refuses if there are uncommitted changes
  echo "✓ Removed worktree: $WT_DIR"
fi

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git branch -d "$BRANCH"         # -d: deletes only if merged (safe)
  echo "✓ Deleted local branch: $BRANCH"
fi

# Delete the remote branch (uncomment to automate)
# git push origin --delete "$BRANCH" && echo "✓ Deleted remote branch: $BRANCH"

git worktree prune
echo "✓ Pruned worktree metadata."
