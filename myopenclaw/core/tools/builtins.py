import os
from datetime import datetime

from ..config import DAILY_MEMORY_DIR, LEGACY_USER_PROFILE_PATH, MEMORY_MD_PATH, USER_MD_PATH
from .base import myopenclaw_tool
from .sandbox_tools import (
    execute_office_shell,
    list_office_files,
    read_office_file,
    write_office_file,
)


@myopenclaw_tool
def get_current_time() -> str:
    """Return the current local system time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@myopenclaw_tool
def calculator(expression: str) -> str:
    """Evaluate a basic math expression in a restricted environment."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as exc:
        return f"Calculation failed: {exc}"


@myopenclaw_tool
def read_user_profile() -> str:
    """Read global user memory, with legacy profile compatibility."""
    sections = []
    if os.path.exists(USER_MD_PATH):
        with open(USER_MD_PATH, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read().strip()
        if content:
            sections.append(f"[USER.md]\n{content}")

    if os.path.exists(LEGACY_USER_PROFILE_PATH):
        with open(LEGACY_USER_PROFILE_PATH, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read().strip()
        if content:
            sections.append(f"[legacy_user_profile.md]\n{content}")

    if not sections:
        return "No user profile memory found."
    return "\n\n".join(sections)


@myopenclaw_tool
def save_user_profile(new_content: str) -> str:
    """Overwrite global user memory."""
    os.makedirs(os.path.dirname(USER_MD_PATH), exist_ok=True)
    with open(USER_MD_PATH, "w", encoding="utf-8") as fh:
        fh.write(new_content)

    return "Global user profile saved to USER.md."


@myopenclaw_tool
def read_project_memory() -> str:
    """Read the current project's auto-memory index."""
    if not os.path.exists(MEMORY_MD_PATH):
        return "No project auto-memory found."
    with open(MEMORY_MD_PATH, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read().strip()
    return content or "Project auto-memory is empty."


@myopenclaw_tool
def append_project_memory(note: str) -> str:
    """Append a durable note to the current project's auto-memory index."""
    os.makedirs(os.path.dirname(MEMORY_MD_PATH), exist_ok=True)
    with open(MEMORY_MD_PATH, "a", encoding="utf-8") as fh:
        prefix = "" if fh.tell() == 0 else "\n"
        fh.write(f"{prefix}- {note}")
    return "Project memory appended to MEMORY.md."


@myopenclaw_tool
def append_daily_memory(note: str, date: str | None = None) -> str:
    """Append a durable note to the daily memory markdown file."""
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        return "Invalid date: use YYYY-MM-DD."

    os.makedirs(DAILY_MEMORY_DIR, exist_ok=True)
    target_path = os.path.join(DAILY_MEMORY_DIR, f"{target_date}.md")
    with open(target_path, "a", encoding="utf-8") as fh:
        prefix = "" if fh.tell() == 0 else "\n"
        fh.write(f"{prefix}- {note}")
    return f"Daily memory appended to {target_date}.md"


@myopenclaw_tool
def read_daily_memory(date: str) -> str:
    """Read a daily memory file by date when the user explicitly asks for it."""
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Invalid date: use YYYY-MM-DD."

    target_path = os.path.join(DAILY_MEMORY_DIR, f"{date}.md")
    if not os.path.exists(target_path):
        return f"No daily memory found for {date}."

    with open(target_path, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read().strip()
    return content or f"Daily memory for {date} is empty."


BUILTIN_TOOLS = [
    get_current_time,
    calculator,
    read_user_profile,
    save_user_profile,
    read_project_memory,
    append_project_memory,
    append_daily_memory,
    read_daily_memory,
    list_office_files,
    read_office_file,
    write_office_file,
    execute_office_shell,
]
