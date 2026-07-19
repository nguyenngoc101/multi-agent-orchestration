#!/usr/bin/env python3
"""
orchestrate.py — SEMI-AUTOMATIC dispatcher for the orchestration loop.

Does the mechanical part the orchestrator (LLM/human) otherwise does by hand:
  1. Ask `gh` for the PR status of every task that has a branch.
  2. For any task whose PR is MERGED → propose state=merged, free the agent
     (status=idle, current_task=null), and append a line to task.log.
  3. Print the next "wave" (tasks ready once their dependencies are merged).

Does NOT merge, push, or spawn workers — only reads status + updates the registry.
Deciding who gets a task (routing by kind) stays with the orchestrator (see ORCHESTRATOR.md).

DEFAULT: dry-run (only prints proposals). Add --write to update the registry.
Depends only on Python 3 stdlib + the gh CLI (optionally load PR status via --status-json).

Usage:
  python3 scripts/orchestrate.py                     # dry-run on task-registry.json
  python3 scripts/orchestrate.py --write             # apply changes
  python3 scripts/orchestrate.py path.json --write
"""
import argparse
import datetime
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

# Reuse compute_waves + TERMINAL from check-registry.py (same directory).
_spec = importlib.util.spec_from_file_location(
    "check_registry", Path(__file__).with_name("check-registry.py"))
_cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cr)
compute_waves = _cr.compute_waves
TERMINAL = _cr.TERMINAL


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def gh_pr_status(branch):
    """Return {'merged': bool, 'state': str} for a branch, or None if no PR/error."""
    try:
        out = subprocess.run(
            ["gh", "pr", "view", branch, "--json", "state,mergedAt"],
            capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None
    return {"merged": bool(data.get("mergedAt")), "state": data.get("state")}


def plan(registry, pr_status_by_branch):
    """PURE: from registry + PR status, return the list of proposed transitions.

    Each transition: {task, from, to, free_agent, note}. Currently handles the main
    case: PR merged → task 'merged' + free the agent holding that task."""
    transitions = []
    for task in registry.get("tasks", []):
        branch = task.get("branch")
        state = task.get("state")
        if not branch or state in TERMINAL:
            continue
        st = pr_status_by_branch.get(branch)
        if st and st.get("merged"):
            transitions.append({
                "task": task.get("id"),
                "from": state,
                "to": "merged",
                "free_agent": task.get("assignee"),
                "note": f"{state}->merged: PR {branch} was merged (orchestrate.py)",
            })
    return transitions


def apply(registry, transitions, when=None):
    """Mutate registry per transitions: change state, append task.log, free the agent."""
    when = when or now_iso()
    by_id = {t.get("id"): t for t in registry.get("tasks", [])}
    agents = {a.get("id"): a for a in registry.get("agents", [])}
    for tr in transitions:
        task = by_id.get(tr["task"])
        if task is None:
            continue
        task["state"] = tr["to"]
        task.setdefault("log", []).append(
            {"ts": when, "by": "orchestrate", "note": tr["note"]})
        agent = agents.get(tr["free_agent"])
        if agent is not None and agent.get("current_task") == tr["task"]:
            agent["status"] = "idle"
            agent["current_task"] = None
    return registry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("registry", nargs="?", default="task-registry.json")
    ap.add_argument("--write", action="store_true", help="write changes to the registry (default: dry-run)")
    ap.add_argument("--status-json", help="load a {branch: {merged,state}} map from a file instead of calling gh (test/offline)")
    args = ap.parse_args()

    with open(args.registry, encoding="utf-8") as f:
        registry = json.load(f)

    # Get PR status
    if args.status_json:
        with open(args.status_json, encoding="utf-8") as f:
            pr_status = json.load(f)
    else:
        pr_status = {}
        for task in registry.get("tasks", []):
            br = task.get("branch")
            if br and task.get("state") not in TERMINAL:
                st = gh_pr_status(br)
                if st:
                    pr_status[br] = st

    transitions = plan(registry, pr_status)

    print("=" * 60)
    print(f"ORCHESTRATE: {args.registry}  ({'WRITE' if args.write else 'dry-run'})")
    print("=" * 60)
    if transitions:
        print("\n▶ Proposed state changes:")
        for tr in transitions:
            free = f", free {tr['free_agent']}" if tr["free_agent"] else ""
            print(f"   - {tr['task']}: {tr['from']}->{tr['to']}{free}")
    else:
        print("\n(no transitions — no newly merged PR)")

    if args.write and transitions:
        apply(registry, transitions)
        with open(args.registry, "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\n✓ Wrote {len(transitions)} change(s) to {args.registry}.")
    elif transitions:
        print("\n(dry-run — add --write to apply)")

    waves, stuck = compute_waves(registry.get("tasks", []))
    print("\n▶ Next WAVES (unmerged tasks):")
    if not waves:
        print("   (no runnable tasks)")
    for k, w in enumerate(waves, 1):
        print(f"   Wave {k}: {', '.join(w)}")
    if stuck:
        print(f"\n✗ STUCK (cycle/missing dep): {', '.join(stuck)}")


if __name__ == "__main__":
    main()
