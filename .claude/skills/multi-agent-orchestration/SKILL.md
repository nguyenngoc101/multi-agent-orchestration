---
name: multi-agent-orchestration
description: >-
  Orchestrate many agents running in parallel on one Git repo using git worktrees +
  gitflow (feature → develop → release → main). Use this skill when you need to split a
  chunk of work into many tasks for multiple agents/workers to do at once, manage
  dependencies and scope so they don't collide, and ship safely through GitHub (PRs, CI,
  merge queue). Triggers on: multi-agent, orchestrator, worker pool, running many agents
  in parallel, git worktree for agents, splitting tasks across agents, or managing
  dependency/scope between parallel tasks.
---

# Multi-agent orchestration

This skill contains the process + tools for one ORCHESTRATOR (Claude) to coordinate many
WORKERS (Claude/Codex/other) working in parallel on a repo, safely for production.

## Two-layer isolation model

1. **worktree** — TECHNICAL isolation: each worker gets 1 directory + 1 `feature/<id>`
   branch, sharing one `.git`, without clobbering each other's files.
2. **gitflow + branch protection** — AUTHORITY isolation: workers only touch `feature/*`
   and merge into `develop`; `main`/`release/*`/`hotfix/*` are human-owned.

`main` always reflects PROD. Features never touch main directly.

## When orchestrating, DO in order

1. Read `task-registry.json` (the single source of truth — do NOT keep state in your head).
2. Run `python3 scripts/check-registry.py` to: detect dependency cycles, missing deps,
   scope overlap, and PRINT the parallel waves. Don't assign tasks when the registry FAILs.
3. For each task in the current wave: match `requires` (capability) with an `idle` agent,
   check scope doesn't overlap an `in_progress` task, then assign.
4. Send the task to the worker per `orchestrator/prompts/WORKER_PROTOCOL.md` (INPUT JSON).
5. Worker runs `scripts/new-task.sh <id>` → code → `scripts/submit-task.sh` → open PR.
6. GitHub gates it: CI (`.github/workflows/ci.yml`) + scope enforce
   (`registry-guard.yml`) + merge queue. The orchestrator does NOT merge into forbidden areas.
7. PR merged → update the registry, worker back to `idle`, repeat from step 1.

## Two kinds of dependency — distinguish them

- **Logical** (`depends_on`): must wait for the other task to be `merged`. Topo-sort. Block cycles.
- **Scope overlap** (`scope.allow` intersect): no logical dependency but can't run at the
  same time — serialize them, or split the shared part into its own prerequisite task.

## HARD boundaries (never violate)

- Orchestrator/worker do NOT push/merge `main`/`release/*`/`hotfix/*`.
- Don't widen `scope.allow` "to finish" — if you exceed scope, STOP and tell a human.
- CI is the arbiter, don't trust a worker's "already tested".
- Cutting releases / approving PROD / hotfixes are human jobs.

## Files in the skill

- `orchestrator/prompts/ORCHESTRATOR.md` — full orchestrator operating rules
- `orchestrator/prompts/WORKER_PROTOCOL.md` — INPUT/OUTPUT contract for workers
- `orchestrator/schema/task-registry.schema.json` — registry schema
- `scripts/check-registry.py` — validate + compute waves
- `scripts/enforce-scope.py` — block PRs changing files out of scope (used in CI)
- `scripts/new-task.sh` / `submit-task.sh` / `cleanup-task.sh` — worktree lifecycle
- `docs/WORKFLOW.md` — full flow local dev → GitHub
- `docs/branch-protection.md` — configuring the server-side gate

## Command quick reference

```
just check-registry              # validate + print parallel waves
./scripts/new-task.sh T-101      # create worktree + feature/T-101
./scripts/submit-task.sh         # rebase + gate + push (inside the worktree)
./scripts/cleanup-task.sh T-101  # clean up after merge (from the main repo)
```
