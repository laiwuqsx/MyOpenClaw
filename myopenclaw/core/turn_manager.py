from dataclasses import dataclass, field

from .context_pipeline import prepare_context


@dataclass
class TurnResult:
    response: object
    state_updates: dict
    tool_calls: list = field(default_factory=list)


def run_agent_turn(state: dict, llm, llm_with_tools, session_context, audit_logger) -> TurnResult:
    raw_messages = state.get("messages", [])
    if raw_messages:
        trailing_tool_messages = []
        for message in reversed(raw_messages):
            if getattr(message, "type", None) == "tool":
                trailing_tool_messages.append(message)
            else:
                break
        for message in reversed(trailing_tool_messages):
            audit_logger.log_event(
                thread_id=session_context.thread_id,
                event="tool_result",
                tool=getattr(message, "name", "unknown"),
                result_summary=str(getattr(message, "content", ""))[:200],
            )

    prepared = prepare_context(state=state, llm=llm, session_context=session_context)
    audit_logger.log_event(
        thread_id=session_context.thread_id,
        event="llm_input",
        message_count=len(prepared.messages_for_llm),
    )

    response = llm_with_tools.invoke(prepared.messages_for_llm)
    tool_calls = list(getattr(response, "tool_calls", []) or [])

    if tool_calls:
        for tool_call in tool_calls:
            audit_logger.log_event(
                thread_id=session_context.thread_id,
                event="tool_call",
                tool=tool_call.get("name", "unknown"),
                args=tool_call.get("args", {}),
            )
    elif getattr(response, "content", None):
        audit_logger.log_event(
            thread_id=session_context.thread_id,
            event="ai_message",
            content=response.content,
        )

    state_updates: dict = {
        "summary": prepared.updated_summary,
        "messages": [],
    }
    if prepared.remove_commands:
        state_updates["messages"].extend(prepared.remove_commands)
    state_updates["messages"].append(response)

    return TurnResult(
        response=response,
        state_updates=state_updates,
        tool_calls=tool_calls,
    )
