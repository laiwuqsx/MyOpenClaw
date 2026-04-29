def build_base_system_prompt() -> str:
    return (
        "You are MYCLAW, a transparent and controllable local AI assistant.\n\n"
        "[Core Principles]\n"
        "1. Be concise, practical, and natural.\n"
        "2. Use long-term memory and recent context together.\n"
        "3. Stay within the workspace sandbox boundaries.\n"
        "4. Prefer explicit tool use over making up external actions.\n"
        "5. Use tools for time-sensitive or exact operations when an appropriate tool exists.\n"
        "6. For calculations, use the calculator tool instead of doing arithmetic mentally.\n"
    )


def build_memory_prompt_section(memory_text: str) -> str:
    if not memory_text:
        return ""
    return f"[Injected Memory]\n{memory_text}"


def build_summary_prompt_section(summary_text: str) -> str:
    if not summary_text:
        return ""
    return f"[Working Summary]\n{summary_text}"


def build_plan_prompt_section(plan_text: str) -> str:
    if not plan_text:
        return ""
    return (
        "[Plan State]\n"
        f"{plan_text}\n\n"
        "Treat this as runtime state. Keep it updated with the `update_plan` tool when the task changes."
    )


def build_approval_prompt_section(approval_text: str) -> str:
    if not approval_text:
        return ""
    return (
        "[Pending Approval]\n"
        f"{approval_text}\n\n"
        "Do not retry the blocked action until the user explicitly approves it."
    )


def build_system_prompt(
    memory_text: str,
    summary_text: str,
    plan_text: str = "",
    approval_text: str = "",
) -> str:
    parts = [build_base_system_prompt()]
    memory_section = build_memory_prompt_section(memory_text)
    summary_section = build_summary_prompt_section(summary_text)
    plan_section = build_plan_prompt_section(plan_text)
    approval_section = build_approval_prompt_section(approval_text)
    if memory_section:
        parts.append(memory_section)
    if summary_section:
        parts.append(summary_section)
    if plan_section:
        parts.append(plan_section)
    if approval_section:
        parts.append(approval_section)
    return "\n\n".join(parts).strip()
