import os

from dotenv import load_dotenv


load_dotenv()


def _read_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        return int(raw_value or default)
    except ValueError:
        return default

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(CORE_DIR)
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)

WORKSPACE_DIR = os.getenv("MYOPENCLAW_WORKSPACE") or os.path.join(PROJECT_ROOT, "workspace")
MEMORY_DIR = os.path.join(WORKSPACE_DIR, "memory")
DAILY_MEMORY_DIR = os.path.join(MEMORY_DIR, "daily")
SUMMARY_DIR = os.path.join(MEMORY_DIR, "summaries")
OFFICE_DIR = os.path.join(WORKSPACE_DIR, "office")
SKILLS_DIR = os.path.join(OFFICE_DIR, "skills")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
DB_PATH = os.path.join(WORKSPACE_DIR, "state.sqlite3")
TASKS_FILE = os.path.join(WORKSPACE_DIR, "tasks.json")

AGENTS_MD_PATH = os.path.join(WORKSPACE_DIR, "AGENTS.md")
PROJECT_MD_PATH = os.path.join(WORKSPACE_DIR, "PROJECT.md")
SOUL_MD_PATH = os.path.join(WORKSPACE_DIR, "SOUL.md")
USER_MD_PATH = os.path.join(WORKSPACE_DIR, "USER.md")
MEMORY_MD_PATH = os.path.join(WORKSPACE_DIR, "MEMORY.md")
HEARTBEAT_MD_PATH = os.path.join(WORKSPACE_DIR, "HEARTBEAT.md")
LEGACY_USER_PROFILE_PATH = os.path.join(MEMORY_DIR, "user_profile.md")

DEFAULT_DAILY_MEMORY_DAYS = _read_int_env("MYOPENCLAW_DAILY_MEMORY_DAYS", 0)
INCLUDE_LEGACY_PROFILE = os.getenv("MYOPENCLAW_INCLUDE_LEGACY_PROFILE", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}

for directory in [WORKSPACE_DIR, MEMORY_DIR, DAILY_MEMORY_DIR, SUMMARY_DIR, OFFICE_DIR, SKILLS_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)
