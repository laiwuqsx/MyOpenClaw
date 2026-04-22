import os
import re

from ..config import SUMMARY_DIR


EMPTY_SUMMARY_MARKERS = {
    "",
    "No existing working summary.",
    "No existing working summary",
}


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
    return normalize_summary_text(raw_content)


def normalize_summary_text(summary: str) -> str:
    """
    Normalize the short-term working summary before it is kept in session state.

    Durable user preferences belong in memory files, so this summary should stay
    concise and focused on active task context.
    """
    normalized = (summary or "").strip()
    if normalized in EMPTY_SUMMARY_MARKERS:
        return ""
    return normalized


def _safe_summary_filename(thread_id: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", thread_id or "system_default").strip("._")
    return safe_id or "system_default"


def get_thread_summary_path(thread_id: str) -> str:
    return os.path.join(SUMMARY_DIR, f"{_safe_summary_filename(thread_id)}.md")


def load_thread_summary(thread_id: str) -> str:
    path = get_thread_summary_path(thread_id)
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return normalize_summary_text(fh.read())
    except Exception:
        return ""


def save_thread_summary(thread_id: str, summary: str) -> str:
    normalized = normalize_summary_text(summary)
    path = get_thread_summary_path(thread_id)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        if normalized:
            fh.write(normalized.rstrip() + "\n")
    return path
