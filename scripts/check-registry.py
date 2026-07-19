#!/usr/bin/env python3
"""
check-registry.py — static arbiter for the task registry.

Checks:
  1. Minimal schema (required fields) + valid enum values (state/status/kind).
  2. Duplicate id (task or agent) → hard error.
  3. Dependency cycle → hard error, stop.
  4. depends_on pointing to a non-existent task → error.
  5. agent <-> task consistency (assignee/current_task point correctly, status matches).
  6. Task log[] well-formed — each entry is an object with 'note'.
  7. Scope overlap between active tasks → warning.
  8. Compute "waves": groups of tasks that can run in parallel right now.

No third-party dependencies — runs on plain Python 3.
Usage: python3 scripts/check-registry.py [path-to-registry.json]
Exit code != 0 on a hard error (usable in CI).
"""
import fnmatch
import json
import sys
from collections import defaultdict

TERMINAL = {"merged"}
ACTIVE   = {"assigned", "in_progress", "in_review", "changes_requested"}

# Keep in sync with orchestrator/schema/task-registry.schema.json
TASK_STATES   = {"backlog", "assigned", "in_progress", "in_review",
                 "changes_requested", "merged", "blocked"}
AGENT_STATUS  = {"idle", "busy", "offline"}
AGENT_KINDS   = {"claude", "codex", "other"}

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_structure(reg):
    """Validate types before graph checks so malformed input reports clean errors."""
    errors = []
    if not isinstance(reg, dict):
        return ["Registry must be a JSON object."], [], []

    tasks = reg.get("tasks")
    agents = reg.get("agents")
    if not isinstance(tasks, list):
        errors.append("Registry is missing the 'tasks' array.")
        tasks = []
    if not isinstance(agents, list):
        errors.append("Registry is missing the 'agents' array.")
        agents = []

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"Task at index {index} must be an object.")
            continue
        for key in ("id", "title", "scope", "state"):
            if key not in task:
                errors.append(f"Task missing field '{key}': {task.get('id', task)}")
        for key in ("id", "title", "state"):
            if key in task and not isinstance(task[key], str):
                errors.append(f"Task at index {index} field '{key}' must be a string.")
        scope = task.get("scope")
        if scope is not None and not isinstance(scope, dict):
            errors.append(f"Task {task.get('id')} scope must be an object.")
        elif isinstance(scope, dict):
            allow = scope.get("allow")
            deny = scope.get("deny", [])
            if not isinstance(allow, list) or not all(isinstance(g, str) for g in allow):
                errors.append(f"Task {task.get('id')} scope.allow must be an array of strings.")
            if not isinstance(deny, list) or not all(isinstance(g, str) for g in deny):
                errors.append(f"Task {task.get('id')} scope.deny must be an array of strings.")
        for key in ("depends_on", "requires"):
            value = task.get(key, [])
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                errors.append(f"Task {task.get('id')} {key} must be an array of strings.")
        log = task.get("log", [])
        if not isinstance(log, list):
            errors.append(f"Task {task.get('id')} log must be an array.")
        else:
            for entry in log:
                if not isinstance(entry, dict):
                    errors.append(f"Task {task.get('id')} each log entry must be an object.")
                elif not isinstance(entry.get("note"), str) or not entry.get("note"):
                    errors.append(f"Task {task.get('id')} log entry missing 'note' (string).")
                else:
                    for key in ("ts", "by"):
                        if key in entry and not isinstance(entry[key], str):
                            errors.append(f"Task {task.get('id')} log.{key} must be a string.")

    for index, agent in enumerate(agents):
        if not isinstance(agent, dict):
            errors.append(f"Agent at index {index} must be an object.")
            continue
        for key in ("id", "kind", "status"):
            if key in agent and not isinstance(agent[key], str):
                errors.append(f"Agent at index {index} field '{key}' must be a string.")
        capabilities = agent.get("capabilities")
        if capabilities is not None and (
            not isinstance(capabilities, list)
            or not all(isinstance(value, str) for value in capabilities)
        ):
            errors.append(f"Agent {agent.get('id')} capabilities must be an array of strings.")

    return errors, tasks, agents

def globs_overlap(a_globs, b_globs):
    """Two glob sets overlap if a glob on one side matches the directory prefix of the other.
    Pragmatic approximation: compare by directory prefix (dropping trailing **)."""
    def norm(g):
        return g.rstrip("*").rstrip("/")
    for a in a_globs:
        na = norm(a)
        for b in b_globs:
            nb = norm(b)
            if na == nb or na.startswith(nb + "/") or nb.startswith(na + "/") \
               or fnmatch.fnmatch(na, b) or fnmatch.fnmatch(nb, a):
                return (a, b)
    return None

def detect_cycles(tasks):
    """Return a list of cycles (each cycle is a list of task ids)."""
    graph = {t["id"]: t.get("depends_on", []) for t in tasks}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = defaultdict(int)
    cycles, stack = [], []

    def dfs(u):
        color[u] = GRAY; stack.append(u)
        for v in graph.get(u, []):
            if v not in graph:
                continue  # missing dep — reported separately
            if color[v] == GRAY:
                i = stack.index(v)
                cycles.append(stack[i:] + [v])
            elif color[v] == WHITE:
                dfs(v)
        color[u] = BLACK; stack.pop()

    for n in graph:
        if color[n] == WHITE:
            dfs(n)
    return cycles

def compute_waves(tasks):
    """Layered topo-sort: wave[k] = tasks ready once every earlier wave is merged.
    Computed only over unmerged tasks; merged tasks count as done."""
    done = {t["id"] for t in tasks if t["state"] in TERMINAL}
    remaining = {t["id"]: set(t.get("depends_on", [])) for t in tasks if t["state"] not in TERMINAL}
    waves = []
    while remaining:
        ready = [tid for tid, deps in remaining.items() if deps <= done]
        if not ready:
            break  # the rest are stuck (cycle / missing dep) — reported elsewhere
        waves.append(sorted(ready))
        for tid in ready:
            done.add(tid); del remaining[tid]
    return waves, sorted(remaining.keys())

def validate_agents(agents, tasks, task_ids, warnings):
    """Validate the agent pool + check two-way consistency with tasks.
    Returns a list of hard errors; appends warnings to `warnings` (in place)."""
    errors = []
    by_id = {}
    for a in agents:
        for k in ("id", "kind", "capabilities", "status"):
            if k not in a:
                errors.append(f"Agent missing field '{k}': {a.get('id', a)}")
        aid = a.get("id")
        if aid is not None:
            if aid in by_id:
                errors.append(f"Duplicate agent id '{aid}' — each agent must have a unique id.")
            by_id[aid] = a
        if "status" in a and a["status"] not in AGENT_STATUS:
            errors.append(f"Agent {aid} status '{a['status']}' is invalid "
                          f"(valid: {', '.join(sorted(AGENT_STATUS))}).")
        if "kind" in a and a["kind"] not in AGENT_KINDS:
            errors.append(f"Agent {aid} kind '{a['kind']}' is invalid "
                          f"(valid: {', '.join(sorted(AGENT_KINDS))}).")
        ct = a.get("current_task")
        if ct is not None and ct not in task_ids:
            errors.append(f"Agent {aid} current_task '{ct}' does not exist in tasks.")
        # status <-> current_task consistency
        if a.get("status") == "busy" and ct is None:
            warnings.append(f"Agent {aid} status=busy but current_task=null.")
        if a.get("status") == "idle" and ct is not None:
            warnings.append(f"Agent {aid} status=idle but still holds current_task={ct}.")

    # Reverse consistency: task.assignee <-> agent exists, and matches current_task
    for t in tasks:
        assignee = t.get("assignee")
        if assignee is not None and assignee not in by_id:
            errors.append(f"Task {t.get('id')} assignee '{assignee}' not found in agents.")
        elif assignee is not None:
            ct = by_id[assignee].get("current_task")
            if ct != t.get("id"):
                warnings.append(
                    f"Task {t.get('id')} assignee={assignee} but that agent's "
                    f"current_task={ct} — two-way mismatch.")
        if t.get("state") == "blocked" and not t.get("blocked_reason"):
            warnings.append(f"Task {t.get('id')} state=blocked but missing blocked_reason.")
        if t.get("state") in ACTIVE and not t.get("assignee"):
            warnings.append(f"Task {t.get('id')} is active but has no assignee.")
    return errors


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "task-registry.json"
    try:
        reg = load(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"✗ Could not read registry '{path}': {exc}")
        sys.exit(1)

    errors, tasks, agents = validate_structure(reg)
    warnings = []

    if errors:
        print("=" * 60)
        print(f"REGISTRY CHECK: {path}")
        print("=" * 60)
        print("\n✗  HARD ERRORS:")
        for error in errors:
            print("   -", error)
        print("\nRESULT: FAIL")
        sys.exit(1)

    ids = {t["id"] for t in tasks}

    # 1. required fields + enum + duplicate id (task)
    seen = set()
    for t in tasks:
        tid = t.get("id")
        if tid is not None:
            if tid in seen:
                errors.append(f"Duplicate task id '{tid}' — each task must have a unique id.")
            seen.add(tid)
        if "state" in t and t["state"] not in TASK_STATES:
            errors.append(f"Task {tid} state '{t['state']}' is invalid "
                          f"(valid: {', '.join(sorted(TASK_STATES))}).")

    # 2. depends_on pointing to a non-existent task
    for t in tasks:
        for d in t.get("depends_on", []):
            if d not in ids:
                errors.append(f"Task {t['id']} depends_on '{d}' does not exist")

    # 3. cycles
    for cyc in detect_cycles(tasks):
        errors.append("Dependency CYCLE: " + " -> ".join(cyc))

    # 3b. validate agents + agent <-> task consistency
    errors += validate_agents(agents, tasks, ids, warnings)

    # 4. scope overlap between active tasks
    active = [t for t in tasks if t["state"] in ACTIVE]
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            ov = globs_overlap(a["scope"]["allow"], b["scope"]["allow"])
            if ov:
                warnings.append(
                    f"Scope OVERLAP between {a['id']} and {b['id']} (active): "
                    f"{ov[0]} <-> {ov[1]} — risk of clobbering files; serialize them.")

    # 5. waves
    waves, stuck = compute_waves(tasks)

    # ── print results ────────────────────────────────────────────
    print("=" * 60)
    print(f"REGISTRY CHECK: {path}")
    print("=" * 60)

    if warnings:
        print("\n⚠  WARNINGS:")
        for w in warnings: print("   -", w)
    if errors:
        print("\n✗  HARD ERRORS:")
        for e in errors: print("   -", e)

    print("\n▶ Parallel WAVES (unmerged tasks):")
    if not waves:
        print("   (no runnable tasks)")
    for k, w in enumerate(waves, 1):
        print(f"   Wave {k}: {', '.join(w)}   ← {len(w)} tasks in parallel")
    if stuck:
        print(f"\n✗ STUCK (cycle/missing dep): {', '.join(stuck)}")

    print()
    if errors or stuck:
        print("RESULT: FAIL")
        sys.exit(1)
    print("RESULT: OK" + ("  (with warnings)" if warnings else ""))
    sys.exit(0)

if __name__ == "__main__":
    main()
