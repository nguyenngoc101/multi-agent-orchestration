#!/usr/bin/env python3
"""
check-registry.py — Trọng tài tĩnh cho task registry.

Kiểm tra:
  1. Schema tối thiểu (field bắt buộc) + giá trị enum hợp lệ (state/status/kind).
  2. Trùng id (task hoặc agent) → lỗi cứng.
  3. Dependency vòng (chu trình) → lỗi cứng, dừng.
  4. depends_on trỏ tới task không tồn tại → lỗi.
  5. Nhất quán agent ↔ task (assignee/current_task trỏ đúng, status khớp).
  6. Nhật ký task (log[]) đúng cấu trúc — mỗi entry là object có 'note'.
  7. Scope overlap giữa các task đang active → cảnh báo.
  8. Tính "wave": nhóm task chạy song song được ở thời điểm hiện tại.

Không phụ thuộc thư viện ngoài — chạy bằng Python 3 chuẩn.
Dùng: python3 scripts/check-registry.py [đường-dẫn-registry.json]
Exit code != 0 nếu có lỗi cứng (CI dùng được).
"""
import fnmatch
import json
import sys
from collections import defaultdict

TERMINAL = {"merged"}
ACTIVE   = {"assigned", "in_progress", "in_review", "changes_requested"}

# Giữ đồng bộ với orchestrator/schema/task-registry.schema.json
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
        return ["Registry phải là một JSON object."], [], []

    tasks = reg.get("tasks")
    agents = reg.get("agents")
    if not isinstance(tasks, list):
        errors.append("Registry thiếu mảng 'tasks'.")
        tasks = []
    if not isinstance(agents, list):
        errors.append("Registry thiếu mảng 'agents'.")
        agents = []

    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            errors.append(f"Task tại vị trí {index} phải là object.")
            continue
        for key in ("id", "title", "scope", "state"):
            if key not in task:
                errors.append(f"Task thiếu field '{key}': {task.get('id', task)}")
        for key in ("id", "title", "state"):
            if key in task and not isinstance(task[key], str):
                errors.append(f"Task tại vị trí {index} field '{key}' phải là string.")
        scope = task.get("scope")
        if scope is not None and not isinstance(scope, dict):
            errors.append(f"Task {task.get('id')} scope phải là object.")
        elif isinstance(scope, dict):
            allow = scope.get("allow")
            deny = scope.get("deny", [])
            if not isinstance(allow, list) or not all(isinstance(g, str) for g in allow):
                errors.append(f"Task {task.get('id')} scope.allow phải là mảng string.")
            if not isinstance(deny, list) or not all(isinstance(g, str) for g in deny):
                errors.append(f"Task {task.get('id')} scope.deny phải là mảng string.")
        for key in ("depends_on", "requires"):
            value = task.get(key, [])
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                errors.append(f"Task {task.get('id')} {key} phải là mảng string.")
        log = task.get("log", [])
        if not isinstance(log, list):
            errors.append(f"Task {task.get('id')} log phải là mảng.")
        else:
            for entry in log:
                if not isinstance(entry, dict):
                    errors.append(f"Task {task.get('id')} mỗi log entry phải là object.")
                elif not isinstance(entry.get("note"), str) or not entry.get("note"):
                    errors.append(f"Task {task.get('id')} log entry thiếu 'note' (string).")
                else:
                    for key in ("ts", "by"):
                        if key in entry and not isinstance(entry[key], str):
                            errors.append(f"Task {task.get('id')} log.{key} phải là string.")

    for index, agent in enumerate(agents):
        if not isinstance(agent, dict):
            errors.append(f"Agent tại vị trí {index} phải là object.")
            continue
        for key in ("id", "kind", "status"):
            if key in agent and not isinstance(agent[key], str):
                errors.append(f"Agent tại vị trí {index} field '{key}' phải là string.")
        capabilities = agent.get("capabilities")
        if capabilities is not None and (
            not isinstance(capabilities, list)
            or not all(isinstance(value, str) for value in capabilities)
        ):
            errors.append(f"Agent {agent.get('id')} capabilities phải là mảng string.")

    return errors, tasks, agents

def globs_overlap(a_globs, b_globs):
    """Hai tập glob coi là chồng nếu một glob của bên này khớp prefix thư mục của bên kia.
    Xấp xỉ thực dụng: so khớp theo tiền tố thư mục (bỏ ** ở cuối)."""
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
    """Trả về danh sách chu trình (mỗi chu trình là list task id)."""
    graph = {t["id"]: t.get("depends_on", []) for t in tasks}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = defaultdict(int)
    cycles, stack = [], []

    def dfs(u):
        color[u] = GRAY; stack.append(u)
        for v in graph.get(u, []):
            if v not in graph:
                continue  # dep thiếu — báo riêng
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
    """Topo-sort theo lớp: wave[k] = task sẵn sàng khi mọi wave trước đã merged.
    Chỉ tính trên task chưa merged; task merged coi như đã hoàn thành."""
    done = {t["id"] for t in tasks if t["state"] in TERMINAL}
    remaining = {t["id"]: set(t.get("depends_on", [])) for t in tasks if t["state"] not in TERMINAL}
    waves = []
    while remaining:
        ready = [tid for tid, deps in remaining.items() if deps <= done]
        if not ready:
            break  # còn lại đều kẹt (chu trình / dep thiếu) — đã báo ở nơi khác
        waves.append(sorted(ready))
        for tid in ready:
            done.add(tid); del remaining[tid]
    return waves, sorted(remaining.keys())

def validate_agents(agents, tasks, task_ids, warnings):
    """Validate pool agent + kiểm tra nhất quán hai chiều với task.
    Trả về list lỗi cứng; thêm cảnh báo vào `warnings` (in-place)."""
    errors = []
    by_id = {}
    for a in agents:
        for k in ("id", "kind", "capabilities", "status"):
            if k not in a:
                errors.append(f"Agent thiếu field '{k}': {a.get('id', a)}")
        aid = a.get("id")
        if aid is not None:
            if aid in by_id:
                errors.append(f"Trùng agent id '{aid}' — mỗi agent phải có id duy nhất.")
            by_id[aid] = a
        if "status" in a and a["status"] not in AGENT_STATUS:
            errors.append(f"Agent {aid} status '{a['status']}' không hợp lệ "
                          f"(hợp lệ: {', '.join(sorted(AGENT_STATUS))}).")
        if "kind" in a and a["kind"] not in AGENT_KINDS:
            errors.append(f"Agent {aid} kind '{a['kind']}' không hợp lệ "
                          f"(hợp lệ: {', '.join(sorted(AGENT_KINDS))}).")
        ct = a.get("current_task")
        if ct is not None and ct not in task_ids:
            errors.append(f"Agent {aid} current_task '{ct}' không tồn tại trong tasks.")
        # Nhất quán status ↔ current_task
        if a.get("status") == "busy" and ct is None:
            warnings.append(f"Agent {aid} status=busy nhưng current_task=null.")
        if a.get("status") == "idle" and ct is not None:
            warnings.append(f"Agent {aid} status=idle nhưng vẫn giữ current_task={ct}.")

    # Nhất quán ngược: task.assignee ↔ agent tồn tại, và khớp current_task
    for t in tasks:
        assignee = t.get("assignee")
        if assignee is not None and assignee not in by_id:
            errors.append(f"Task {t.get('id')} assignee '{assignee}' không có trong agents.")
        elif assignee is not None:
            ct = by_id[assignee].get("current_task")
            if ct != t.get("id"):
                warnings.append(
                    f"Task {t.get('id')} assignee={assignee} nhưng agent đó "
                    f"current_task={ct} — hai chiều lệch nhau.")
        if t.get("state") == "blocked" and not t.get("blocked_reason"):
            warnings.append(f"Task {t.get('id')} state=blocked nhưng thiếu blocked_reason.")
        if t.get("state") in ACTIVE and not t.get("assignee"):
            warnings.append(f"Task {t.get('id')} đang active nhưng chưa có assignee.")
    return errors


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "task-registry.json"
    try:
        reg = load(path)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"✗ Không đọc được registry '{path}': {exc}")
        sys.exit(1)

    errors, tasks, agents = validate_structure(reg)
    warnings = []

    if errors:
        print("=" * 60)
        print(f"REGISTRY CHECK: {path}")
        print("=" * 60)
        print("\n✗  LỖI CỨNG:")
        for error in errors:
            print("   -", error)
        print("\nKẾT QUẢ: FAIL")
        sys.exit(1)

    ids = {t["id"] for t in tasks}

    # 1. field bắt buộc + enum + trùng id (task)
    seen = set()
    for t in tasks:
        tid = t.get("id")
        if tid is not None:
            if tid in seen:
                errors.append(f"Trùng task id '{tid}' — mỗi task phải có id duy nhất.")
            seen.add(tid)
        if "state" in t and t["state"] not in TASK_STATES:
            errors.append(f"Task {tid} state '{t['state']}' không hợp lệ "
                          f"(hợp lệ: {', '.join(sorted(TASK_STATES))}).")

    # 2. depends_on trỏ tới task không tồn tại
    for t in tasks:
        for d in t.get("depends_on", []):
            if d not in ids:
                errors.append(f"Task {t['id']} depends_on '{d}' không tồn tại")

    # 3. chu trình
    for cyc in detect_cycles(tasks):
        errors.append("Dependency VÒNG: " + " → ".join(cyc))

    # 3b. validate agents + nhất quán agent ↔ task
    errors += validate_agents(agents, tasks, ids, warnings)

    # 4. scope overlap giữa task đang active
    active = [t for t in tasks if t["state"] in ACTIVE]
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            ov = globs_overlap(a["scope"]["allow"], b["scope"]["allow"])
            if ov:
                warnings.append(
                    f"Scope CHỒNG giữa {a['id']} và {b['id']} (đang active): "
                    f"{ov[0]} ↔ {ov[1]} — nguy cơ giẫm file, nên nối tiếp hóa.")

    # 5. wave
    waves, stuck = compute_waves(tasks)

    # ── in kết quả ───────────────────────────────────────────────
    print("=" * 60)
    print(f"REGISTRY CHECK: {path}")
    print("=" * 60)

    if warnings:
        print("\n⚠  CẢNH BÁO:")
        for w in warnings: print("   -", w)
    if errors:
        print("\n✗  LỖI CỨNG:")
        for e in errors: print("   -", e)

    print("\n▶ WAVE song song (task chưa merged):")
    if not waves:
        print("   (không có task nào chạy được)")
    for k, w in enumerate(waves, 1):
        print(f"   Wave {k}: {', '.join(w)}   ← {len(w)} task song song")
    if stuck:
        print(f"\n✗ KẸT (chu trình/dep thiếu): {', '.join(stuck)}")

    print()
    if errors or stuck:
        print("KẾT QUẢ: FAIL")
        sys.exit(1)
    print("KẾT QUẢ: OK" + ("  (có cảnh báo)" if warnings else ""))
    sys.exit(0)

if __name__ == "__main__":
    main()
