import asyncio
import os
import random
import time

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.application import get_app
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel

from myopenclaw.core.agent import create_agent_app
from myopenclaw.core.config import DB_PATH
from myopenclaw.core.control import format_approval_state_for_prompt, format_plan_state_for_prompt


console = Console(no_color=True, force_terminal=False)
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

    logo = """
███╗   ███╗██╗   ██╗ ██████╗ ██████╗ ███████╗███╗   ██╗
████╗ ████║╚██╗ ██╔╝██╔═══██╗██╔══██╗██╔════╝████╗  ██║
██╔████╔██║ ╚████╔╝ ██║   ██║██████╔╝█████╗  ██╔██╗ ██║
██║╚██╔╝██║  ╚██╔╝  ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║
██║ ╚═╝ ██║   ██║   ╚██████╔╝██║     ███████╗██║ ╚████║
╚═╝     ╚═╝   ╚═╝    ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝
""".strip("\n")

    quote = random.choice(
        [
            "Local-first agents, readable by humans.",
            "Inspect the loop, not just the answer.",
            "Use tools when they make the answer better.",
            "A small runtime beats a mysterious black box.",
        ]
    )

    print(logo)
    print(" MYCLAW Local Runtime")
    print()
    print(quote)
    print()
    print(f"Configured provider: {provider}    Configured model: {model}")
    print()


def cprint(text: str = "", end: str = "\n") -> None:
    print(str(text), end=end, flush=True)


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

    def toolbar(self) -> AnyFormattedText:
        if not self.is_spinning:
            return ""
        elapsed = time.time() - self.start_time
        if self.is_tool_calling:
            label = self.tool_msg
        else:
            label = self.words[int(elapsed) % len(self.words)]
        frame = self.frames[int(elapsed * 12) % len(self.frames)]
        return f"  {frame} {label} [{elapsed:.1f}s]"


async def run_interactive_runtime(provider: str, model: str) -> None:
    print_banner(provider=provider, model=model)

    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as memory:
        app = create_agent_app(
            provider_name=provider,
            model_name=model,
            checkpointer=memory,
        )
        approved_tools: set[str] = set()
        approved_permissions: set[str] = set()
        config = {
            "configurable": {
                "thread_id": "local_main",
                "approval_policy": "deny_writes",
                "approved_tools": sorted(approved_tools),
                "approved_permissions": sorted(approved_permissions),
            }
        }
        spinner = SpinnerState()

        session = PromptSession(
            bottom_toolbar=spinner.toolbar,
            style=Style.from_dict({"bottom-toolbar": "bg:default fg:default noreverse"}),
            erase_when_done=True,
            reserve_space_for_menu=0,
        )
        prompt_message = "  ❯ "
        placeholder_text = "message..."

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
                    cprint("\n  Session interrupted. Exiting.")
                    break

                user_input = user_input.strip()
                if not user_input:
                    continue
                if user_input.lower() in {"/exit", "/quit"}:
                    cprint("  MYCLAW shutting down.")
                    break
                if user_input.lower() == "/plan":
                    snapshot = await app.aget_state(config)
                    plan_text = format_plan_state_for_prompt((snapshot.values or {}).get("plan_state"))
                    cprint(f"  {plan_text or 'No active runtime plan.'}\n")
                    continue
                if user_input.lower() == "/approvals":
                    snapshot = await app.aget_state(config)
                    approval_text = format_approval_state_for_prompt((snapshot.values or {}).get("approval_state"))
                    cprint(f"  {approval_text or 'No pending approval requests.'}\n")
                    continue
                if user_input.lower().startswith("/approve "):
                    target = user_input[len("/approve ") :].strip()
                    if not target:
                        cprint("  Usage: /approve <tool_name|permission_mode>\n")
                        continue
                    snapshot = await app.aget_state(config)
                    pending = (snapshot.values or {}).get("approval_state") or {}
                    if target == pending.get("tool_name"):
                        approved_tools.add(target)
                    else:
                        approved_permissions.add(target)
                    config["configurable"]["approved_tools"] = sorted(approved_tools)
                    config["configurable"]["approved_permissions"] = sorted(approved_permissions)
                    await app.aupdate_state(config, {"approval_state": {}})
                    cprint(f"  Approved: {target}\n")
                    continue

                cprint(f"  ❯ {user_input}\n")
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
                                        cprint(f"  ● Tool Call: {tool_call['name']}")
                                        cprint()
                                elif getattr(last_msg, "content", None):
                                    spinner.stop()
                                    content = str(last_msg.content).strip()
                                    if content:
                                        lines = content.splitlines()
                                        first = lines[0]
                                        remainder = lines[1:]
                                        formatted = f"  ❯ {first}"
                                        for line in remainder:
                                            formatted += f"\n    {line}"
                                        cprint(formatted)
                            else:
                                spinner.is_tool_calling = False
                except Exception as exc:
                    spinner.stop()
                    console.print(
                        Panel(
                            f"Runtime error:\n{exc}",
                            title="MYCLAW",
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
                "MYCLAW is not configured yet.\n\n"
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
                title="MYCLAW Startup Error",
                border_style="red",
            )
        )


if __name__ == "__main__":
    main()
