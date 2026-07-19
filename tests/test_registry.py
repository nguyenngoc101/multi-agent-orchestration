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
        self.assertIn("KẾT QUẢ: OK", result.stdout)

    def test_missing_task_id_is_clean_validation_error(self):
        result = self.run_checker({
            "agents": [],
            "tasks": [{"title": "broken", "scope": {"allow": ["src/**"]}, "state": "backlog"}],
        })
        self.assertEqual(1, result.returncode)
        self.assertIn("thiếu field 'id'", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_wrong_scope_type_is_clean_validation_error(self):
        result = self.run_checker({
            "agents": [],
            "tasks": [{"id": "T-1", "title": "broken", "scope": [], "state": "backlog"}],
        })
        self.assertEqual(1, result.returncode)
        self.assertIn("scope phải là object", result.stdout)
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
        self.assertIn("Dependency VÒNG", result.stdout)


if __name__ == "__main__":
    unittest.main()
