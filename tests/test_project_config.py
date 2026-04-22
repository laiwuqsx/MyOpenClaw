import os
import tempfile
import unittest

from myopenclaw.core.config import _discover_project_root, _safe_project_id


class TestProjectConfig(unittest.TestCase):
    def test_discover_project_root_uses_git_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = os.path.join(tmpdir, "repo")
            nested = os.path.join(project_root, "src", "pkg")
            os.makedirs(os.path.join(project_root, ".git"), exist_ok=True)
            os.makedirs(nested, exist_ok=True)

            self.assertEqual(_discover_project_root(nested), project_root)

    def test_safe_project_id_includes_stable_hash(self):
        project_id = _safe_project_id("/tmp/My Project")

        self.assertTrue(project_id.startswith("My-Project-"))
        self.assertGreater(len(project_id), len("My-Project-"))


if __name__ == "__main__":
    unittest.main()
