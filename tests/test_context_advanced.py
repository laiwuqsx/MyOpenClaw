import unittest

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from myopenclaw.core.context import trim_context_messages


class TestContextTrimming(unittest.TestCase):
    def test_trim_keep_all_below_threshold(self):
        messages = [
            SystemMessage(content="system"),
            HumanMessage(content="u1"),
            AIMessage(content="a1"),
            HumanMessage(content="u2"),
            AIMessage(content="a2"),
        ]

        kept, discarded = trim_context_messages(messages, trigger_turns=10, keep_turns=10)
        self.assertEqual(len(kept), 5)
        self.assertEqual(len(discarded), 0)

    def test_trim_discards_old_turns(self):
        messages = [
            SystemMessage(content="system"),
            HumanMessage(content="u1"),
            AIMessage(content="a1"),
            HumanMessage(content="u2"),
            AIMessage(content="a2"),
            HumanMessage(content="u3"),
            AIMessage(content="a3"),
        ]

        kept, discarded = trim_context_messages(messages, trigger_turns=2, keep_turns=1)
        self.assertEqual(len(kept), 3)
        self.assertEqual(len(discarded), 4)

    def test_trim_turns_include_tool_messages(self):
        messages = [
            HumanMessage(content="u1"),
            AIMessage(content="a1"),
            ToolMessage(content="t1", tool_call_id="1"),
            HumanMessage(content="u2"),
            AIMessage(content="a2"),
        ]

        kept, discarded = trim_context_messages(messages, trigger_turns=2, keep_turns=1)
        self.assertEqual(len(kept), 2)
        self.assertEqual(len(discarded), 3)


if __name__ == "__main__":
    unittest.main()
