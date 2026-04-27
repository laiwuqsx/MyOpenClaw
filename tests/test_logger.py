import unittest

from myopenclaw.core.logger import (
    AUDIT_SCHEMA_VERSION,
    build_audit_event,
    clear_audit_context,
    infer_event_family,
    infer_event_status,
    set_audit_context,
)


class TestLogger(unittest.TestCase):
    def tearDown(self):
        clear_audit_context()

    def test_build_audit_event_uses_stable_v1_schema(self):
        set_audit_context(
            session_id="session-1",
            session_mode="main",
            thread_id="thread-1",
            provider="openai",
            model="gpt-4o-mini",
        )

        event = build_audit_event(
            thread_id=None,
            event="tool_call",
            tool="calculator",
            status="requested",
            payload={"args": {"expression": "1+1"}},
        )

        self.assertEqual(event["schema_version"], AUDIT_SCHEMA_VERSION)
        self.assertEqual(event["thread_id"], "thread-1")
        self.assertEqual(event["session_id"], "session-1")
        self.assertEqual(event["provider"], "openai")
        self.assertEqual(event["tool"], "calculator")
        self.assertEqual(event["status"], "requested")
        self.assertEqual(event["payload"]["args"]["expression"], "1+1")

    def test_event_family_and_status_inference(self):
        self.assertEqual(infer_event_family("tool_result"), "tool")
        self.assertEqual(infer_event_family("ai_message"), "assistant")
        self.assertEqual(infer_event_status("shell_blocked"), "blocked")
        self.assertEqual(infer_event_status("shell_timeout"), "timeout")


if __name__ == "__main__":
    unittest.main()
