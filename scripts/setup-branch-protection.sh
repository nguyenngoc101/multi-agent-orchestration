#!/usr/bin/env bash
# setup-branch-protection.sh — áp "lớp chặn phía server" bằng một lệnh (gh api).
# Biến docs/branch-protection.md thành cấu hình thật, idempotent.
#
# MẶC ĐỊNH: dry-run (chỉ IN kế hoạch). Thêm --apply để thực sự gọi API.
# Yêu cầu: gh đã đăng nhập, tài khoản có quyền admin trên repo.
#
# Dùng:
#   ./scripts/setup-branch-protection.sh            # xem kế hoạch
#   ./scripts/setup-branch-protection.sh --apply    # áp thật
#
# Cố tình KHÔNG hardcode tên check stack: required checks = job CI trung lập
# (gate, validate-registry). Đổi ở biến CHECKS nếu tên job khác.

set -euo pipefail

APPLY=false
[[ "${1:-}" == "--apply" ]] && APPLY=true

command -v gh >/dev/null 2>&1 || { echo "✗ Cần gh CLI (https://cli.github.com)." >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "✗ gh chưa đăng nhập. Chạy: gh auth login" >&2; exit 1; }

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
CHECKS='"gate","validate-registry"'   # job phải xanh trước khi merge

echo "Repo: $REPO"
echo "Required checks: $CHECKS"
$APPLY && echo "Chế độ: ÁP THẬT (--apply)" || echo "Chế độ: DRY-RUN (thêm --apply để áp)"
echo

# enforce_admins=false: giữ đường cho owner override lúc bootstrap; đổi thành true
# khi muốn khoá cả admin. approvals: main cần người duyệt, develop có thể 0.
run() {
  local method="$1" path="$2" body="$3" desc="$4"
  echo "→ $desc  ($method $path)"
  if $APPLY; then
    printf '%s' "$body" | gh api -X "$method" "$path" --input - >/dev/null \
      && echo "  ✓ OK" || { echo "  ✗ THẤT BẠI (kiểm quyền admin / tên check)"; return 1; }
  else
    echo "  [dry-run] body: $(printf '%s' "$body" | tr -d '\n' | tr -s ' ')"
  fi
}

# ── main / develop: classic branch protection (nhánh cụ thể) ────────────────
protect_branch() {
  local branch="$1" approvals="$2"
  local reviews="null"
  [[ "$approvals" -gt 0 ]] && reviews="{\"required_approving_review_count\":$approvals}"
  run PUT "repos/$REPO/branches/$branch/protection" "$(cat <<JSON
{
  "required_status_checks": { "strict": true, "contexts": [ $CHECKS ] },
  "enforce_admins": false,
  "required_pull_request_reviews": $reviews,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
)" "protect $branch (PR + checks + no force-push, approvals=$approvals)"
}

protect_branch main 1
protect_branch develop 0

# ── release/* , hotfix/* : ruleset (wildcard) ───────────────────────────────
# Không thêm rule creation/deletion để người vẫn cắt/xoá release được; chỉ bắt
# PR + checks + cấm force-push trên các nhánh này.
run POST "repos/$REPO/rulesets" "$(cat <<JSON
{
  "name": "protect-release-hotfix",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["refs/heads/release/**","refs/heads/hotfix/**"], "exclude": [] } },
  "rules": [
    { "type": "pull_request", "parameters": {
        "required_approving_review_count": 1,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false } },
    { "type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [ { "context": "gate" }, { "context": "validate-registry" } ] } },
    { "type": "non_fast_forward" }
  ]
}
JSON
)" "ruleset release/* + hotfix/* (PR + checks + no force-push)"

echo
echo "Ghi chú (làm trên UI, không script được tin cậy theo team):"
echo "  - Restrict who can push main/release/hotfix → chỉ team người (loại account agent)."
echo "  - Bật Merge Queue cho develop (Settings → Rules)."
echo "  - Thay @your-team trong .github/CODEOWNERS bằng team thật."
$APPLY || { echo; echo "Đây là DRY-RUN. Chạy lại với --apply để áp."; }
