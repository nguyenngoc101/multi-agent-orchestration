#!/usr/bin/env bash
# setup-branch-protection.sh — apply the "server-side gate" with one command (gh api).
# Turns docs/branch-protection.md into real, idempotent configuration.
#
# DEFAULT: dry-run (only PRINTS the plan). Add --apply to actually call the API.
# Requires: gh logged in, with an account that has admin on the repo.
#
# Usage:
#   ./scripts/setup-branch-protection.sh            # show the plan
#   ./scripts/setup-branch-protection.sh --apply    # apply for real
#
# Deliberately does NOT hardcode stack check names: required checks = the neutral
# CI jobs (gate, validate-registry). Change the CHECKS var if your job names differ.

set -euo pipefail

APPLY=false
[[ "${1:-}" == "--apply" ]] && APPLY=true

command -v gh >/dev/null 2>&1 || { echo "✗ Need the gh CLI (https://cli.github.com)." >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "✗ gh not logged in. Run: gh auth login" >&2; exit 1; }

REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
CHECKS='"gate","validate-registry"'   # jobs that must be green before merge

echo "Repo: $REPO"
echo "Required checks: $CHECKS"
$APPLY && echo "Mode: APPLY (--apply)" || echo "Mode: DRY-RUN (add --apply to apply)"
echo

# enforce_admins=false: keep an override path for the owner during bootstrap; set to
# true when you want to lock admins out too. approvals: main needs human review,
# develop can be 0.
run() {
  local method="$1" path="$2" body="$3" desc="$4"
  echo "→ $desc  ($method $path)"
  if $APPLY; then
    printf '%s' "$body" | gh api -X "$method" "$path" --input - >/dev/null \
      && echo "  ✓ OK" || { echo "  ✗ FAILED (check admin rights / check names)"; return 1; }
  else
    echo "  [dry-run] body: $(printf '%s' "$body" | tr -d '\n' | tr -s ' ')"
  fi
}

# ── main / develop: classic branch protection (concrete branches) ────────────
protect_branch() {
  local branch="$1" approvals="$2"
  # Always send the reviews object (even count 0) so "Require a pull request before
  # merging" is ON. Sending null turns the PR requirement OFF — then direct pushes to
  # the branch are allowed, defeating the point. develop -> count 0 (PR required, no
  # approval); main -> count 1 (PR + 1 human approval).
  local reviews="{\"required_approving_review_count\":$approvals}"
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
# No creation/deletion rules so humans can still cut/delete releases; only require
# PR + checks + block force-push on these branches.
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
echo "Notes (do these in the UI — not reliably scriptable per team):"
echo "  - Restrict who can push main/release/hotfix → the human team only (exclude agent accounts)."
echo "  - Enable Merge Queue for develop (Settings → Rules)."
echo "  - Replace @your-team in .github/CODEOWNERS with a real team."
$APPLY || { echo; echo "This was a DRY-RUN. Re-run with --apply to apply."; }
