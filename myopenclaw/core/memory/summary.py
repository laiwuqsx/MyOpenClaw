def build_summary_prompt(current_summary: str, discarded_text: str) -> str:
    existing_summary = current_summary or "No existing working summary."
    return (
        "You maintain the working context summary for an agent runtime.\n\n"
        f"[Current Summary]\n{existing_summary}\n\n"
        f"[Discarded Conversation]\n{discarded_text}\n\n"
        "Task:\n"
        "- merge the important context from the discarded conversation into the working summary\n"
        "- keep only task progress, open loops, important decisions, and relevant short-term context\n"
        "- do not store stable user preferences here\n"
        "- return only the updated summary in concise prose"
    )


def merge_summary_response(raw_content: str) -> str:
    if not raw_content:
        return ""
    return raw_content.strip()
