#!/usr/bin/env python3
"""
orchestrate.py — dispatcher BÁN TỰ ĐỘNG cho vòng lặp điều phối.

Làm phần cơ khí mà orchestrator (LLM/người) hay phải làm tay:
  1. Hỏi `gh` trạng thái PR của mỗi task đang có branch.
  2. Task nào PR đã MERGED → đề xuất chuyển `state=merged`, giải phóng agent
     (status=idle, current_task=null), và APPEND một dòng vào `task.log`.
  3. In "wave" kế tiếp (task sẵn sàng sau khi dependency đã merged).

KHÔNG merge, KHÔNG push, KHÔNG spawn worker — chỉ đọc trạng thái + cập nhật registry.
Quyết định giao task cho ai (routing theo kind) vẫn do orchestrator (xem ORCHESTRATOR.md).

MẶC ĐỊNH: dry-run (chỉ in đề xuất). Thêm --write để ghi vào registry.
Chỉ phụ thuộc Python 3 stdlib + gh CLI (tùy chọn: có thể nạp pr-status từ --status-json).

Dùng:
  python3 scripts/orchestrate.py                     # dry-run trên task-registry.json
  python3 scripts/orchestrate.py --write             # áp thay đổi
  python3 scripts/orchestrate.py path.json --write
"""
import argparse
import datetime
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

# Tái dùng compute_waves + TERMINAL từ check-registry.py (cùng thư mục).
_spec = importlib.util.spec_from_file_location(
    "check_registry", Path(__file__).with_name("check-registry.py"))
_cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cr)
compute_waves = _cr.compute_waves
TERMINAL = _cr.TERMINAL


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def gh_pr_status(branch):
    """Trả về {'merged': bool, 'state': str} cho branch, hoặc None nếu không có PR/lỗi."""
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
    """PURE: từ registry + trạng thái PR, trả về danh sách transition đề xuất.

    Mỗi transition: {task, from, to, free_agent, note}. Hiện xử lý ca chính:
    PR đã merged → task 'merged' + giải phóng agent giữ task đó."""
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
                "note": f"{state}→merged: PR {branch} đã merged (orchestrate.py)",
            })
    return transitions


def apply(registry, transitions, when=None):
    """Mutate registry theo transitions: đổi state, append task.log, giải phóng agent."""
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
    ap.add_argument("--write", action="store_true", help="ghi thay đổi vào registry (mặc định: dry-run)")
    ap.add_argument("--status-json", help="nạp map {branch: {merged,state}} từ file thay vì gọi gh (test/offline)")
    args = ap.parse_args()

    with open(args.registry, encoding="utf-8") as f:
        registry = json.load(f)

    # Lấy trạng thái PR
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
        print("\n▶ Đề xuất chuyển state:")
        for tr in transitions:
            free = f", giải phóng {tr['free_agent']}" if tr["free_agent"] else ""
            print(f"   - {tr['task']}: {tr['from']}→{tr['to']}{free}")
    else:
        print("\n(không có transition — không PR nào mới merged)")

    if args.write and transitions:
        apply(registry, transitions)
        with open(args.registry, "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"\n✓ Đã ghi {len(transitions)} thay đổi vào {args.registry}.")
    elif transitions:
        print("\n(dry-run — thêm --write để áp)")

    waves, stuck = compute_waves(registry.get("tasks", []))
    print("\n▶ WAVE kế tiếp (task chưa merged):")
    if not waves:
        print("   (không có task nào chạy được)")
    for k, w in enumerate(waves, 1):
        print(f"   Wave {k}: {', '.join(w)}")
    if stuck:
        print(f"\n✗ KẸT (chu trình/dep thiếu): {', '.join(stuck)}")


if __name__ == "__main__":
    main()
