import os
import platform
import re
import shlex
import subprocess
import time
from dataclasses import dataclass

from ..config import OFFICE_DIR
from ..logger import audit_logger
from .base import myopenclaw_tool


SYS_OS = platform.system()
MAX_READ_CHARS = 10_000
MAX_STDIO_CHARS = 2_000
SHELL_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class ShellPolicyDecision:
    allowed: bool
    risk: str
    reason: str
    argv: list[str]


SAFE_SHELL_COMMANDS = {
    "cat",
    "find",
    "grep",
    "head",
    "ls",
    "pwd",
    "rg",
    "sed",
    "tail",
    "wc",
}

DENIED_SHELL_COMMANDS = {
    "bash",
    "chmod",
    "chown",
    "curl",
    "dd",
    "git",
    "mkfs",
    "node",
    "npm",
    "python",
    "python3",
    "rm",
    "sh",
    "sudo",
    "wget",
}

SHELL_CONTROL_TOKENS = {"|", "||", "&&", ";", ">", ">>", "<", "2>", "&"}


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


def _token_looks_like_path_escape(token: str) -> bool:
    if token in {"", ".", "--"}:
        return False
    if token == ".." or token.startswith("../") or "/../" in token or token.endswith("/.."):
        return True
    if token.startswith("/") or token.startswith("~") or token.startswith("\\"):
        return True
    if re.match(r"(?i)^[a-z]:", token):
        return True
    return False


def evaluate_shell_policy(command: str) -> ShellPolicyDecision:
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return ShellPolicyDecision(False, "blocked", f"Could not parse command: {exc}", [])

    if not argv:
        return ShellPolicyDecision(False, "blocked", "Empty command.", [])

    if any(token in SHELL_CONTROL_TOKENS for token in argv):
        return ShellPolicyDecision(False, "blocked", "Shell control operators are not allowed.", argv)

    executable = os.path.basename(argv[0])
    if executable in DENIED_SHELL_COMMANDS:
        return ShellPolicyDecision(False, "blocked", f"Command is denied by policy: {executable}", argv)

    if executable not in SAFE_SHELL_COMMANDS:
        return ShellPolicyDecision(False, "blocked", f"Command is not in the safe allowlist: {executable}", argv)

    for token in argv[1:]:
        if _token_looks_like_path_escape(token):
            return ShellPolicyDecision(False, "blocked", f"Argument escapes the office workspace: {token}", argv)

    return ShellPolicyDecision(True, "low", "Allowed safe read-only command.", argv)


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


@myopenclaw_tool
def patch_office_file(filepath: str, old_text: str, new_text: str, expected_replacements: int = 1) -> str:
    """Replace exact text inside an office workspace file."""
    try:
        if expected_replacements < 1:
            return "Invalid expected_replacements: use a positive integer."
        if old_text == "":
            return "Invalid patch: old_text must not be empty."

        target_path = _get_safe_path(filepath)
        if not os.path.exists(target_path):
            return f"File does not exist: {filepath}"
        if os.path.isdir(target_path):
            return f"Path is a directory, not a file: {filepath}"

        with open(target_path, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read()

        found = content.count(old_text)
        if found != expected_replacements:
            return (
                "Patch not applied: expected "
                f"{expected_replacements} occurrence(s), found {found}."
            )

        updated = content.replace(old_text, new_text, expected_replacements)
        with open(target_path, "w", encoding="utf-8") as fh:
            fh.write(updated)

        return f"Patched office file: {filepath} ({expected_replacements} replacement(s))"
    except Exception as exc:
        return str(exc)


@myopenclaw_tool
def execute_office_shell(command: str) -> str:
    """Run a non-interactive shell command with OFFICE_DIR as the working directory."""
    started = time.monotonic()
    decision = evaluate_shell_policy(command)
    try:
        if not decision.allowed:
            audit_logger.log_event(
                thread_id="tool",
                event="shell_blocked",
                command=command,
                reason=decision.reason,
                risk=decision.risk,
            )
            return f"Permission denied: {decision.reason}"

        result = subprocess.run(
            decision.argv,
            shell=False,
            cwd=OFFICE_DIR,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=SHELL_TIMEOUT_SECONDS,
        )
        duration_ms = int((time.monotonic() - started) * 1000)

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        audit_logger.log_event(
            thread_id="tool",
            event="shell_executed",
            command=command,
            argv=decision.argv,
            risk=decision.risk,
            exit_code=result.returncode,
            duration_ms=duration_ms,
            stdout_chars=len(stdout),
            stderr_chars=len(stderr),
        )

        rendered = [
            f"System: {SYS_OS}",
            f"Command: {command}",
            f"Policy: {decision.risk} risk - {decision.reason}",
            f"Exit Code: {result.returncode}",
            f"Duration: {duration_ms}ms",
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
        duration_ms = int((time.monotonic() - started) * 1000)
        audit_logger.log_event(
            thread_id="tool",
            event="shell_timeout",
            command=command,
            argv=decision.argv,
            duration_ms=duration_ms,
        )
        return f"Command timed out after {SHELL_TIMEOUT_SECONDS} seconds."
    except Exception as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        audit_logger.log_event(
            thread_id="tool",
            event="shell_error",
            command=command,
            argv=decision.argv,
            duration_ms=duration_ms,
            error=str(exc),
        )
        return f"Shell execution failed: {exc}"
