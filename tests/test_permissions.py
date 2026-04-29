import unittest

from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from types import SimpleNamespace

from myopenclaw.core.permissions import (
    build_permission_gated_tools,
    clear_permission_context,
    evaluate_tool_permission,
    permission_context_from_config,
    set_permission_context,
    wrap_tool_call_with_permissions,
)
from myopenclaw.core.tools.base import myopenclaw_tool


@myopenclaw_tool(
    permission_mode="workspace_read",
    tags=("test",),
)
def sample_read_tool(path: str) -> str:
    """Read a fake path for tests."""
    return f"read:{path}"


@myopenclaw_tool(
    permission_mode="workspace_patch",
    risk="medium",
    read_only=False,
    write_scope="office",
    requires_approval=True,
    tags=("test",),
)
def sample_write_tool(content: str) -> str:
    """Write fake content for tests."""
    return f"write:{content}"


class TestPermissions(unittest.TestCase):
    def tearDown(self):
        clear_permission_context()

    def test_read_tool_is_allowed_by_default(self):
        decision = evaluate_tool_permission("sample_read_tool", sample_read_tool.metadata["myopenclaw/contract"])

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.status, "allowed")

    def test_requires_approval_tool_is_blocked_without_approval(self):
        decision = evaluate_tool_permission(
            "sample_write_tool",
            sample_write_tool.metadata["myopenclaw/contract"],
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, "approval_required")

    def test_requires_approval_tool_can_be_preapproved(self):
        set_permission_context(approved_tools=["sample_write_tool"])
        decision = evaluate_tool_permission(
            "sample_write_tool",
            sample_write_tool.metadata["myopenclaw/contract"],
        )

        self.assertTrue(decision.allowed)
        self.assertTrue(decision.approval_required)

    def test_gated_tool_returns_permission_denied_message_when_blocked(self):
        gated_tool = build_permission_gated_tools([sample_write_tool])[0]

        result = gated_tool.invoke({"content": "x"})

        self.assertIn("Permission denied by runtime policy.", result)
        self.assertIn("Approval Required: yes", result)

    def test_gated_tool_blocks_tools_without_contract(self):
        @tool
        def plain_tool(name: str) -> str:
            """Plain tool without myopenclaw contract."""
            return f"hello {name}"

        gated_tool = build_permission_gated_tools([plain_tool])[0]
        result = gated_tool.invoke({"name": "world"})

        self.assertIn("missing an explicit permission contract", result)

    def test_wrap_tool_call_writes_pending_approval_state(self):
        request = SimpleNamespace(
            tool_call={"name": "sample_write_tool", "id": "call-1", "args": {"content": "x"}},
            tool=sample_write_tool,
            state={},
            runtime=SimpleNamespace(config={"configurable": {"approval_policy": "deny_writes"}}),
        )

        result = wrap_tool_call_with_permissions(
            request,
            lambda _request: ToolMessage(content="ok", name="sample_write_tool", tool_call_id="call-1"),
        )

        self.assertEqual(result.update["approval_state"]["status"], "pending")
        self.assertEqual(result.update["approval_state"]["tool_name"], "sample_write_tool")

    def test_permission_context_can_be_built_from_runtime_config(self):
        context = permission_context_from_config(
            {
                "configurable": {
                    "approval_policy": "deny_writes",
                    "approved_tools": ["sample_write_tool"],
                    "approved_permissions": ["workspace_patch"],
                }
            }
        )

        self.assertEqual(context.approval_policy, "deny_writes")
        self.assertIn("sample_write_tool", context.approved_tools)
        self.assertIn("workspace_patch", context.approved_permissions)


if __name__ == "__main__":
    unittest.main()
