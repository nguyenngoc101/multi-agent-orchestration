# justfile — the SINGLE point defining stack commands. Switching stacks = edit only this.
# Install just: https://github.com/casey/just  (or use an equivalent Makefile)
#
# The recipes below check this repository's own tooling. When embedding this workflow
# into an application repo, extend them with your stack's commands:
#   Java/Maven:   mvn -q spotless:check | test | package
#   Node:         npm run lint | test | build
#   Go:           golangci-lint run | go test ./... | go build ./...
#   Python:       ruff check . | pytest | python -m build

# Install dependencies for a new worktree (each worktree installs its own — files outside git aren't shared)
bootstrap:
    @echo "No dependencies beyond the Python 3 standard library."

lint:
    PYTHONPYCACHEPREFIX=.cache/pyc python3 -m compileall -q scripts tests
    bash -n scripts/*.sh .githooks/*
    python3 scripts/check-skill-sync.py

test:
    python3 -m unittest discover -s tests -v

build:
    python3 scripts/check-registry.py task-registry.json

# Check the registry (cycles, scope overlap, print waves)
check-registry:
    python3 scripts/check-registry.py task-registry.json

# Print the current parallel waves (quick view)
waves:
    python3 scripts/check-registry.py task-registry.json

# Semi-auto dispatcher (dry-run): PR merged → propose state changes + print next wave
orchestrate:
    python3 scripts/orchestrate.py task-registry.json
