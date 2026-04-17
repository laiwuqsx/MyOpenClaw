import os
import tempfile
import unittest
from unittest.mock import patch

from myopenclaw.core.memory.injection import (
    build_memory_specs,
    format_memory_blocks_for_prompt,
    load_injected_memory_blocks,
)


class TestMemoryInjection(unittest.TestCase):
    def test_build_memory_specs_by_mode(self):
        main_specs = build_memory_specs("main")
        heartbeat_specs = build_memory_specs("heartbeat")

        self.assertTrue(any(spec.name == "AGENTS.md" for spec in main_specs))
        self.assertTrue(any(spec.name == "HEARTBEAT.md" for spec in heartbeat_specs))
        self.assertFalse(any(spec.name == "HEARTBEAT.md" for spec in main_specs))

    def test_load_injected_memory_blocks_and_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_path = os.path.join(tmpdir, "AGENTS.md")
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


if __name__ == "__main__":
    unittest.main()
