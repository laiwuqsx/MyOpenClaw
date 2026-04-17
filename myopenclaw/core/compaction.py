from langchain_core.messages import HumanMessage, RemoveMessage

from .context import trim_context_messages
from .memory.summary import build_summary_prompt, merge_summary_response


def should_compact_messages(messages: list, trigger_turns: int) -> bool:
    human_turns = sum(1 for msg in messages if isinstance(msg, HumanMessage))
    return human_turns >= trigger_turns


def compact_context_messages(messages: list, trigger_turns: int, keep_turns: int) -> tuple[list, list]:
    return trim_context_messages(messages, trigger_turns=trigger_turns, keep_turns=keep_turns)


def summarize_discarded_messages(llm, current_summary: str, discarded_messages: list) -> str:
    discarded_text = "\n".join(
        f"{getattr(message, 'type', 'unknown')}: {getattr(message, 'content', '')}"
        for message in discarded_messages
        if getattr(message, "content", "")
    ).strip()
    if not discarded_text:
        return current_summary

    summary_prompt = build_summary_prompt(current_summary=current_summary, discarded_text=discarded_text)
    response = llm.invoke(summary_prompt)
    raw_content = getattr(response, "content", response)
    return merge_summary_response(raw_content)


def build_remove_commands(discarded_messages: list) -> list[RemoveMessage]:
    return [RemoveMessage(id=message.id) for message in discarded_messages if getattr(message, "id", None)]
