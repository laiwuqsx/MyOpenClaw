import unittest

from myopenclaw.core.control import (
    build_approval_state,
    build_plan_state,
    format_approval_state_for_prompt,
    format_plan_state_for_prompt,
)


class TestControlState(unittest.TestCase):
    def test_build_plan_state_normalizes_items(self):
        plan_state = build_plan_state(
            [
                {"step": "Inspect runtime", "status": "completed"},
                {"step": "Add approval state", "status": "in_progress"},
            ],
            explanation="Control-plane rollout",
        )

        self.assertEqual(len(plan_state["items"]), 2)
        self.assertEqual(plan_state["items"][1]["status"], "in_progress")
        self.assertIn("updated_at", plan_state)

    def test_build_plan_state_rejects_multiple_in_progress_steps(self):
        with self.assertRaises(ValueError):
            build_plan_state(
                [
                    {"step": "One", "status": "in_progress"},
                    {"step": "Two", "status": "in_progress"},
                ]
            )

    def test_prompt_formatters_render_control_sections(self):
        plan_text = format_plan_state_for_prompt(
            build_plan_state(
                [{"step": "Add CLI commands", "status": "pending"}],
                explanation="Next step",
            )
        )
        approval_text = format_approval_state_for_prompt(
            build_approval_state(
                tool_name="write_office_file",
                permission_mode="workspace_write",
                risk="medium",
                write_scope="office",
                reason="Write-capable tools require approval.",
                tool_args={"filepath": "notes.txt"},
            )
        )

        self.assertIn("Add CLI commands", plan_text)
        self.assertIn("Tool: write_office_file", approval_text)


if __name__ == "__main__":
    unittest.main()
