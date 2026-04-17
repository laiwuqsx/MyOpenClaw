import os

from dotenv import load_dotenv


load_dotenv()

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(CORE_DIR)
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)

WORKSPACE_DIR = os.getenv("MYOPENCLAW_WORKSPACE") or os.path.join(PROJECT_ROOT, "workspace")
MEMORY_DIR = os.path.join(WORKSPACE_DIR, "memory")
DAILY_MEMORY_DIR = MEMORY_DIR
OFFICE_DIR = os.path.join(WORKSPACE_DIR, "office")
SKILLS_DIR = os.path.join(OFFICE_DIR, "skills")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
DB_PATH = os.path.join(WORKSPACE_DIR, "state.sqlite3")
TASKS_FILE = os.path.join(WORKSPACE_DIR, "tasks.json")

AGENTS_MD_PATH = os.path.join(WORKSPACE_DIR, "AGENTS.md")
SOUL_MD_PATH = os.path.join(WORKSPACE_DIR, "SOUL.md")
USER_MD_PATH = os.path.join(WORKSPACE_DIR, "USER.md")
MEMORY_MD_PATH = os.path.join(WORKSPACE_DIR, "MEMORY.md")
HEARTBEAT_MD_PATH = os.path.join(WORKSPACE_DIR, "HEARTBEAT.md")
LEGACY_USER_PROFILE_PATH = os.path.join(MEMORY_DIR, "user_profile.md")

for directory in [WORKSPACE_DIR, MEMORY_DIR, DAILY_MEMORY_DIR, OFFICE_DIR, SKILLS_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)
