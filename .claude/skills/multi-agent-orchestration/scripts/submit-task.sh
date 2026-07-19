#!/usr/bin/env bash
# submit-task.sh
# Chạy TRONG worktree của feature branch. Rebase lên develop, chạy gate
# (lint/test/build qua just|make), rồi push. Không tự merge — chỉ chuẩn bị PR.
# Stack-agnostic: gate gọi qua RUNNER, không gọi thẳng công cụ stack.

set -euo pipefail

BASE="${BASE_BRANCH:-origin/develop}"

branch="$(git symbolic-ref --short HEAD)"
if [[ ! "$branch" =~ ^feature/ ]]; then
  echo "✗ Đang ở '$branch'. Script chỉ chạy trên feature/*." >&2
  exit 1
fi

# Chọn runner: just > make. Không đoán lệnh stack.
if command -v just >/dev/null 2>&1 && [[ -f justfile || -f Justfile ]]; then
  RUNNER="just"
elif [[ -f Makefile || -f makefile ]]; then
  RUNNER="make"
else
  echo "✗ Không tìm thấy justfile/Makefile. Thêm nó để định nghĩa lint/test/build." >&2
  echo "  (Cố tình không hardcode lệnh stack ở đây.)" >&2
  exit 1
fi

echo "→ Rebase lên $BASE"
if git remote get-url origin >/dev/null 2>&1; then
  git fetch origin
  git rebase "$BASE"
else
  echo "ℹ Không có remote 'origin' — rebase lên nhánh local nếu có."
  local_base="${BASE#origin/}"
  if git show-ref --verify --quiet "refs/heads/${local_base}"; then
    git rebase "$local_base"
  else
    echo "ℹ Bỏ qua rebase (không tìm thấy base)."
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
echo "✓ Sẵn sàng mở PR:  $branch  →  develop"
echo "  Nếu có gh CLI:"
echo "    gh pr create --base develop --head \"$branch\" --fill"
