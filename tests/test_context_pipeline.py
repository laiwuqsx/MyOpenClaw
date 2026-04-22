import unittest
from types import SimpleNamespace
from unittest.mock import patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from myopenclaw.core.context_pipeline import prepare_context
from myopenclaw.core.session_state import SessionContext


class FakeLLM:
    def invoke(self, *_args, **_kwargs):
        return SimpleNamespace(content="updated summary")


class TestContextPipeline(unittest.TestCase):
    def test_prepare_context_injects_memory_and_summary(self):
        state = {
            "messages": [
                HumanMessage(content="hello"),
                AIMessage(content="hi"),
            ],
            "summary": "working summary",
        }
        session_context = SessionContext(
            session_id="s1",
            session_mode="main",
            thread_id="t1",
            workspace_dir="/tmp/workspace",
            provider_name="openai",
            model_name="gpt-4o-mini",
        )

        with patch("myopenclaw.core.context_pipeline.load_injected_memory_blocks", return_value=[]), patch(
            "myopenclaw.core.context_pipeline.load_project_summary",
            return_value="",
        ):
            prepared = prepare_context(state=state, llm=FakeLLM(), session_context=session_context)

        self.assertEqual(len([m for m in prepared.messages_for_llm if isinstance(m, SystemMessage)]), 1)
        self.assertEqual(prepared.updated_summary, "working summary")
        self.assertIn("Working Summary", prepared.messages_for_llm[0].content)

    def test_prepare_context_compacts_and_updates_summary(self):
        messages = []
        for idx in range(41):
            messages.append(HumanMessage(content=f"user {idx}"))
            messages.append(AIMessage(content=f"ai {idx}"))

        state = {"messages": messages, "summary": ""}
        session_context = SessionContext(
            session_id="s1",
            session_mode="main",
            thread_id="t1",
            workspace_dir="/tmp/workspace",
            provider_name="openai",
            model_name="gpt-4o-mini",
        )

        with patch("myopenclaw.core.context_pipeline.load_injected_memory_blocks", return_value=[]), patch(
            "myopenclaw.core.context_pipeline.load_project_summary",
            return_value="",
        ), patch("myopenclaw.core.context_pipeline.save_project_summary") as mock_save:
            prepared = prepare_context(state=state, llm=FakeLLM(), session_context=session_context)

        self.assertEqual(prepared.updated_summary, "updated summary")
        mock_save.assert_called_once_with("updated summary")
        self.assertEqual(len([m for m in prepared.messages_for_llm if isinstance(m, SystemMessage)]), 1)
        self.assertLess(len(prepared.messages_for_llm), len(messages))

    def test_prepare_context_does_not_load_summary_when_state_is_empty(self):
        state = {
            "messages": [
                HumanMessage(content="continue"),
            ],
            "summary": "",
        }
        session_context = SessionContext(
            session_id="s1",
            session_mode="main",
            thread_id="t1",
            workspace_dir="/tmp/workspace",
            provider_name="openai",
            model_name="gpt-4o-mini",
        )

        with patch("myopenclaw.core.context_pipeline.load_injected_memory_blocks", return_value=[]), patch(
            "myopenclaw.core.context_pipeline.load_project_summary",
            return_value="",
        ):
            prepared = prepare_context(state=state, llm=FakeLLM(), session_context=session_context)

        self.assertEqual(prepared.updated_summary, "")
        self.assertNotIn("Working Summary", prepared.messages_for_llm[0].content)

    def test_prepare_context_loads_project_summary_when_state_is_empty(self):
        state = {
            "messages": [
                HumanMessage(content="continue"),
            ],
            "summary": "",
        }
        session_context = SessionContext(
            session_id="s1",
            session_mode="main",
            thread_id="t1",
            workspace_dir="/tmp/workspace",
            provider_name="openai",
            model_name="gpt-4o-mini",
        )

        with patch("myopenclaw.core.context_pipeline.load_injected_memory_blocks", return_value=[]), patch(
            "myopenclaw.core.context_pipeline.load_project_summary",
            return_value="loaded summary",
        ):
            prepared = prepare_context(state=state, llm=FakeLLM(), session_context=session_context)

        self.assertEqual(prepared.updated_summary, "loaded summary")
        self.assertIn("loaded summary", prepared.messages_for_llm[0].content)


if __name__ == "__main__":
    unittest.main()
