from dataclasses import dataclass, field

from .context_pipeline import prepare_context


@dataclass
class TurnResult:
    response: object
    state_updates: dict
    tool_calls: list = field(default_factory=list)


def run_agent_turn(
    state: dict,
    llm,
    llm_with_tools,
    session_context,
    audit_logger,
    tool_contracts: dict | None = None,
) -> TurnResult:
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
                event_family="tool",
                status="ok",
                tool=getattr(message, "name", "unknown"),
                contract=(tool_contracts or {}).get(getattr(message, "name", "unknown"), {}),
                payload={
                    "result_summary": str(getattr(message, "content", ""))[:200],
                    "tool_call_id": getattr(message, "tool_call_id", ""),
                },
            )

    prepared = prepare_context(state=state, llm=llm, session_context=session_context)
    audit_logger.log_event(
        thread_id=session_context.thread_id,
        event="llm_input",
        event_family="llm",
        payload={"message_count": len(prepared.messages_for_llm)},
    )

    response = llm_with_tools.invoke(prepared.messages_for_llm)
    tool_calls = list(getattr(response, "tool_calls", []) or [])

    if tool_calls:
        for tool_call in tool_calls:
            audit_logger.log_event(
                thread_id=session_context.thread_id,
                event="tool_call",
                event_family="tool",
                status="requested",
                tool=tool_call.get("name", "unknown"),
                contract=(tool_contracts or {}).get(tool_call.get("name", "unknown"), {}),
                payload={
                    "args": tool_call.get("args", {}),
                    "tool_call_id": tool_call.get("id", ""),
                    "tool_call_type": tool_call.get("type", ""),
                },
            )
    elif getattr(response, "content", None):
        audit_logger.log_event(
            thread_id=session_context.thread_id,
            event="ai_message",
            event_family="assistant",
            payload={"content": response.content},
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
