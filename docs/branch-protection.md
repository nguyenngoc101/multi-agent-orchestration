# Branch protection — the UN-BYPASSABLE gate

Local hooks (`.githooks/`) are the first defense layer, but an agent (or human) can skip
them with `--no-verify`. The real enforcement lives on the SERVER. Configure it once.

## Principles

| Branch | Direct push | Require PR | Require CI green | Require review | Who may merge |
|---|---|---|---|---|---|
| `main` | ❌ | ✓ | ✓ | ✓ (human) | Human / release manager only |
| `release/*` | ❌ | ✓ | ✓ | ✓ (human) | Human only |
| `develop` | ❌ | ✓ | ✓ | ✓ or auto | Agent via PR, after CI green |
| `hotfix/*` | ❌ | ✓ | ✓ | ✓ (human) | Human only |
| `feature/*` | ✓ (agent) | — | — | — | (agent's own branch) |

Core point: agents are ONLY allowed to create/push `feature/*` and open PRs into
`develop`. The server rejects every other branch — even if the agent tries `--no-verify`.

## GitHub — Rulesets (recommended) or Branch protection

For each target (`main`, `develop`, `release/*`, `hotfix/*`):
- Require a pull request before merging (on; require ≥1 approval for main/release)
- Require status checks to pass → select the CI checks (lint/test/build)
- Require branches to be up to date before merging
- Block force pushes
- Restrict who can push → the human team only (exclude agent accounts) for main/release/hotfix
- (main/release) Require review from Code Owners if using CODEOWNERS
- Enable the merge queue for `develop`; required workflows must listen for `merge_group`

Agent permissions: create a machine account / token for agents, granting only enough to
push `feature/*` and create PRs. Do NOT grant admin/bypass.

Replace the sample owner in `.github/CODEOWNERS` with a real team/user. The registry
control-plane must go through a CODEOWNER-approved PR before the corresponding feature
branch is created.

> Shortcut: `./scripts/setup-branch-protection.sh` applies most of this via `gh api`
> (dry-run by default; `--apply` to apply). Team push-restriction and the merge queue
> still need the UI.

## GitLab — Protected branches + Push rules

- Settings → Repository → Protected branches:
  - `main`, `release/*`, `hotfix/*`: Allowed to push = No one; Allowed to merge = Maintainers (human)
  - `develop`: Allowed to push = No one; Allowed to merge = Developers+ (via MR)
- Settings → Merge requests: enable "Pipelines must succeed" and "All discussions resolved"
- Push Rules: enable "Do not allow users to remove tags", block force push
- Wildcard `feature/*`: leave default (agents can push)

## Bitbucket / others

Same principles: main/release/hotfix = merge-only via PR, CI required, block force push,
limit who can merge. Apply the same permission matrix as the table above.

## CI gate (described, tool-agnostic)

A PR into `develop` (and into `main`/`release`) must run 3 jobs, all green before merge:

1. `lint`  — calls `just lint`  (or `make lint`)
2. `test`  — calls `just test`  (or `make test`)
3. `build` — calls `just build` (or `make build`)

The pipeline ONLY calls these tasks, never writes stack commands itself — so the CI config
is identical regardless of the repo's language; switching stacks means editing `justfile`.

## Deploy gate (4 environments)

- Dev  : auto-deploy when the release branch updates.
- SIT  : auto or 1-click; runs integration tests on the SAME artifact.
- UAT  : deploy for acceptance; requires a tester's sign-off.
- PROD : **manual approval gate** — only an authorized approver (with a who/when log for
         audit). Agents are NOT in this flow.

The same artifact is promoted through all 4 envs; no rebuild between environments.
