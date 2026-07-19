import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check-registry.py"


class RegistryCheckerTests(unittest.TestCase):
    def run_checker(self, registry):
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
            json.dump(registry, handle)
            handle.flush()
            return subprocess.run(
                [sys.executable, str(CHECKER), handle.name],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_valid_registry_passes(self):
        result = self.run_checker({"agents": [], "tasks": []})
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("RESULT: OK", result.stdout)

    def test_missing_task_id_is_clean_validation_error(self):
        result = self.run_checker({
            "agents": [],
            "tasks": [{"title": "broken", "scope": {"allow": ["src/**"]}, "state": "backlog"}],
        })
        self.assertEqual(1, result.returncode)
        self.assertIn("missing field 'id'", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_wrong_scope_type_is_clean_validation_error(self):
        result = self.run_checker({
            "agents": [],
            "tasks": [{"id": "T-1", "title": "broken", "scope": [], "state": "backlog"}],
        })
        self.assertEqual(1, result.returncode)
        self.assertIn("scope must be an object", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_cycle_fails(self):
        result = self.run_checker({
            "agents": [],
            "tasks": [
                {"id": "T-1", "title": "one", "scope": {"allow": ["one/**"]},
                 "state": "backlog", "depends_on": ["T-2"]},
                {"id": "T-2", "title": "two", "scope": {"allow": ["two/**"]},
                 "state": "backlog", "depends_on": ["T-1"]},
            ],
        })
        self.assertEqual(1, result.returncode)
        self.assertIn("Dependency CYCLE", result.stdout)

    def test_valid_log_passes(self):
        result = self.run_checker({
            "agents": [],
            "tasks": [{
                "id": "T-1", "title": "logged", "scope": {"allow": ["src/**"]},
                "state": "backlog",
                "log": [{"ts": "2026-07-19T00:00:00Z", "by": "orchestrator", "note": "created"}],
            }],
        })
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("RESULT: OK", result.stdout)

    def test_log_entry_missing_note_is_error(self):
        result = self.run_checker({
            "agents": [],
            "tasks": [{
                "id": "T-1", "title": "bad-log", "scope": {"allow": ["src/**"]},
                "state": "backlog",
                "log": [{"by": "orchestrator"}],
            }],
        })
        self.assertEqual(1, result.returncode)
        self.assertIn("log entry missing 'note'", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_log_not_a_list_is_error(self):
        result = self.run_checker({
            "agents": [],
            "tasks": [{
                "id": "T-1", "title": "bad-log", "scope": {"allow": ["src/**"]},
                "state": "backlog", "log": "nope",
            }],
        })
        self.assertEqual(1, result.returncode)
        self.assertIn("log must be an array", result.stdout)


if __name__ == "__main__":
    unittest.main()
