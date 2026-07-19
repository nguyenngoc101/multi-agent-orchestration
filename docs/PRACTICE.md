# PRACTICE — Hands-on exercises

6 exercises from easy to hard. Each has a goal, steps, and what to observe.
Do them on a test repo (can be an empty repo + a few dummy files) to stay safe.

Setup:
```bash
git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh scripts/*.py
# create a few dummy files so there's something to change
mkdir -p src/payment src/web/history db/migrations src/shared
echo "x" > src/payment/.keep; echo "x" > src/web/history/.keep
git add -A && git commit -m "seed"
git switch -c develop        # create the develop branch if missing
```

---

## Exercise 1 — Basic worktree (1 agent)

Goal: understand how a worktree is isolated from the main repo.

```bash
./scripts/new-task.sh demo-a
git worktree list                  # see 2 lines: main repo + ../wt/demo-a
cd ../wt/demo-a
echo "code" > src/payment/refund.txt
git add -A && git commit -m "T: demo-a work"
```

Observe: the main repo does NOT see `refund.txt` (different working dir). But the commit
shares the same `.git`. Run `git log` in both places to see it.

---

## Exercise 2 — Two parallel agents (different scope)

Goal: two worktrees running at once, not touching each other.

```bash
./scripts/new-task.sh feat-payment
./scripts/new-task.sh feat-web
# change src/payment/** in worktree 1, src/web/history/** in worktree 2 — in parallel
```

Observe: `git worktree list` has 3 lines. The two agents change two different file areas,
commit independently, no conflict. This is "real" parallelism.

---

## Exercise 3 — Dependencies waiting (check-registry)

Goal: see `check-registry.py` compute waves and hold back a task with unmet dependencies.

Set `task-registry.json` to:
```json
{"agents":[],"tasks":[
  {"id":"T-1","title":"shared","scope":{"allow":["src/shared/**"]},"depends_on":[],"state":"backlog"},
  {"id":"T-2","title":"pay","scope":{"allow":["src/payment/**"]},"depends_on":["T-1"],"state":"backlog"},
  {"id":"T-3","title":"web","scope":{"allow":["src/web/**"]},"depends_on":["T-1"],"state":"backlog"}
]}
```
```bash
just check-registry
```
Observe: Wave 1 = T-1 (alone); Wave 2 = T-2, T-3 (parallel, after T-1 is done).
Change T-1's state to `merged` and re-run → Wave 1 is now T-2, T-3.

---

## Exercise 4 — Cycle detection

Goal: see the CI-guard block a dependency cycle.

Add to the registry: T-2 `depends_on: ["T-3"]` and T-3 `depends_on: ["T-2"]`.
```bash
just check-registry            # → ERROR: Dependency CYCLE: T-2 -> T-3 -> T-2, exit 1
```
Observe: exit code 1 (CI would fail). This is a task-splitting error, not a code error.

---

## Exercise 5 — A blocked scope violation

Goal: see `enforce-scope.py` block a PR that changes files out of scope.

The registry has T-101 with scope `allow: src/payment/**`, `deny: src/shared/**`, state `in_progress`.
```bash
BASE=$(git rev-parse develop)
git switch -c feature/T-101
echo "ok" > src/payment/ok.txt        # valid
echo "bad" > src/shared/bad.txt       # violation
git add -A && git commit -m "mix"
HEAD=$(git rev-parse HEAD)
python3 scripts/enforce-scope.py --registry task-registry.json --task T-101 --base $BASE --head $HEAD
```
Observe: it reports the `src/shared/bad.txt` violation, exit 1. On real GitHub, this is where
`registry-guard.yml` fails the PR → the worker must STOP and ask a human to re-split the task.

---

## Exercise 6 — Full cycle: feature → develop → release → main

Goal: walk through gitflow once end to end.

```bash
# feature into develop
./scripts/new-task.sh feat-x
cd ../wt/feat-x && echo "x" > src/payment/x.txt
git add -A && git commit -m "feat-x"
git switch develop && git merge --no-ff feature/feat-x

# release cut
git switch -c release/2026.03
# (simulate promotion Dev→SIT→UAT→PROD)

# into main + tag
git switch main && git merge --no-ff release/2026.03 && git tag v2026.03
git switch develop && git merge --no-ff release/2026.03   # back-merge
```
Observe: `main` now points at exactly what "went to PROD"; the tag marks the version; develop
receives everything back from the release. Try `git log --oneline --graph --all` to see the shape.

---

## Extension challenges

- Enable the hooks and try `git commit` while on the `develop` branch → pre-commit blocks it.
- Try `git push origin develop` from a fake feature branch → pre-push blocks it.
- Write more tasks into the registry so there are 3 waves, each with ≥2 parallel tasks.
  Compare against the reference answer: `python3 scripts/check-registry.py examples/task-registry.sample.json`.
- Simulate a "silent" worker: leave a task in `in_progress` forever, and practice writing the
  rule for the orchestrator to free the agent (see ORCHESTRATOR.md "Handling situations").
