# WORKER_PROTOCOL.md — Contract for EVERY worker (Claude / Codex / other)

An agent-neutral protocol. The orchestrator assigns tasks in the INPUT format; the
worker returns results in the OUTPUT format. Don't rely on any single agent's specifics.

## INPUT — orchestrator assigns to a worker

```json
{
  "task_id": "T-101",
  "title": "Add a refund endpoint for payment",
  "branch": "feature/T-101",
  "base": "origin/develop",
  "scope": {
    "allow": ["src/payment/**", "test/payment/**"],
    "deny":  ["src/shared/**"]
  },
  "acceptance": [
    "POST /payments/{id}/refund returns 200 and creates a refund record",
    "Tests for the success case and the over-amount case"
  ],
  "commands": { "lint": "just lint", "test": "just test", "build": "just build" }
}
```

## Constraints a worker MUST follow (regardless of agent type)

1. ONLY change files matching `scope.allow`, NEVER touch `scope.deny` or files outside
   allow. Need to touch outside scope → STOP, return OUTPUT with `status=blocked` + reason.
   Don't widen it yourself.
2. Work in the worktree of the assigned `branch`. Don't check out another branch.
3. Before reporting done: rebase onto `base`, run `commands.lint/test/build`, all green.
4. No `git stash`, no force-push, don't touch main/develop/release/hotfix.
5. Small commits, clear messages, referencing `task_id`.
6. Context lives in ARTIFACTS, not memory: if reassigned, read `task.log`, your branch,
   and PR comments to reconstruct — don't assume you remember the previous session.
7. Cross-cutting decisions (shared interfaces, conventions) → READ `docs/decisions/` first
   and follow the Accepted ADRs. Need a NEW shared decision → STOP, propose an ADR
   (status=blocked, state it in `notes`); do NOT settle it yourself in a feature branch.

## OUTPUT — worker returns to the orchestrator

```json
{
  "task_id": "T-101",
  "status": "pr_open",        // pr_open | blocked | failed
  "branch": "feature/T-101",
  "pr": "https://github.com/org/repo/pull/210",
  "files_changed": ["src/payment/refund.*", "test/payment/refund.*"],
  "checks": { "lint": "pass", "test": "pass", "build": "pass" },
  "notes": "Notes for the reviewer; or the reason if blocked/failed",
  "out_of_scope_needed": []   // list files outside scope if blocked
}
```

## State rules

- `pr_open`  → orchestrator moves the task to `in_review`, waits for CI + review.
- `blocked`  → orchestrator reads `out_of_scope_needed` / `notes`, asks a human to re-split.
- `failed`   → orchestrator may reassign (same worker to keep context, or another idle
  worker if the task is independent).

## After review

If the reviewer/CI asks for changes: the orchestrator re-sends the same INPUT + a
`feedback` array (list of points to fix). The worker fixes it IN the same branch,
pushes again, and returns a new OUTPUT.
