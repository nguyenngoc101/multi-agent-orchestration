#!/usr/bin/env bash
# new-task.sh <task-name>
# Tạo worktree + feature branch off từ origin/develop, chuẩn hóa mọi thứ.
# Stack-agnostic: không cài đặt gì theo stack. Nếu cần tách port/DB per-worktree,
# thêm ở mục "HOOK MÔI TRƯỜNG" cuối file (tùy dự án).

set -euo pipefail

task="${1:?Cần task-name. Dùng: ./scripts/new-task.sh <task-name>}"

# Vệ sinh tên task: chữ (hoa/thường), số, gạch ngang.
# Cho phép hoa để khớp id kiểu 'T-101' trong registry → branch feature/T-101.
if [[ ! "$task" =~ ^[A-Za-z0-9][A-Za-z0-9-]*$ ]]; then
  echo "✗ task-name không hợp lệ: '$task' (chỉ A-Z, a-z, 0-9, '-')." >&2
  exit 1
fi

# Thư mục repo chính = nơi chạy script (giả định chạy từ gốc repo)
MAIN_REPO="$(git rev-parse --show-toplevel)"
BRANCH="feature/${task}"
WT_DIR="${WORKTREE_ROOT:-${MAIN_REPO}/../wt}/${task}"
BASE="${BASE_BRANCH:-origin/develop}"

cd "$MAIN_REPO"

# Bảo đảm hook được kích hoạt cho toàn repo (áp cho cả worktree)
git config core.hooksPath .githooks

# Fetch nếu có remote 'origin'; bỏ qua êm nếu chưa có (dev local / lúc practice)
if git remote get-url origin >/dev/null 2>&1; then
  git fetch origin
else
  echo "ℹ Không có remote 'origin' — bỏ qua fetch (dev local)."
  # Nếu BASE trỏ origin/* mà không có origin, lùi về nhánh local cùng tên
  if [[ "$BASE" == origin/* ]]; then
    local_base="${BASE#origin/}"
    if git show-ref --verify --quiet "refs/heads/${local_base}"; then
      BASE="$local_base"
      echo "ℹ Dùng base local: $BASE"
    fi
  fi
fi

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "✗ Branch ${BRANCH} đã tồn tại. Chọn task-name khác hoặc dọn cái cũ." >&2
  exit 1
fi

git worktree add "$WT_DIR" -b "$BRANCH" "$BASE"

echo "✓ Worktree: $WT_DIR"
echo "✓ Branch:   $BRANCH  (off từ $BASE)"
echo ""
echo "Bước tiếp:"
echo "  cd \"$WT_DIR\""
echo "  export GIT_AUTHOR_NAME=\"agent-${task}\""
echo "  export GIT_AUTHOR_EMAIL=\"agent-${task}@local\""
echo "  export GIT_COMMITTER_NAME=\"agent-${task}\""
echo "  export GIT_COMMITTER_EMAIL=\"agent-${task}@local\""

# ── HOOK MÔI TRƯỜNG (tùy dự án, KHÔNG gắn stack) ─────────────────────────
# Nếu agent chạy dev server / DB / migration, cách ly runtime ở đây để hai
# worktree không đụng nhau về port/DB. Ví dụ ghi ra file .env.local:
#
#   PORT=$(( 3000 + RANDOM % 1000 ))
#   echo "APP_PORT=${PORT}"        >> "$WT_DIR/.env.local"
#   echo "DB_SCHEMA=agent_${task}" >> "$WT_DIR/.env.local"
#
# Cài dependency (mỗi worktree tự cài — file ngoài git không share):
#   ( cd "$WT_DIR" && just bootstrap )   # 'just bootstrap' do repo định nghĩa
# ─────────────────────────────────────────────────────────────────────────
