# Worker runtimes — triggering Codex vs Claude correctly

Maps `agents[].kind` → how the orchestrator *actually* spawns a worker. Learned from a
live run; read alongside "Worker routing" in `orchestrator/prompts/ORCHESTRATOR.md`.

## Principle: Codex by default, Claude as the exception

- **Codex (unlimited)** = the throughput engine → default worker for ordinary tasks.
- **Claude (Pro, scarce)** = orchestrator + reviewer + sensitive/hard tasks → `claude-lead`.

## kind = "codex" — spawn via the plugin, worktree pre-created

```
1. Create the correct feature/* worktree FIRST:
     ./scripts/new-task.sh <task-id>          # → ../wt/<id> on feature/<id>
2. Spawn the Codex worker pointed at that worktree:
     Agent(subagent_type="codex:codex-rescue", prompt=<INPUT JSON + worktree path>)
3. Codex codes + tests within scope, commits, (submit-task → PR).
```

**Two gotchas you MUST know (hit in a live run):**

1. **Do NOT use the harness `isolation:"worktree"` for Codex.** That worktree is
   **auto-cleaned when the first run makes no changes** → a resume loses its workspace.
   Its branch name is also not `feature/*`, so a worker obeying AGENTS.md blocks itself.
   → Always create the `feature/<id>` worktree with `new-task.sh` and point Codex at it.

2. **Codex's sandbox may block `git commit`** (can't create `index.lock`). Then Codex
   writes code/tests fine but can't commit → can't complete `submit-task.sh`.
   → Run Codex in a write-capable mode (e.g. `--sandbox workspace-write` / loosen approval
   for git operations), OR have the orchestrator commit on its behalf, then continue.

## kind = "claude" — sub-agent with the harness worktree

```
Agent(subagent_type="general-purpose", isolation:"worktree", prompt=<INPUT JSON>)
```

Here `isolation:"worktree"` is fine because the Claude sub-agent works + commits within the
turn, so the worktree has changes and isn't auto-cleaned. Use it for escalated tasks
(sensitive/architecture/Codex failed ≥2 times).

## kind = "other"

No direct call channel → the orchestrator sets `assigned`, prints the INPUT JSON, and STOPS
to wait for that human/agent to pick it up. "Available" here is trust in the registry, unverified.

## Check that Codex is ready

```
/codex:setup                        # check the CLI + auth; ready=true means good to go
/codex:setup --enable-review-gate   # (optional) require Claude to review Codex's work before stopping
```
