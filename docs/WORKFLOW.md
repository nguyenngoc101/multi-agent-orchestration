# WORKFLOW — Full flow: local dev → GitHub

From the orchestrator splitting tasks to code reaching PROD. Every stack command goes
through `just` (or `make`), so it's language-agnostic.

## Big picture

```
ORCHESTRATOR (Claude)
   │  read registry → check waves → match idle worker → assign task
   ▼
WORKER (local)                         GITHUB
  new-task.sh  ─ worktree+branch        ┌───────────────────────────┐
  code                                  │ PR  → CI (lint/test/build) │
  submit-task.sh ─ rebase+gate+push ──► │     → registry-guard       │
                                        │     → merge queue          │
                                        │     → merge into develop    │
                                        └───────────┬───────────────┘
                                                    ▼
                                     release cut (human) → Dev→SIT→UAT→PROD
                                                    ▼
                                        merge into main + tag (=PROD)
```

## Phase 1 — Orchestrator splits & assigns (local or CI)

1. Open a control-plane PR that changes only `task-registry.json`: add a task with
   `scope.allow`, `requires`, `depends_on`. This PR must be approved by a CODEOWNER and
   merged into `develop` before the feature branch is created; a worker may not add or
   widen its own policy.
2. `just check-registry` — must be OK; view the waves. If FAIL (cycle/missing dep), fix it.
3. The orchestrator picks a task from the current wave, matches an idle agent, assigns per WORKER_PROTOCOL.

## Phase 2 — Worker works (local dev)

```bash
# 1. Create the isolated environment
./scripts/new-task.sh T-101          # worktree ../wt/T-101 + branch feature/T-101
cd ../wt/T-101
export GIT_AUTHOR_NAME="agent-T-101" GIT_AUTHOR_EMAIL="agent-T-101@local"
just bootstrap                       # install dependencies for this worktree

# 2. Code — ONLY within T-101's scope.allow. Small, frequent commits.

# 3. Prepare the PR
./scripts/submit-task.sh             # rebase origin/develop + lint+test+build + push
```

On the first push the script rebases to keep history straight. If the branch already
exists on the remote, the script merges `origin/develop` instead of rebasing, to avoid
force-pushing already-published history.

Local hooks (`.githooks/pre-commit`, `pre-push`) block accidental commits/pushes to forbidden branches.

## Phase 3 — GitHub (automatic)

Open a PR `feature/T-101 → develop` (submit-task suggests the `gh pr create` command).

On the PR, running in parallel:
- **ci.yml** — lint/test/build must be green.
- **registry-guard.yml** — validate the registry + `enforce-scope.py` blocks the PR if it
  changes files outside T-101's `scope.allow`.
- **CODEOWNERS** — if the PR touches a sensitive area (`src/shared`, `db/migrations`...),
  human review is required.

Green + approved PR → into the **merge queue**. The queue rebases each PR onto the latest
develop, re-runs CI, and merges sequentially (squash). This is where serialization makes
parallelism safe. The guard and registry policy used to evaluate a feature PR are checked
out from the base SHA, so a PR cannot edit its own arbiter or scope to pass the checks.

## Phase 4 — Clean up & repeat

```bash
cd <main repo>
./scripts/cleanup-task.sh T-101      # remove worktree + branch
```
The orchestrator updates the registry: T-101 = `merged`, worker back to `idle`, unblocking
tasks that depend on T-101 (into a later wave).

## Phase 5 — Release (human, NOT an agent)

```bash
git switch develop && git pull
git switch -c release/2026.03        # cut when enough features have accumulated
# CI/CD promotes the SAME artifact: Dev → SIT → UAT (acceptance) → PROD (manual approval)
git switch main && git merge --no-ff release/2026.03 && git tag v2026.03
git switch develop && git merge --no-ff release/2026.03   # back-merge
```

## Phase 6 — Hotfix (human)

```bash
git switch main && git switch -c hotfix/2026.03.1
# fix → promote through envs → deploy PROD
git switch main    && git merge --no-ff hotfix/2026.03.1 && git tag v2026.03.1
git switch develop && git merge --no-ff hotfix/2026.03.1   # MANDATORY back-merge
```

## Who may do what

| Action | Agent | Human |
|---|---|---|
| feature/* + PR into develop | ✓ | ✓ |
| merge into develop | ✓ (if protection allows, CI green) | ✓ |
| cut release/* | ✗ | ✓ |
| merge into main, tag | ✗ | ✓ |
| approve PROD | ✗ | ✓ |
| hotfix | ✗ | ✓ |
