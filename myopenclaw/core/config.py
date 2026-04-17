import os

from dotenv import load_dotenv


load_dotenv()

CORE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(CORE_DIR)
PROJECT_ROOT = os.path.dirname(PACKAGE_DIR)

WORKSPACE_DIR = os.getenv(
    "MYOPENCLAW_WORKSPACE",
    os.path.join(PROJECT_ROOT, "workspace"),
)
MEMORY_DIR = os.path.join(WORKSPACE_DIR, "memory")
OFFICE_DIR = os.path.join(WORKSPACE_DIR, "office")
SKILLS_DIR = os.path.join(OFFICE_DIR, "skills")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

for directory in [WORKSPACE_DIR, MEMORY_DIR, OFFICE_DIR, SKILLS_DIR, LOG_DIR]:
    os.makedirs(directory, exist_ok=True)
