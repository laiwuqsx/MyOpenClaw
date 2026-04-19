import os
import tempfile
import unittest
from unittest.mock import patch

from myopenclaw.core.config import OFFICE_DIR
from myopenclaw.core.tools.sandbox_tools import (
    _get_safe_path,
    execute_office_shell,
    list_office_files,
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
        ]
        for command in dangerous_commands:
            with self.subTest(command=command):
                result = execute_office_shell.invoke({"command": command})
                self.assertIn("Permission denied", result)

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


if __name__ == "__main__":
    unittest.main()
