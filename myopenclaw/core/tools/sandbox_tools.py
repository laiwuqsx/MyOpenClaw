import os
import platform
import re
import subprocess

from ..config import OFFICE_DIR
from .base import myopenclaw_tool


SYS_OS = platform.system()
MAX_READ_CHARS = 10_000
MAX_STDIO_CHARS = 2_000
SHELL_TIMEOUT_SECONDS = 60


def _get_safe_path(relative_path: str) -> str:
    """
    Resolve a user-supplied relative path inside the office workspace.

    The path must stay within OFFICE_DIR after normalization.
    """
    base_dir = os.path.abspath(OFFICE_DIR)
    target_path = os.path.abspath(os.path.join(base_dir, relative_path))

    if os.path.commonpath([base_dir, target_path]) != base_dir:
        raise PermissionError(
            f"Permission denied: '{relative_path}' resolves outside the office workspace."
        )
    return target_path


@myopenclaw_tool
def list_office_files(sub_dir: str = "") -> str:
    """List files and folders inside the office workspace."""
    try:
        target_dir = _get_safe_path(sub_dir)
        if not os.path.exists(target_dir):
            return f"Directory does not exist: {sub_dir}"
        if not os.path.isdir(target_dir):
            return f"Not a directory: {sub_dir}"

        items = sorted(os.listdir(target_dir))
        if not items:
            return f"[{sub_dir or 'office root'}] is empty."

        rendered = []
        for item in items:
            item_path = os.path.join(target_dir, item)
            item_type = "DIR" if os.path.isdir(item_path) else "FILE"
            rendered.append(f"{item_type} {item}")
        return "\n".join(rendered)
    except Exception as exc:
        return str(exc)


@myopenclaw_tool
def read_office_file(filepath: str) -> str:
    """Read a text file relative to the office workspace."""
    try:
        target_path = _get_safe_path(filepath)
        if not os.path.exists(target_path):
            return f"File does not exist: {filepath}"
        if os.path.isdir(target_path):
            return f"Path is a directory, not a file: {filepath}"

        with open(target_path, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()

        if len(content) > MAX_READ_CHARS:
            return content[:MAX_READ_CHARS] + "\n\n...[content truncated]..."
        return content
    except Exception as exc:
        return str(exc)


@myopenclaw_tool
def write_office_file(filepath: str, content: str, mode: str = "w") -> str:
    """Write or append text to a file relative to the office workspace."""
    try:
        if mode not in {"w", "a"}:
            return "Invalid mode: use 'w' to overwrite or 'a' to append."

        target_path = _get_safe_path(filepath)
        parent_dir = os.path.dirname(target_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        with open(target_path, mode, encoding="utf-8") as fh:
            if mode == "a" and content and not content.startswith("\n") and fh.tell() > 0:
                fh.write("\n")
            fh.write(content)

        action = "overwrote" if mode == "w" else "appended to"
        return f"Successfully {action} office file: {filepath} ({len(content)} chars)"
    except Exception as exc:
        return str(exc)


def _contains_dangerous_shell_pattern(command: str) -> bool:
    dangerous_patterns = [
        r"\.\.",
        r"(?:^|\s|[<>|&;])/",
        r"(?:^|\s|[<>|&;])~",
        r"(?:^|\s|[<>|&;])\\",
        r"(?i)(?:^|\s|[<>|&;])[a-z]:",
        r"(?i)\bcd\s+\.\.",
        r"(?i)\bpython(?:3)?\s+-c\b",
        r"(?i)\bnode\s+-e\b",
    ]
    return any(re.search(pattern, command) for pattern in dangerous_patterns)


@myopenclaw_tool
def execute_office_shell(command: str) -> str:
    """Run a non-interactive shell command with OFFICE_DIR as the working directory."""
    try:
        if _contains_dangerous_shell_pattern(command):
            return "Permission denied: command appears to escape or bypass the office workspace."

        result = subprocess.run(
            command,
            shell=True,
            cwd=OFFICE_DIR,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=SHELL_TIMEOUT_SECONDS,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        rendered = [
            f"System: {SYS_OS}",
            f"Command: {command}",
            f"Exit Code: {result.returncode}",
        ]

        if result.returncode != 0 and ("prompt" in stderr.lower() or "y/n" in stdout.lower()):
            rendered.append("Hint: the command may have expected interactive confirmation.")

        if stdout:
            rendered.append(
                "[STDOUT]\n" + (stdout[-MAX_STDIO_CHARS:] if len(stdout) > MAX_STDIO_CHARS else stdout)
            )
        if stderr:
            rendered.append(
                "[STDERR]\n" + (stderr[-MAX_STDIO_CHARS:] if len(stderr) > MAX_STDIO_CHARS else stderr)
            )

        if not stdout and not stderr:
            rendered.append("(no terminal output)")

        return "\n".join(rendered)
    except subprocess.TimeoutExpired:
        return f"Command timed out after {SHELL_TIMEOUT_SECONDS} seconds."
    except Exception as exc:
        return f"Shell execution failed: {exc}"
