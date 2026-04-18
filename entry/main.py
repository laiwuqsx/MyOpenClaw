import asyncio
import os
import random
import time

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.application import get_app
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel

from myopenclaw.core.agent import create_agent_app
from myopenclaw.core.config import DB_PATH


console = Console()
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def type_line(text: str, delay: float = 0.004) -> None:
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()


def print_banner(provider: str, model: str) -> None:
    clear_screen()

    cyan = "\033[38;5;51m"
    green = "\033[38;5;84m"
    silver = "\033[38;5;250m"
    white = "\033[37m"
    bold = "\033[1m"
    reset = "\033[0m"

    logo = f"""{cyan}{bold}
███╗   ███╗██╗   ██╗ ██████╗ ██████╗ ███████╗███╗   ██╗
████╗ ████║╚██╗ ██╔╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║
██╔████╔██║ ╚████╔╝ ██║   ██║██████╔╝█████╗  ██╔██╗ ██║
██║╚██╔╝██║  ╚██╔╝  ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║
██║ ╚═╝ ██║   ██║   ╚██████╔╝██║     ███████╗██║ ╚████║
╚═╝     ╚═╝   ╚═╝    ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝
{reset}"""

    quote = random.choice(
        [
            "Local-first agents, readable by humans.",
            "Inspect the loop, not just the answer.",
            "Use tools when they make the answer better.",
            "A small runtime beats a mysterious black box.",
        ]
    )

    print(logo)
    print(f"{white}{bold} MyOpenClaw Local Runtime {reset}")
    print()
    print(f"{silver}{quote}{reset}")
    print()
    type_line(
        f"{green}Configured provider:{reset} {provider}    "
        f"{green}Configured model:{reset} {model}"
    )
    print()


def cprint(text: str = "", end: str = "\n") -> None:
    print_formatted_text(ANSI(str(text)), end=end)


class SpinnerState:
    def __init__(self) -> None:
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.words = [
            "Thinking...",
            "Checking memory...",
            "Preparing context...",
            "Evaluating tools...",
            "Working...",
        ]
        self.is_spinning = False
        self.is_tool_calling = False
        self.tool_msg = ""
        self.start_time = 0.0

    def start(self) -> None:
        self.is_spinning = True
        self.is_tool_calling = False
        self.tool_msg = ""
        self.start_time = time.time()

    def stop(self) -> None:
        self.is_spinning = False
        self.is_tool_calling = False
        self.tool_msg = ""

    def toolbar(self) -> ANSI:
        if not self.is_spinning:
            return ANSI("")
        elapsed = time.time() - self.start_time
        if self.is_tool_calling:
            label = self.tool_msg
        else:
            label = self.words[int(elapsed) % len(self.words)]
        frame = self.frames[int(elapsed * 12) % len(self.frames)]
        return ANSI(
            f"  \033[38;5;51m{frame}\033[0m "
            f"\033[38;5;250m{label}\033[0m "
            f"\033[38;5;84m[{elapsed:.1f}s]\033[0m"
        )


async def run_interactive_runtime(provider: str, model: str) -> None:
    print_banner(provider=provider, model=model)

    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory:
        app = create_agent_app(
            provider_name=provider,
            model_name=model,
            checkpointer=memory,
        )
        config = {"configurable": {"thread_id": "local_main"}}
        spinner = SpinnerState()

        session = PromptSession(
            bottom_toolbar=spinner.toolbar,
            style=Style.from_dict({"bottom-toolbar": "bg:default fg:default noreverse"}),
            erase_when_done=True,
            reserve_space_for_menu=0,
        )
        prompt_message = ANSI("  \033[38;5;51m❯\033[0m ")
        placeholder_text = ANSI("\033[3m\033[38;5;242mmessage...\033[0m")

        async def redraw_timer() -> None:
            while True:
                if spinner.is_spinning:
                    try:
                        get_app().invalidate()
                    except Exception:
                        pass
                await asyncio.sleep(0.08)

        redraw_task = asyncio.create_task(redraw_timer())
        try:
            while True:
                try:
                    user_input = await session.prompt_async(
                        prompt_message,
                        placeholder=placeholder_text,
                    )
                except (KeyboardInterrupt, EOFError):
                    cprint("\n  \033[38;5;84mSession interrupted. Exiting.\033[0m")
                    break

                user_input = user_input.strip()
                if not user_input:
                    continue
                if user_input.lower() in {"/exit", "/quit"}:
                    cprint("  \033[38;5;84mMyOpenClaw shutting down.\033[0m")
                    break

                cprint(f"\033[48;2;38;38;38m\033[38;5;255m  ❯ {user_input}  \033[0m\n")
                spinner.start()
                inputs = {"messages": [HumanMessage(content=user_input)]}

                try:
                    async for event in app.astream(inputs, config=config, stream_mode="updates"):
                        for node_name, node_data in event.items():
                            if node_name == "agent":
                                last_msg = node_data["messages"][-1]
                                if getattr(last_msg, "tool_calls", None):
                                    for tool_call in last_msg.tool_calls:
                                        spinner.is_tool_calling = True
                                        spinner.tool_msg = f"Using tool: {tool_call['name']}"
                                        cprint(f"  ● \033[38;5;51mTool Call:\033[0m {tool_call['name']}")
                                        cprint()
                                elif getattr(last_msg, "content", None):
                                    spinner.stop()
                                    content = str(last_msg.content).strip()
                                    if content:
                                        lines = content.splitlines()
                                        first = lines[0]
                                        remainder = lines[1:]
                                        formatted = f"  \033[38;5;84m❯\033[0m \033[38;5;250m{first}"
                                        for line in remainder:
                                            formatted += f"\n    {line}"
                                        formatted += "\033[0m"
                                        cprint(formatted)
                            else:
                                spinner.is_tool_calling = False
                except Exception as exc:
                    spinner.stop()
                    console.print(
                        Panel(
                            f"Runtime error:\n{exc}",
                            title="MyOpenClaw",
                            border_style="red",
                        )
                    )
                finally:
                    spinner.stop()
                    cprint()
        finally:
            redraw_task.cancel()


def main() -> None:
    load_dotenv(ENV_PATH)
    provider = os.getenv("DEFAULT_PROVIDER", "unset")
    model = os.getenv("DEFAULT_MODEL", "unset")
    if not provider or provider == "unset" or not model or model == "unset":
        console.print(
            Panel(
                "MyOpenClaw is not configured yet.\n\n"
                "Run `myopenclaw config` first or create `.env` from `.env.example`.",
                title="Boot Incomplete",
                border_style="yellow",
            )
        )
        return

    try:
        with patch_stdout():
            asyncio.run(run_interactive_runtime(provider=provider, model=model))
    except Exception as exc:
        console.print(
            Panel(
                f"Failed to start the runtime.\n\n{exc}",
                title="MyOpenClaw Startup Error",
                border_style="red",
            )
        )


if __name__ == "__main__":
    main()
