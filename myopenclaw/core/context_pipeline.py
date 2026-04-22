from dataclasses import dataclass, field

from langchain_core.messages import SystemMessage

from .compaction import build_remove_commands, compact_context_messages, summarize_discarded_messages
from .memory.injection import format_memory_blocks_for_prompt, load_injected_memory_blocks
from .memory.summary import load_project_summary, normalize_summary_text, save_project_summary
from .prompt_builder import build_system_prompt
from .session_state import SessionContext


@dataclass
class PreparedContext:
    messages_for_llm: list
    updated_summary: str
    remove_commands: list = field(default_factory=list)
    memory_blocks_text: str = ""
    active_summary: str = ""


def prepare_context(state: dict, llm, session_context: SessionContext) -> PreparedContext:
    raw_messages = state.get("messages", [])
    current_summary = normalize_summary_text(state.get("summary", ""))
    if not current_summary:
        current_summary = load_project_summary()

    final_messages, discarded_messages = compact_context_messages(
        raw_messages,
        trigger_turns=40,
        keep_turns=10,
    )

    updated_summary = current_summary
    remove_commands = []
    if discarded_messages:
        updated_summary = summarize_discarded_messages(
            llm=llm,
            current_summary=current_summary,
            discarded_messages=discarded_messages,
        )
        save_project_summary(updated_summary)
        remove_commands = build_remove_commands(discarded_messages)

    memory_blocks = load_injected_memory_blocks(session_mode=session_context.session_mode)
    memory_blocks_text = format_memory_blocks_for_prompt(memory_blocks)
    system_prompt = build_system_prompt(
        memory_text=memory_blocks_text,
        summary_text=updated_summary,
    )

    non_system_messages = [message for message in final_messages if not isinstance(message, SystemMessage)]
    messages_for_llm = [SystemMessage(content=system_prompt)] + non_system_messages

    return PreparedContext(
        messages_for_llm=messages_for_llm,
        updated_summary=updated_summary,
        remove_commands=remove_commands,
        memory_blocks_text=memory_blocks_text,
        active_summary=updated_summary,
    )
