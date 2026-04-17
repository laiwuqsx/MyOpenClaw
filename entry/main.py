import os

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel


console = Console()
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


def main() -> None:
    load_dotenv(ENV_PATH)
    provider = os.getenv("DEFAULT_PROVIDER", "unset")
    model = os.getenv("DEFAULT_MODEL", "unset")

    console.print(
        Panel(
            "Phase 1 bootstrap complete.\n\n"
            "The package, CLI, environment handling, and project layout are ready.\n"
            "The full agent runtime will arrive in Phase 2.\n\n"
            f"Configured provider: {provider}\n"
            f"Configured model: {model}",
            title="MyOpenClaw",
            border_style="cyan",
        )
    )


if __name__ == "__main__":
    main()
