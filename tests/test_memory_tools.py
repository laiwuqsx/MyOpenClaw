import os
import tempfile
import unittest
from unittest.mock import patch

from myopenclaw.core.tools.builtins import (
    append_daily_memory,
    read_daily_memory,
    read_user_profile,
    save_user_profile,
)


class TestMemoryTools(unittest.TestCase):
    def test_user_profile_reads_current_and_legacy_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            user_path = os.path.join(tmpdir, "USER.md")
            legacy_path = os.path.join(tmpdir, "memory", "user_profile.md")
            os.makedirs(os.path.dirname(legacy_path), exist_ok=True)

            with open(user_path, "w", encoding="utf-8") as fh:
                fh.write("current profile")
            with open(legacy_path, "w", encoding="utf-8") as fh:
                fh.write("legacy profile")

            with patch("myopenclaw.core.tools.builtins.USER_MD_PATH", user_path), patch(
                "myopenclaw.core.tools.builtins.LEGACY_USER_PROFILE_PATH",
                legacy_path,
            ):
                result = read_user_profile.invoke({})

            self.assertIn("current profile", result)
            self.assertIn("legacy profile", result)

    def test_save_user_profile_writes_current_and_legacy_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            user_path = os.path.join(tmpdir, "USER.md")
            legacy_path = os.path.join(tmpdir, "memory", "user_profile.md")

            with patch("myopenclaw.core.tools.builtins.USER_MD_PATH", user_path), patch(
                "myopenclaw.core.tools.builtins.LEGACY_USER_PROFILE_PATH",
                legacy_path,
            ):
                result = save_user_profile.invoke({"new_content": "remember this"})

            self.assertIn("User profile saved", result)
            with open(user_path, "r", encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "remember this")
            with open(legacy_path, "r", encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "remember this")

    def test_append_daily_memory_validates_date(self):
        result = append_daily_memory.invoke({"note": "note", "date": "04-21-2026"})
        self.assertIn("Invalid date", result)

    def test_read_daily_memory_requires_explicit_date(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = os.path.join(tmpdir, "2026-04-21.md")
            with open(memory_path, "w", encoding="utf-8") as fh:
                fh.write("- continue phase4")

            with patch("myopenclaw.core.tools.builtins.DAILY_MEMORY_DIR", tmpdir):
                result = read_daily_memory.invoke({"date": "2026-04-21"})

            self.assertIn("continue phase4", result)

    def test_read_daily_memory_validates_date(self):
        result = read_daily_memory.invoke({"date": "04-21-2026"})
        self.assertIn("Invalid date", result)


if __name__ == "__main__":
    unittest.main()
