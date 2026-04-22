import os
import hashlib
import re

from dotenv import load_dotenv


load_dotenv()


def _read_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value or default)
    except ValueError:
        return default


def _find_upward_marker(start_dir: str, marker: str) -> str | None:
    current = os.path.abspath(start_dir)
    while True:
        candidate = os.path.join(current, marker)
        if os.path.exists(candidate):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _discover_project_root(start_dir: str) -> str:
    return _find_upward_marker(start_dir, ".git") or _find_upward_marker(start_dir, ".myopenclaw") or os.path.abspath(start_dir)


def _safe_project_id(project_root: str) -> str:
    base = os.path.basename(os.path.abspath(project_root)) or "project"
    safe_base = re.sub(r"[^A-Za-z0-9_.-]+", "-", base).strip(".-") or "project"
    digest = hashlib.sha1(os.path.abspath(project_root).encode("utf-8")).hexdigest()[:8]
    return f"{safe_base}-{digest}"


def _resolve_global_home(fallback_root: str) -> str:
    explicit_home = os.getenv("MYOPENCLAW_HOME")
    if explicit_home:
        return explicit_home

    default_home = os.path.join(os.path.expanduser("~"), ".myopenclaw")
    try:
        os.makedirs(default_home, exist_ok=True)
        return default_home
    except PermissionError:
        return os.path.join(fallback_root, "workspace", ".myopenclaw")

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(CORE_DIR)
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)

INVOCATION_CWD = os.getenv("MYOPENCLAW_CWD") or os.getcwd()
ACTIVE_PROJECT_ROOT = _discover_project_root(INVOCATION_CWD)
PROJECT_ID = os.getenv("MYOPENCLAW_PROJECT_ID") or _safe_project_id(ACTIVE_PROJECT_ROOT)

GLOBAL_HOME = _resolve_global_home(PROJECT_ROOT)
PROJECT_DATA_DIR = os.path.join(GLOBAL_HOME, "projects", PROJECT_ID)
PROJECT_LOCAL_DIR = os.path.join(ACTIVE_PROJECT_ROOT, ".myopenclaw")

WORKSPACE_DIR = os.getenv("MYOPENCLAW_WORKSPACE") or PROJECT_DATA_DIR
MEMORY_DIR = os.path.join(WORKSPACE_DIR, "memory")
DAILY_MEMORY_DIR = os.path.join(WORKSPACE_DIR, "daily")
SUMMARY_DIR = os.path.join(WORKSPACE_DIR, "summaries")
SUMMARY_MD_PATH = os.path.join(WORKSPACE_DIR, "SUMMARY.md")
OFFICE_DIR = os.getenv("MYOPENCLAW_OFFICE") or os.path.join(PROJECT_LOCAL_DIR, "office")
SKILLS_DIR = os.path.join(OFFICE_DIR, "skills")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
DB_PATH = os.path.join(WORKSPACE_DIR, "state.sqlite3")
TASKS_FILE = os.path.join(WORKSPACE_DIR, "tasks.json")

GLOBAL_USER_MD_PATH = os.path.join(GLOBAL_HOME, "USER.md")
GLOBAL_MEMORY_MD_PATH = os.path.join(GLOBAL_HOME, "MEMORY.md")
OPENCLAW_MD_PATH = os.path.join(ACTIVE_PROJECT_ROOT, "OPENCLAW.md")
LOCAL_OPENCLAW_MD_PATH = os.path.join(PROJECT_LOCAL_DIR, "OPENCLAW.md")
AGENTS_MD_PATH = os.path.join(ACTIVE_PROJECT_ROOT, "AGENTS.md")
PROJECT_MD_PATH = OPENCLAW_MD_PATH
SOUL_MD_PATH = os.path.join(GLOBAL_HOME, "SOUL.md")
USER_MD_PATH = GLOBAL_USER_MD_PATH
MEMORY_MD_PATH = os.path.join(MEMORY_DIR, "MEMORY.md")
HEARTBEAT_MD_PATH = os.path.join(WORKSPACE_DIR, "HEARTBEAT.md")
LEGACY_USER_PROFILE_PATH = os.path.join(MEMORY_DIR, "user_profile.md")

DEFAULT_DAILY_MEMORY_DAYS = _read_int_env("MYOPENCLAW_DAILY_MEMORY_DAYS", 0)
INCLUDE_LEGACY_PROFILE = os.getenv("MYOPENCLAW_INCLUDE_LEGACY_PROFILE", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

for directory in [GLOBAL_HOME, PROJECT_DATA_DIR, WORKSPACE_DIR, MEMORY_DIR, DAILY_MEMORY_DIR, SUMMARY_DIR, PROJECT_LOCAL_DIR, OFFICE_DIR, SKILLS_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)
