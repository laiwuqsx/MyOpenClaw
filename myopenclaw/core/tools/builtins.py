import os
from datetime import datetime

from ..config import DAILY_MEMORY_DIR, LEGACY_USER_PROFILE_PATH
from .base import myopenclaw_tool


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
    """Read the legacy user profile markdown file if it exists."""
    if not os.path.exists(LEGACY_USER_PROFILE_PATH):
        return "No legacy user profile found."

    with open(LEGACY_USER_PROFILE_PATH, "r", encoding="utf-8", errors="ignore") as fh:
        content = fh.read().strip()
    return content or "Legacy user profile is empty."


@myopenclaw_tool
def save_user_profile(new_content: str) -> str:
    """Overwrite the legacy user profile markdown file."""
    os.makedirs(os.path.dirname(LEGACY_USER_PROFILE_PATH), exist_ok=True)
    with open(LEGACY_USER_PROFILE_PATH, "w", encoding="utf-8") as fh:
        fh.write(new_content)
    return "Legacy user profile saved."


@myopenclaw_tool
def append_daily_memory(note: str, date: str | None = None) -> str:
    """Append a durable note to the daily memory markdown file."""
    target_date = date or datetime.now().strftime("%Y-%m-%d")
    os.makedirs(DAILY_MEMORY_DIR, exist_ok=True)
    target_path = os.path.join(DAILY_MEMORY_DIR, f"{target_date}.md")
    with open(target_path, "a", encoding="utf-8") as fh:
        prefix = "" if fh.tell() == 0 else "\n"
        fh.write(f"{prefix}- {note}")
    return f"Daily memory appended to {target_date}.md"


BUILTIN_TOOLS = [
    get_current_time,
    calculator,
    read_user_profile,
    save_user_profile,
    append_daily_memory,
]
