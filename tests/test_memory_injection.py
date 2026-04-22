import os
import tempfile
import unittest
from unittest.mock import patch

from myopenclaw.core.memory.injection import (
    build_memory_specs,
    format_memory_blocks_for_prompt,
    load_injected_memory_blocks,
)
from myopenclaw.core.memory.files import list_recent_daily_memory_files


class TestMemoryInjection(unittest.TestCase):
    def test_build_memory_specs_by_mode(self):
        main_specs = build_memory_specs("main")
        heartbeat_specs = build_memory_specs("heartbeat")

        self.assertTrue(any(spec.name == "AGENTS.md" for spec in main_specs))
        self.assertTrue(any(spec.name == "PROJECT.md" for spec in main_specs))
        self.assertTrue(any(spec.name == "HEARTBEAT.md" for spec in heartbeat_specs))
        self.assertFalse(any(spec.name == "HEARTBEAT.md" for spec in main_specs))
        self.assertFalse(any(spec.name == "legacy_user_profile.md" for spec in main_specs))

    def test_legacy_profile_is_explicit(self):
        specs = build_memory_specs("main", include_legacy_profile=True)
        self.assertTrue(any(spec.name == "legacy_user_profile.md" for spec in specs))

    def test_load_injected_memory_blocks_and_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_path = os.path.join(tmpdir, "AGENTS.md")
            project_path = os.path.join(tmpdir, "PROJECT.md")
            soul_path = os.path.join(tmpdir, "SOUL.md")
            user_path = os.path.join(tmpdir, "USER.md")
            memory_path = os.path.join(tmpdir, "MEMORY.md")
            legacy_path = os.path.join(tmpdir, "user_profile.md")
            daily_dir = os.path.join(tmpdir, "memory")
            os.makedirs(daily_dir, exist_ok=True)

            with open(agents_path, "w", encoding="utf-8") as fh:
                fh.write("agents memory")
            with open(user_path, "w", encoding="utf-8") as fh:
                fh.write("user memory")
            with open(os.path.join(daily_dir, "2026-04-17.md"), "w", encoding="utf-8") as fh:
                fh.write("daily memory")

            with patch("myopenclaw.core.memory.injection.AGENTS_MD_PATH", agents_path), \
                patch("myopenclaw.core.memory.injection.PROJECT_MD_PATH", project_path), \
                patch("myopenclaw.core.memory.injection.SOUL_MD_PATH", soul_path), \
                patch("myopenclaw.core.memory.injection.USER_MD_PATH", user_path), \
                patch("myopenclaw.core.memory.injection.MEMORY_MD_PATH", memory_path), \
                patch("myopenclaw.core.memory.injection.LEGACY_USER_PROFILE_PATH", legacy_path), \
                patch("myopenclaw.core.memory.injection.DAILY_MEMORY_DIR", daily_dir):
                blocks = load_injected_memory_blocks("main", daily_memory_days=2)

            self.assertTrue(any(block.name == "AGENTS.md" for block in blocks))
            self.assertTrue(any(block.name == "USER.md" for block in blocks))
            self.assertTrue(any(block.source_type == "daily_memory" for block in blocks))

            rendered = format_memory_blocks_for_prompt(blocks)
            self.assertIn("[Memory: AGENTS.md]", rendered)
            self.assertIn("daily memory", rendered)

    def test_daily_memory_is_not_loaded_by_default(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_path = os.path.join(tmpdir, "AGENTS.md")
            project_path = os.path.join(tmpdir, "PROJECT.md")
            daily_dir = os.path.join(tmpdir, "memory")
            os.makedirs(daily_dir, exist_ok=True)

            with open(agents_path, "w", encoding="utf-8") as fh:
                fh.write("agents memory")
            with open(os.path.join(daily_dir, "2026-04-17.md"), "w", encoding="utf-8") as fh:
                fh.write("daily memory")

            with patch("myopenclaw.core.memory.injection.AGENTS_MD_PATH", agents_path), \
                patch("myopenclaw.core.memory.injection.PROJECT_MD_PATH", project_path), \
                patch("myopenclaw.core.memory.injection.SOUL_MD_PATH", os.path.join(tmpdir, "SOUL.md")), \
                patch("myopenclaw.core.memory.injection.USER_MD_PATH", os.path.join(tmpdir, "USER.md")), \
                patch("myopenclaw.core.memory.injection.MEMORY_MD_PATH", os.path.join(tmpdir, "MEMORY.md")), \
                patch("myopenclaw.core.memory.injection.LEGACY_USER_PROFILE_PATH", os.path.join(tmpdir, "user_profile.md")), \
                patch("myopenclaw.core.memory.injection.DAILY_MEMORY_DIR", daily_dir):
                blocks = load_injected_memory_blocks("main")

            self.assertFalse(any(block.source_type == "daily_memory" for block in blocks))

    def test_daily_memory_discovery_uses_recent_dated_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in [
                "2026-04-15.md",
                "2026-04-17.md",
                "notes.md",
                "invalid-date.md",
            ]:
                with open(os.path.join(tmpdir, name), "w", encoding="utf-8") as fh:
                    fh.write(name)

            files = list_recent_daily_memory_files(tmpdir, days=1)

            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith("2026-04-17.md"))


if __name__ == "__main__":
    unittest.main()
