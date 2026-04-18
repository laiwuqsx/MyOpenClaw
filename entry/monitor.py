from rich.console import Console
from rich.panel import Panel


console = Console()


def main() -> None:
    console.print(
        Panel(
            "Monitor bootstrap is in place.\n"
            "Live audit rendering will be implemented in a later phase.",
            title="MYCLAW Monitor",
            border_style="magenta",
        )
    )


if __name__ == "__main__":
    main()
