import unittest
import tempfile
import os
from unittest.mock import patch

from myopenclaw.core.memory.summary import (
    get_project_summary_path,
    load_project_summary,
    normalize_summary_text,
    save_project_summary,
)


class TestMemorySummary(unittest.TestCase):
    def test_normalize_summary_removes_empty_markers(self):
        self.assertEqual(normalize_summary_text(" No existing working summary. "), "")
        self.assertEqual(normalize_summary_text(" active task "), "active task")

    def test_project_summary_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = f"{tmpdir}/SUMMARY.md"
            with patch("myopenclaw.core.memory.summary.SUMMARY_MD_PATH", summary_path):
                path = save_project_summary(" active task ")
                self.assertEqual(path, get_project_summary_path())
                self.assertTrue(path.endswith("SUMMARY.md"))
                self.assertEqual(load_project_summary(), "active task")

    def test_project_summary_loads_legacy_local_main_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_dir = f"{tmpdir}/summaries"
            legacy_path = f"{legacy_dir}/local_main.md"
            with patch("myopenclaw.core.memory.summary.SUMMARY_MD_PATH", f"{tmpdir}/SUMMARY.md"), patch(
                "myopenclaw.core.memory.summary.SUMMARY_DIR",
                legacy_dir,
            ):
                save_project_summary("")
                # Remove the empty new file so fallback path is exercised.
                os.remove(f"{tmpdir}/SUMMARY.md")
                os.makedirs(legacy_dir, exist_ok=True)
                with open(legacy_path, "w", encoding="utf-8") as fh:
                    fh.write("legacy summary")

                self.assertEqual(load_project_summary(), "legacy summary")


if __name__ == "__main__":
    unittest.main()
