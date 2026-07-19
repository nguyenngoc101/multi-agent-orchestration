#!/usr/bin/env python3
"""
enforce-scope.py — hard gate in CI: a feature/<task> PR may only change files
inside that task's scope.allow (and not in scope.deny) per the registry.

This is the enforcement layer for the "file boundary" that AGENTS.md/WORKER_PROTOCOL
only recommend. An agent can ignore soft rules; this job cannot be ignored.

Usage:
  enforce-scope.py --registry task-registry.json --task T-101 --base <sha> --head <sha>
Exit != 0 if any file is out of scope.
"""
import argparse, json, subprocess, sys, fnmatch

def changed_files(base, head):
    # Disable rename collapsing so both the old and new path are checked.
    # Otherwise moving an out-of-scope file into an allowed directory only
    # reports the destination and silently modifies the source scope.
    out = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", f"{base}...{head}"],
        capture_output=True, text=True, check=True).stdout
    return [l for l in out.splitlines() if l.strip()]

def match_any(path, globs):
    return any(fnmatch.fnmatch(path, g) or path.startswith(g.rstrip("*").rstrip("/") + "/")
               for g in globs)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    args = ap.parse_args()

    reg = json.load(open(args.registry))
    task = next((t for t in reg["tasks"] if t["id"] == args.task), None)
    if task is None:
        print(f"::error::Task {args.task} not found in the registry.")
        sys.exit(1)

    allow = task["scope"]["allow"]
    deny  = task["scope"].get("deny", [])
    files = changed_files(args.base, args.head)

    violations = []
    for f in files:
        if deny and match_any(f, deny):
            violations.append((f, "in scope.deny"))
        elif not match_any(f, allow):
            violations.append((f, "outside scope.allow"))

    print(f"Task {args.task} — allow={allow} deny={deny}")
    print(f"Files changed: {len(files)}")
    if violations:
        print("\n✗ SCOPE VIOLATIONS:")
        for f, why in violations:
            print(f"   - {f}  ({why})")
        print(f"\n::error::PR changes {len(violations)} file(s) outside {args.task}'s scope. "
              "The worker must STOP and tell the orchestrator/human to re-split the task.")
        sys.exit(1)

    print("✓ All changed files are within scope.")
    sys.exit(0)

if __name__ == "__main__":
    main()
