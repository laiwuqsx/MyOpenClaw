import unittest
from types import SimpleNamespace

from langchain_core.messages import AIMessage, ToolMessage

from myopenclaw.core.session_state import SessionContext
from myopenclaw.core.turn_manager import run_agent_turn


class FakeLogger:
    def __init__(self):
        self.events = []

    def log_event(self, **kwargs):
        self.events.append(kwargs)


class FakeLLM:
    def invoke(self, *_args, **_kwargs):
        return SimpleNamespace(content="summary")


class FakeLLMWithAIMessage:
    def invoke(self, *_args, **_kwargs):
        return AIMessage(content="hello world")


class FakeLLMWithToolCall:
    def invoke(self, *_args, **_kwargs):
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "calculator",
                    "args": {"expression": "1+1"},
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        )


class TestTurnManager(unittest.TestCase):
    def test_run_agent_turn_logs_ai_message(self):
        logger = FakeLogger()
        session_context = SessionContext(
            session_id="s1",
            session_mode="main",
            thread_id="thread-1",
            workspace_dir="/tmp/workspace",
            provider_name="openai",
            model_name="gpt-4o-mini",
        )
        result = run_agent_turn(
            state={"messages": [], "summary": ""},
            llm=FakeLLM(),
            llm_with_tools=FakeLLMWithAIMessage(),
            session_context=session_context,
            audit_logger=logger,
        )

        self.assertEqual(result.response.content, "hello world")
        self.assertTrue(any(event["event"] == "ai_message" for event in logger.events))
        self.assertIn("messages", result.state_updates)

    def test_run_agent_turn_logs_tool_result_and_tool_call(self):
        logger = FakeLogger()
        session_context = SessionContext(
            session_id="s1",
            session_mode="main",
            thread_id="thread-1",
            workspace_dir="/tmp/workspace",
            provider_name="openai",
            model_name="gpt-4o-mini",
        )
        tool_message = ToolMessage(content="42", tool_call_id="call-1", name="calculator")
        result = run_agent_turn(
            state={"messages": [tool_message], "summary": ""},
            llm=FakeLLM(),
            llm_with_tools=FakeLLMWithToolCall(),
            session_context=session_context,
            audit_logger=logger,
        )

        self.assertEqual(len(result.tool_calls), 1)
        self.assertTrue(any(event["event"] == "tool_result" for event in logger.events))
        self.assertTrue(any(event["event"] == "tool_call" for event in logger.events))


if __name__ == "__main__":
    unittest.main()
