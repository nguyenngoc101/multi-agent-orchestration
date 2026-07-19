# AGENTS.md — Working rules for AI agents (MANDATORY)

Read this file BEFORE running any git command. Violations get blocked by hooks /
branch protection — but you must comply on your own, not rely on being blocked.

## 0. Supreme principles

- You ONLY work in your current worktree, on your `feature/<task>` branch.
- You ONLY merge (via PR) into `develop`.
- You NEVER touch: `main`, `release/*`, `hotfix/*`.
  These branches are human-controlled (cutting releases, approving PROD, hotfixes).

## 1. Branch boundaries

| Branch | You may | Notes |
|---|---|---|
| `feature/<task>` | Full control (your branch) | 1 task = 1 branch = 1 worktree |
| `develop` | Merge in via PR only | Integration branch |
| `main` | ❌ Forbidden | = PROD, human-owned |
| `release/*` | ❌ Forbidden | Stabilization, human-owned |
| `hotfix/*` | ❌ Forbidden | PROD patch, human-owned |

## 2. File boundaries (scope)

- Only change files within the scope assigned in your prompt/issue.
- If you need to change a file OUTSIDE scope: STOP, report it in the PR/issue, wait
  for confirmation. Don't spill edits into another module — that's the source of
  conflicts between agents.

## 3. Workflow

1. Create the worktree + branch with the standard script (do NOT type
   `git worktree add` yourself):
   ```
   ./scripts/new-task.sh <task-name>
   ```
2. Code, commit small and often, with clear messages.
3. Before opening a PR, run the submit script (it rebases + checks + pushes):
   ```
   ./scripts/submit-task.sh <task-name>
   ```
4. Open a PR **targeting `develop`**, filling in the template.
5. After the PR is merged, clean up:
   ```
   ./scripts/cleanup-task.sh <task-name>
   ```

## 4. Absolutely forbidden commands

- `git checkout main` / `develop` / `release/*` / `hotfix/*` to commit onto them
- `git push` straight to `main` / `develop` / `release/*` / `hotfix/*`
- `git push --force` / `--force-with-lease` to any shared branch
- `git stash` (the stash is shared across the whole repo between worktrees — easy to pop the wrong thing)
- local `git config` to change user/email (config is shared repo-wide — use the
  `GIT_AUTHOR_*` environment variables the script sets up)
- `git worktree remove --force` while there are uncommitted changes
- Rewriting the history of a pushed branch (`rebase -i` then force push)

## 5. Rebase & conflicts

- Rebase onto `origin/develop` BEFORE pushing and before any long task:
  ```
  git fetch origin && git rebase origin/develop
  ```
- Rebase early, rebase often: small conflicts are easier than accumulated ones.
- Prefer `rebase` over `merge` to keep your branch history straight.
- If a conflict exceeds your scope (touches another module's files): STOP, report to a human.

## 6. Before opening a PR — self-check checklist

- [ ] Rebased onto the latest `origin/develop`
- [ ] Lint green:  `<LINT_CMD>`
- [ ] Tests green: `<TEST_CMD>`
- [ ] Build green: `<BUILD_CMD>`
- [ ] Only touched files within scope
- [ ] Clear commit messages, PR describes: what, which files, how to test

> `<LINT_CMD>` / `<TEST_CMD>` / `<BUILD_CMD>` are defined in the repo's `justfile`
> or `Makefile` (see section 7). Don't hardcode a specific stack's commands.

## 7. Build/test/lint commands — through a single entry point

The repo defines every command via `just` (or `make`). You ONLY call the task name,
never a stack tool directly:

```
just lint      # or: make lint
just test      # or: make test
just build     # or: make build
```

If there's no `justfile`/`Makefile` yet, ask a human to add one — don't guess stack commands.

## 8. Environment-based config

- Do NOT hardcode environment values (DB URL, endpoint, secret) into the code or
  by branch. Dev/SIT/UAT/PROD config lives outside the code (environment variables /
  config store), injected at deploy time. The same artifact runs in every environment.
