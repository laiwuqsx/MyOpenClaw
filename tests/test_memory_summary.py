import unittest
import tempfile
from unittest.mock import patch

from myopenclaw.core.memory.summary import (
    get_thread_summary_path,
    load_thread_summary,
    normalize_summary_text,
    save_thread_summary,
)


class TestMemorySummary(unittest.TestCase):
    def test_normalize_summary_removes_empty_markers(self):
        self.assertEqual(normalize_summary_text(" No existing working summary. "), "")
        self.assertEqual(normalize_summary_text(" active task "), "active task")

    def test_thread_summary_round_trip_uses_safe_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("myopenclaw.core.memory.summary.SUMMARY_DIR", tmpdir):
                path = save_thread_summary("../local main", " active task ")
                self.assertEqual(path, get_thread_summary_path("../local main"))
                self.assertTrue(path.endswith("local_main.md"))
                self.assertEqual(load_thread_summary("../local main"), "active task")


if __name__ == "__main__":
    unittest.main()
