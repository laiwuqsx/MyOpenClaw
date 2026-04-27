import os
import tempfile
import unittest
from unittest.mock import patch

from myopenclaw.core.config import OFFICE_DIR
from myopenclaw.core.tools.sandbox_tools import (
    _get_safe_path,
    execute_office_shell,
    evaluate_shell_policy,
    list_office_files,
    patch_office_file,
    read_office_file,
    write_office_file,
)


class TestSandboxTools(unittest.TestCase):
    def test_get_safe_path_blocks_traversal(self):
        with self.assertRaises(PermissionError):
            _get_safe_path("../../etc/passwd")

    @patch("myopenclaw.core.tools.sandbox_tools.os.path.exists", return_value=True)
    @patch(
        "myopenclaw.core.tools.sandbox_tools.os.path.isdir",
        side_effect=lambda p: p == os.path.abspath(OFFICE_DIR) or p.endswith("subdir"),
    )
    @patch("myopenclaw.core.tools.sandbox_tools.os.listdir", return_value=["file.txt", "subdir"])
    def test_list_office_files(self, _mock_listdir, _mock_isdir, _mock_exists):
        result = list_office_files.invoke({"sub_dir": ""})
        self.assertIn("FILE file.txt", result)
        self.assertIn("DIR subdir", result)

    @patch("myopenclaw.core.tools.sandbox_tools.os.path.exists", return_value=False)
    def test_read_office_file_missing(self, _mock_exists):
        result = read_office_file.invoke({"filepath": "missing.txt"})
        self.assertIn("File does not exist", result)

    def test_write_office_file_invalid_mode(self):
        result = write_office_file.invoke({"filepath": "test.txt", "content": "hello", "mode": "x"})
        self.assertIn("Invalid mode", result)

    def test_execute_office_shell_blocks_dangerous_commands(self):
        dangerous_commands = [
            "cd ../",
            "cat /etc/passwd",
            "ls ~",
            "python -c 'print(1)'",
            "node -e 'console.log(1)'",
            "rm file.txt",
            "ls . && pwd",
        ]
        for command in dangerous_commands:
            with self.subTest(command=command):
                result = execute_office_shell.invoke({"command": command})
                self.assertIn("Permission denied", result)

    def test_shell_policy_allows_safe_read_commands(self):
        decision = evaluate_shell_policy("ls notes")

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.risk, "low")
        self.assertEqual(decision.argv, ["ls", "notes"])

    def test_shell_policy_blocks_control_operators(self):
        decision = evaluate_shell_policy("ls notes && pwd")

        self.assertFalse(decision.allowed)
        self.assertIn("control operators", decision.reason)

    def test_execute_office_shell_runs_without_shell_interpolation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("myopenclaw.core.tools.sandbox_tools.OFFICE_DIR", tmpdir):
                with open(os.path.join(tmpdir, "a.txt"), "w", encoding="utf-8") as fh:
                    fh.write("hello")

                result = execute_office_shell.invoke({"command": "ls"})

        self.assertIn("Exit Code: 0", result)
        self.assertIn("a.txt", result)

    def test_write_and_read_inside_temp_office(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("myopenclaw.core.tools.sandbox_tools.OFFICE_DIR", tmpdir):
                write_result = write_office_file.invoke(
                    {"filepath": "notes/test.txt", "content": "hello office", "mode": "w"}
                )
                self.assertIn("Successfully overwrote", write_result)

                read_result = read_office_file.invoke({"filepath": "notes/test.txt"})
                self.assertEqual(read_result, "hello office")

                self.assertTrue(os.path.exists(os.path.join(tmpdir, "notes", "test.txt")))

    def test_patch_office_file_replaces_exact_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("myopenclaw.core.tools.sandbox_tools.OFFICE_DIR", tmpdir):
                path = os.path.join(tmpdir, "notes.txt")
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("hello office")

                result = patch_office_file.invoke(
                    {
                        "filepath": "notes.txt",
                        "old_text": "office",
                        "new_text": "workspace",
                        "expected_replacements": 1,
                    }
                )
                with open(path, "r", encoding="utf-8") as fh:
                    content = fh.read()

        self.assertIn("Patched office file", result)
        self.assertEqual(content, "hello workspace")

    def test_patch_office_file_requires_expected_match_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("myopenclaw.core.tools.sandbox_tools.OFFICE_DIR", tmpdir):
                path = os.path.join(tmpdir, "notes.txt")
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write("same same")

                result = patch_office_file.invoke(
                    {
                        "filepath": "notes.txt",
                        "old_text": "same",
                        "new_text": "changed",
                        "expected_replacements": 1,
                    }
                )

        self.assertIn("Patch not applied", result)
        self.assertIn("found 2", result)


if __name__ == "__main__":
    unittest.main()
