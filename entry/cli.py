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

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.chdir(PROJECT_ROOT)

app = typer.Typer(help="MYCLAW - Transparent local agent runtime")
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
