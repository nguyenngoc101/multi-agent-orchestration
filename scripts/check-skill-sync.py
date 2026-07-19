#!/usr/bin/env python3
"""Fail when the distributable Claude skill drifts from root source files."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / ".claude" / "skills" / "multi-agent-orchestration"
MIRRORED = (
    "AGENTS.md",
    "docs/WORKFLOW.md",
    "docs/branch-protection.md",
    "orchestrator/prompts/ORCHESTRATOR.md",
    "orchestrator/prompts/WORKER_PROTOCOL.md",
    "orchestrator/schema/task-registry.schema.json",
    "scripts/check-registry.py",
    "scripts/cleanup-task.sh",
    "scripts/enforce-scope.py",
    "scripts/new-task.sh",
    "scripts/submit-task.sh",
)


def main():
    drifted = [path for path in MIRRORED if (ROOT / path).read_bytes() != (SKILL / path).read_bytes()]
    if drifted:
        print("Skill copy is out of sync:", file=sys.stderr)
        for path in drifted:
            print(f"  - {path}", file=sys.stderr)
        return 1
    print("✓ Skill copy in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
