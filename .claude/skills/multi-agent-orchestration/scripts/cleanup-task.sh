#!/usr/bin/env bash
# cleanup-task.sh <task-name>
# Chạy TỪ repo chính sau khi PR đã merge vào develop. Gỡ worktree + branch.

set -euo pipefail

task="${1:?Cần task-name. Dùng: ./scripts/cleanup-task.sh <task-name>}"

if [[ ! "$task" =~ ^[A-Za-z0-9][A-Za-z0-9-]*$ ]]; then
  echo "✗ task-name không hợp lệ: '$task' (chỉ A-Z, a-z, 0-9, '-')." >&2
  exit 1
fi

MAIN_REPO="$(git rev-parse --show-toplevel)"
BRANCH="feature/${task}"
WT_DIR="${WORKTREE_ROOT:-${MAIN_REPO}/../wt}/${task}"

cd "$MAIN_REPO"

if [[ -d "$WT_DIR" ]]; then
  git worktree remove "$WT_DIR"   # từ chối nếu còn thay đổi chưa commit
  echo "✓ Đã gỡ worktree: $WT_DIR"
fi

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git branch -d "$BRANCH"         # -d: chỉ xóa nếu đã merge (an toàn)
  echo "✓ Đã xóa branch local: $BRANCH"
fi

# Xóa branch trên remote (bỏ comment nếu muốn tự động)
# git push origin --delete "$BRANCH" && echo "✓ Đã xóa branch remote: $BRANCH"

git worktree prune
echo "✓ Đã prune metadata worktree."
