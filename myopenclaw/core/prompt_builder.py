def build_base_system_prompt() -> str:
    return (
        "You are MyOpenClaw, a transparent and controllable local AI assistant.\n\n"
        "[Core Principles]\n"
        "1. Be concise, practical, and natural.\n"
        "2. Use long-term memory and recent context together.\n"
        "3. Stay within the workspace sandbox boundaries.\n"
        "4. Prefer explicit tool use over making up external actions.\n"
    )


def build_memory_prompt_section(memory_text: str) -> str:
    if not memory_text:
        return ""
    return f"[Injected Memory]\n{memory_text}"


def build_summary_prompt_section(summary_text: str) -> str:
    if not summary_text:
        return ""
    return f"[Working Summary]\n{summary_text}"


def build_system_prompt(memory_text: str, summary_text: str) -> str:
    parts = [build_base_system_prompt()]
    memory_section = build_memory_prompt_section(memory_text)
    summary_section = build_summary_prompt_section(summary_text)
    if memory_section:
        parts.append(memory_section)
    if summary_section:
        parts.append(summary_section)
    return "\n\n".join(parts).strip()
