#!/usr/bin/env python3
"""
enforce-scope.py — Chặn cứng ở CI: PR của feature/<task> chỉ được đổi file
nằm trong scope.allow (và không nằm trong scope.deny) của task đó trong registry.

Đây là lớp cưỡng chế "ranh giới file" mà AGENTS.md/WORKER_PROTOCOL chỉ khuyến nghị.
Agent có thể lờ luật mềm; job này thì không lờ được.

Dùng:
  enforce-scope.py --registry task-registry.json --task T-101 --base <sha> --head <sha>
Exit != 0 nếu có file ngoài scope.
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
        print(f"::error::Task {args.task} không có trong registry.")
        sys.exit(1)

    allow = task["scope"]["allow"]
    deny  = task["scope"].get("deny", [])
    files = changed_files(args.base, args.head)

    violations = []
    for f in files:
        if deny and match_any(f, deny):
            violations.append((f, "nằm trong scope.deny"))
        elif not match_any(f, allow):
            violations.append((f, "ngoài scope.allow"))

    print(f"Task {args.task} — allow={allow} deny={deny}")
    print(f"File thay đổi: {len(files)}")
    if violations:
        print("\n✗ VI PHẠM SCOPE:")
        for f, why in violations:
            print(f"   - {f}  ({why})")
        print(f"\n::error::PR đổi {len(violations)} file ngoài scope của {args.task}. "
              "Worker phải DỪNG và báo orchestrator/người để chia lại task.")
        sys.exit(1)

    print("✓ Mọi file thay đổi đều trong scope.")
    sys.exit(0)

if __name__ == "__main__":
    main()
