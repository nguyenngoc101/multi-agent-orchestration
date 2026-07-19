#!/usr/bin/env bash
# submit-task.sh
# Run INSIDE the feature branch's worktree. Update from develop, run the gate
# (lint/test/build via just|make), then push. Does not merge — only prepares the PR.
# Stack-agnostic: the gate goes through RUNNER, never a stack tool directly.

set -euo pipefail

BASE="${BASE_BRANCH:-origin/develop}"

branch="$(git symbolic-ref --short HEAD)"
if [[ ! "$branch" =~ ^feature/ ]]; then
  echo "✗ On '$branch'. This script only runs on feature/*." >&2
  exit 1
fi

# Pick runner: just > make. Don't guess stack commands.
if command -v just >/dev/null 2>&1 && [[ -f justfile || -f Justfile ]]; then
  RUNNER="just"
elif [[ -f Makefile || -f makefile ]]; then
  RUNNER="make"
else
  echo "✗ No justfile/Makefile found. Add one to define lint/test/build." >&2
  echo "  (Deliberately not hardcoding stack commands here.)" >&2
  exit 1
fi

published=false
if git remote get-url origin >/dev/null 2>&1 && \
   git ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
  published=true
fi

echo "→ Update from $BASE"
if git remote get-url origin >/dev/null 2>&1; then
  git fetch origin
  if [[ "$published" == true ]]; then
    # Rebase would rewrite an already-published branch and require a forbidden
    # force-push. Preserve history with a regular merge instead.
    git merge --no-edit "$BASE"
  else
    git rebase "$BASE"
  fi
else
  echo "ℹ No 'origin' remote — rebase onto a local branch if present."
  local_base="${BASE#origin/}"
  if git show-ref --verify --quiet "refs/heads/${local_base}"; then
    git rebase "$local_base"
  else
    echo "ℹ Skipping rebase (base not found)."
  fi
fi

echo "→ Gate: lint"
$RUNNER lint
echo "→ Gate: test"
$RUNNER test
echo "→ Gate: build"
$RUNNER build

echo "→ Push $branch"
git push -u origin "$branch"

echo ""
echo "✓ Ready to open a PR:  $branch  →  develop"
echo "  With the gh CLI:"
echo "    gh pr create --base develop --head \"$branch\" --fill"
