import logging
import os
import sys

import questionary
import typer
from dotenv import load_dotenv, set_key, unset_key
from rich.console import Console
from rich.panel import Panel


ENTRY_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ENTRY_DIR)
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
os.environ.setdefault("MYOPENCLAW_CWD", os.getcwd())

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.chdir(PROJECT_ROOT)

app = typer.Typer(help="MYCLAW - Transparent local agent runtime")
memory_app = typer.Typer(help="Inspect local memory files")
project_app = typer.Typer(help="Inspect or initialize project context")
app.add_typer(memory_app, name="memory")
app.add_typer(project_app, name="project")
console = Console()

prompt_style = questionary.Style(
    [
        ("qmark", "fg:#5fd7ff bold"),
        ("question", "fg:#ffffff bold"),
        ("answer", "fg:#5fd7ff bold"),
        ("pointer", "fg:#5fd7ff bold"),
        ("highlighted", "fg:#5fd7ff bold"),
        ("instruction", "fg:#808080"),
    ]
)


def _ensure_env_file() -> None:
    if not os.path.exists(ENV_PATH):
        with open(ENV_PATH, "w", encoding="utf-8"):
            pass


def _show_boot_error() -> None:
    console.print(
        Panel(
            "MYCLAW is not configured yet.\n\n"
            "Run `myopenclaw config` first or create a `.env` file from `.env.example`.",
            title="Boot Incomplete",
            border_style="yellow",
        )
    )


@app.command("config")
def config_wizard() -> None:
    _ensure_env_file()
    console.print(
        Panel(
            "Configure the default model provider for MYCLAW.\n"
            "Phase 1 keeps this lightweight: values are saved locally to `.env`.",
            title="MYCLAW Config",
            border_style="cyan",
        )
    )

    provider = questionary.select(
        "Choose a provider:",
        choices=["openai", "anthropic", "ollama", "other"],
        style=prompt_style,
        instruction="Use arrow keys and press enter",
    ).ask()

    if not provider:
        console.print("Configuration cancelled.")
        return

    model = questionary.text(
        "Choose a model name:",
        default="gpt-4o-mini",
        style=prompt_style,
    ).ask()

    if model is None:
        console.print("Configuration cancelled.")
        return

    api_key = ""
    env_key = ""
    if provider == "openai":
        env_key = "OPENAI_API_KEY"
    elif provider == "anthropic":
        env_key = "ANTHROPIC_API_KEY"

    if env_key:
        api_key = (
            questionary.password(
                f"Enter {env_key}:",
                style=prompt_style,
            ).ask()
            or ""
        )

    base_url = (
        questionary.text(
            "Optional base URL (leave blank to skip):",
            style=prompt_style,
        ).ask()
        or ""
    )

    logging.getLogger("dotenv.main").setLevel(logging.ERROR)
    unset_key(ENV_PATH, "OPENAI_API_BASE")
    unset_key(ENV_PATH, "ANTHROPIC_BASE_URL")
    unset_key(ENV_PATH, "OLLAMA_BASE_URL")

    if env_key and api_key:
        set_key(ENV_PATH, env_key, api_key)

    if base_url:
        if provider == "openai":
            set_key(ENV_PATH, "OPENAI_API_BASE", base_url)
        elif provider == "anthropic":
            set_key(ENV_PATH, "ANTHROPIC_BASE_URL", base_url)
        elif provider == "ollama":
            set_key(ENV_PATH, "OLLAMA_BASE_URL", base_url)

    set_key(ENV_PATH, "DEFAULT_PROVIDER", provider)
    set_key(ENV_PATH, "DEFAULT_MODEL", model)

    console.print(
        Panel(
            f"Saved configuration to `{ENV_PATH}`.\n"
            f"Default provider: {provider}\n"
            f"Default model: {model}",
            border_style="green",
        )
    )


@app.command("run")
def run_agent() -> None:
    load_dotenv(ENV_PATH)
    provider = os.getenv("DEFAULT_PROVIDER")
    model = os.getenv("DEFAULT_MODEL")
    if not provider or not model:
        _show_boot_error()
        raise typer.Exit()

    import entry.main as main_module

    main_module.main()


@app.command("monitor")
def run_monitor() -> None:
    import entry.monitor as monitor_module

    monitor_module.main()


def _read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read().strip()


@memory_app.command("show")
def show_memory() -> None:
    from myopenclaw.core.config import (
        AGENTS_MD_PATH,
        GLOBAL_MEMORY_MD_PATH,
        LOCAL_OPENCLAW_MD_PATH,
        MEMORY_MD_PATH,
        OPENCLAW_MD_PATH,
        SOUL_MD_PATH,
        USER_MD_PATH,
    )

    paths = [
        ("Global USER.md", USER_MD_PATH),
        ("Global MEMORY.md", GLOBAL_MEMORY_MD_PATH),
        ("Project OPENCLAW.md", OPENCLAW_MD_PATH),
        ("Local .myopenclaw/OPENCLAW.md", LOCAL_OPENCLAW_MD_PATH),
        ("Legacy AGENTS.md", AGENTS_MD_PATH),
        ("Global SOUL.md", SOUL_MD_PATH),
        ("Project auto-memory MEMORY.md", MEMORY_MD_PATH),
    ]
    for name, path in paths:
        content = _read_text(path)
        console.print(
            Panel(
                content or "(empty or missing)",
                title=name,
                border_style="cyan" if content else "dim",
            )
        )


@memory_app.command("today")
def show_today_memory() -> None:
    from datetime import datetime

    from myopenclaw.core.config import DAILY_MEMORY_DIR

    today = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(DAILY_MEMORY_DIR, f"{today}.md")
    content = _read_text(path)
    console.print(
        Panel(
            content or f"No daily memory for {today}.",
            title=f"Daily Memory: {today}",
            border_style="cyan" if content else "dim",
        )
    )


@memory_app.command("recent")
def show_recent_memory(days: int = typer.Option(3, "--days", "-d", min=1, help="Number of recent daily files to show.")) -> None:
    from myopenclaw.core.config import DAILY_MEMORY_DIR
    from myopenclaw.core.memory.files import list_recent_daily_memory_files

    paths = list_recent_daily_memory_files(DAILY_MEMORY_DIR, days=days)
    if not paths:
        console.print(Panel("No recent daily memory files found.", title="Daily Memory", border_style="dim"))
        return

    for path in paths:
        content = _read_text(path)
        console.print(
            Panel(
                content or "(empty)",
                title=os.path.basename(path),
                border_style="cyan",
            )
        )


@memory_app.command("summary")
def show_summary() -> None:
    from myopenclaw.core.memory.summary import get_project_summary_path, load_project_summary

    content = load_project_summary()
    console.print(
        Panel(
            content or f"No summary found at {get_project_summary_path()}.",
            title="Project Summary",
            border_style="cyan" if content else "dim",
        )
    )


@project_app.command("current")
def show_current_project() -> None:
    from myopenclaw.core.config import ACTIVE_PROJECT_ROOT, PROJECT_DATA_DIR, PROJECT_ID, PROJECT_LOCAL_DIR, WORKSPACE_DIR

    console.print(
        Panel(
            "\n".join(
                [
                    f"Project root: {ACTIVE_PROJECT_ROOT}",
                    f"Project id: {PROJECT_ID}",
                    f"Project data: {PROJECT_DATA_DIR}",
                    f"Local config: {PROJECT_LOCAL_DIR}",
                    f"Runtime workspace: {WORKSPACE_DIR}",
                ]
            ),
            title="Current Project",
            border_style="cyan",
        )
    )


@project_app.command("init")
def init_project() -> None:
    from myopenclaw.core.config import ACTIVE_PROJECT_ROOT, LOCAL_OPENCLAW_MD_PATH, PROJECT_LOCAL_DIR

    os.makedirs(PROJECT_LOCAL_DIR, exist_ok=True)
    if not os.path.exists(LOCAL_OPENCLAW_MD_PATH):
        with open(LOCAL_OPENCLAW_MD_PATH, "w", encoding="utf-8") as fh:
            fh.write(
                "# OPENCLAW\n\n"
                "## Project Instructions\n\n"
                "- Add project-specific build, test, and architecture notes here.\n"
            )
    console.print(
        Panel(
            f"Initialized project context for:\n{ACTIVE_PROJECT_ROOT}\n\nCreated or reused:\n{PROJECT_LOCAL_DIR}",
            title="Project Initialized",
            border_style="green",
        )
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
