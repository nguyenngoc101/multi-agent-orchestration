# Multi-Agent Orchestration — Practice Project

A template repo to **practice** orchestrating many agents running in parallel on one
Git codebase, shipped through GitHub safely for production. Stack-agnostic: every
build/test/lint command goes through `just`/`make`; switching stacks means editing only
the `justfile`.

## Core idea — two isolation layers

1. **git worktree** → TECHNICAL isolation: each agent gets its own directory + branch,
   sharing one `.git`, without clobbering each other's files.
2. **gitflow + branch protection** → AUTHORITY isolation: agents only touch `feature/*`
   and merge into `develop`; `main`/`release/*`/`hotfix/*` are human-owned. `main` = PROD.

Orchestrate with an **orchestrator (Claude) + worker pool** model (Claude/Codex/other),
assigning tasks by capability + idle agent, managing dependencies and scope so that
parallelism doesn't turn into chaos.

## Structure

```
AGENTS.md                      Rules for every agent (read before working)
task-registry.json             Source of truth: tasks, scope, dependencies, agents
justfile                       Single point defining stack commands

.claude/skills/
  multi-agent-orchestration/   SKILL.md — Claude auto-loads the orchestration process

orchestrator/
  prompts/ORCHESTRATOR.md      Orchestrator operating rules
  prompts/WORKER_PROTOCOL.md   INPUT/OUTPUT contract for workers
  schema/task-registry.schema.json

scripts/
  new-task.sh                  Create worktree + feature branch
  submit-task.sh               Rebase + gate + push
  cleanup-task.sh              Clean up after merge
  check-registry.py            Validate registry + compute parallel waves
  enforce-scope.py             Block PRs changing files out of scope (used in CI)
  orchestrate.py               Semi-auto dispatcher: PR merged → transition state + next wave
  setup-branch-protection.sh   Apply server-side branch protection via gh api (dry-run by default)

.githooks/
  pre-commit / pre-push        Locally block commits/pushes to forbidden branches

.github/
  workflows/ci.yml             Gate lint/test/build on PRs
  workflows/registry-guard.yml Validate registry + enforce scope
  pull_request_template.md
  CODEOWNERS
  merge-queue.md               Note on enabling the merge queue

docs/
  WORKFLOW.md                  Full flow: local dev → GitHub
  branch-protection.md         Configuring the server-side gate
  PRACTICE.md                  Step-by-step practice exercises
  worker-runtimes.md           Trigger Codex vs Claude workers by agents[].kind
  decisions/                   ADRs — SHARED memory (project-context) for every agent

examples/
  task-registry.sample.json    Sample 3-wave registry (reference while practicing)
```

## Quick setup

```bash
# 1. Enable the hooks
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh scripts/*.py

# 2. Install just (or use the Makefile) — https://github.com/casey/just

# 3. This template self-checks using the Python standard library. When applying it to
#    an app, extend lint/test/build in justfile/Makefile with your stack's commands.

# 4. Try the registry check
just check-registry            # prints the parallel waves

# 5. (On GitHub) configure branch protection + merge queue per docs/
```

## Getting started with practice

See `docs/PRACTICE.md` — 6 exercises from easy to hard, covering the full range:
basic worktree, two parallel agents, dependencies waiting on each other, scope conflict,
a scope violation blocked by CI, and a full release cycle.

## Safety note

The orchestrator model is powerful but **the lead is a single point of failure**. Early
on, keep a human on the merge-into-develop approval, watch a few dozen tasks to see
whether scope stays clean, and only then loosen toward automation. Don't go full-auto
from day one.

The registry and the guard scripts used to evaluate a PR are always read from a trusted
base SHA; never run the guard version supplied by the PR itself. A new task must first
be added to `develop` via a control-plane PR approved by a CODEOWNER, and only then does
a worker open a feature PR.
