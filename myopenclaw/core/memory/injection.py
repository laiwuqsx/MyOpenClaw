from ..config import (
    AGENTS_MD_PATH,
    DAILY_MEMORY_DIR,
    HEARTBEAT_MD_PATH,
    LEGACY_USER_PROFILE_PATH,
    MEMORY_MD_PATH,
    SOUL_MD_PATH,
    USER_MD_PATH,
)
from .files import load_memory_file, load_recent_daily_memory
from .models import LoadedMemoryBlock, MemoryFileSpec


def build_memory_specs(session_mode: str = "main") -> list[MemoryFileSpec]:
    session_mode = session_mode or "main"
    if session_mode == "heartbeat":
        return [
            MemoryFileSpec("AGENTS.md", AGENTS_MD_PATH, load_in_modes={"heartbeat"}, description="Core runtime rules"),
            MemoryFileSpec("HEARTBEAT.md", HEARTBEAT_MD_PATH, load_in_modes={"heartbeat"}, description="Heartbeat behavior"),
        ]
    if session_mode == "main":
        return [
            MemoryFileSpec("AGENTS.md", AGENTS_MD_PATH, load_in_modes={"main"}, description="Core runtime rules"),
            MemoryFileSpec("SOUL.md", SOUL_MD_PATH, load_in_modes={"main"}, description="Assistant style guidance"),
            MemoryFileSpec("USER.md", USER_MD_PATH, load_in_modes={"main"}, description="User-facing memory"),
            MemoryFileSpec("MEMORY.md", MEMORY_MD_PATH, load_in_modes={"main"}, description="Durable memory"),
            MemoryFileSpec(
                "legacy_user_profile.md",
                LEGACY_USER_PROFILE_PATH,
                load_in_modes={"main"},
                description="Legacy CyberClaw profile compatibility",
            ),
        ]
    return [
        MemoryFileSpec("AGENTS.md", AGENTS_MD_PATH, description="Core runtime rules"),
        MemoryFileSpec("SOUL.md", SOUL_MD_PATH, description="Assistant style guidance"),
    ]


def load_injected_memory_blocks(
    session_mode: str = "main",
    daily_memory_days: int = 2,
) -> list[LoadedMemoryBlock]:
    blocks: list[LoadedMemoryBlock] = []
    for spec in build_memory_specs(session_mode=session_mode):
        block = load_memory_file(spec)
        if block is not None:
            blocks.append(block)

    if session_mode == "main":
        blocks.extend(
            load_recent_daily_memory(
                DAILY_MEMORY_DIR,
                days=daily_memory_days,
                max_chars_per_file=3000,
            )
        )
    return blocks


def format_memory_blocks_for_prompt(blocks: list[LoadedMemoryBlock]) -> str:
    formatted: list[str] = []
    for block in blocks:
        if not block.content:
            continue
        suffix = "\n[Truncated]" if block.truncated else ""
        formatted.append(f"[Memory: {block.name}]\n{block.content}{suffix}")
    return "\n\n".join(formatted).strip()
