import importlib.util
from pathlib import Path
from unittest import mock
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("enforce_scope", ROOT / "scripts" / "enforce-scope.py")
ENFORCE_SCOPE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENFORCE_SCOPE)


class EnforceScopeTests(unittest.TestCase):
    def test_changed_files_disables_rename_collapsing(self):
        completed = mock.Mock(stdout="outside/source.py\nallowed/source.py\n")
        with mock.patch.object(ENFORCE_SCOPE.subprocess, "run", return_value=completed) as run:
            files = ENFORCE_SCOPE.changed_files("base", "head")
        self.assertEqual(["outside/source.py", "allowed/source.py"], files)
        self.assertIn("--no-renames", run.call_args.args[0])

    def test_deny_takes_precedence_over_allow(self):
        path = "src/shared/secret.py"
        self.assertTrue(ENFORCE_SCOPE.match_any(path, ["src/**"]))
        self.assertTrue(ENFORCE_SCOPE.match_any(path, ["src/shared/**"]))


if __name__ == "__main__":
    unittest.main()
