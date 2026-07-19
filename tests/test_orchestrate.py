import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("orchestrate", ROOT / "scripts" / "orchestrate.py")
ORCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORCH)


def sample_registry():
    return {
        "agents": [
            {"id": "codex-1", "kind": "codex", "capabilities": ["frontend"],
             "status": "busy", "current_task": "T-102"},
        ],
        "tasks": [
            {"id": "T-101", "title": "a", "scope": {"allow": ["src/a/**"]},
             "state": "backlog", "depends_on": []},
            {"id": "T-102", "title": "b", "scope": {"allow": ["src/b/**"]},
             "state": "in_review", "assignee": "codex-1", "branch": "feature/T-102",
             "depends_on": []},
            {"id": "T-103", "title": "c", "scope": {"allow": ["db/**"]},
             "state": "backlog", "depends_on": ["T-101"]},
        ],
    }


class OrchestrateTests(unittest.TestCase):
    def test_plan_proposes_merge_and_frees_agent(self):
        reg = sample_registry()
        transitions = ORCH.plan(reg, {"feature/T-102": {"merged": True, "state": "MERGED"}})
        self.assertEqual(1, len(transitions))
        tr = transitions[0]
        self.assertEqual("T-102", tr["task"])
        self.assertEqual("merged", tr["to"])
        self.assertEqual("codex-1", tr["free_agent"])

    def test_plan_ignores_open_pr(self):
        reg = sample_registry()
        transitions = ORCH.plan(reg, {"feature/T-102": {"merged": False, "state": "OPEN"}})
        self.assertEqual([], transitions)

    def test_plan_ignores_task_without_branch(self):
        reg = sample_registry()
        # T-101 has no branch → never proposed even if some branch is merged.
        transitions = ORCH.plan(reg, {"feature/T-999": {"merged": True}})
        self.assertEqual([], transitions)

    def test_apply_sets_state_frees_agent_and_logs(self):
        reg = sample_registry()
        transitions = ORCH.plan(reg, {"feature/T-102": {"merged": True}})
        ORCH.apply(reg, transitions, when="2026-07-19T00:00:00Z")
        t102 = next(t for t in reg["tasks"] if t["id"] == "T-102")
        agent = reg["agents"][0]
        self.assertEqual("merged", t102["state"])
        self.assertEqual("idle", agent["status"])
        self.assertIsNone(agent["current_task"])
        self.assertEqual("2026-07-19T00:00:00Z", t102["log"][-1]["ts"])
        self.assertEqual("orchestrate", t102["log"][-1]["by"])

    def test_apply_then_wave_unlocks_downstream(self):
        # After T-101 merges, T-103 (depends_on T-101) should enter a wave.
        reg = sample_registry()
        reg["tasks"][0]["state"] = "merged"  # T-101 done
        waves, stuck = ORCH.compute_waves(reg["tasks"])
        self.assertEqual([], stuck)
        self.assertIn("T-103", [t for w in waves for t in w])


if __name__ == "__main__":
    unittest.main()
