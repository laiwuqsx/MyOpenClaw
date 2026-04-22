from ..config import (
    AGENTS_MD_PATH,
    DAILY_MEMORY_DIR,
    DEFAULT_DAILY_MEMORY_DAYS,
    GLOBAL_MEMORY_MD_PATH,
    GLOBAL_USER_MD_PATH,
    HEARTBEAT_MD_PATH,
    INCLUDE_LEGACY_PROFILE,
    LEGACY_USER_PROFILE_PATH,
    LOCAL_OPENCLAW_MD_PATH,
    MEMORY_MD_PATH,
    OPENCLAW_MD_PATH,
    SOUL_MD_PATH,
)
from .files import load_memory_file, load_recent_daily_memory
from .models import LoadedMemoryBlock, MemoryFileSpec


def build_memory_specs(
    session_mode: str = "main",
    include_legacy_profile: bool = INCLUDE_LEGACY_PROFILE,
) -> list[MemoryFileSpec]:
    session_mode = session_mode or "main"
    if session_mode == "heartbeat":
        return [
            MemoryFileSpec("AGENTS.md", AGENTS_MD_PATH, load_in_modes={"heartbeat"}, description="Core runtime rules"),
            MemoryFileSpec("HEARTBEAT.md", HEARTBEAT_MD_PATH, load_in_modes={"heartbeat"}, description="Heartbeat behavior"),
        ]
    if session_mode == "main":
        specs = [
            MemoryFileSpec("USER.md", GLOBAL_USER_MD_PATH, load_in_modes={"main"}, description="Global user preferences"),
            MemoryFileSpec("OPENCLAW.md", OPENCLAW_MD_PATH, load_in_modes={"main"}, description="Project instructions"),
            MemoryFileSpec(
                ".myopenclaw/OPENCLAW.md",
                LOCAL_OPENCLAW_MD_PATH,
                load_in_modes={"main"},
                description="Local project instructions",
            ),
            MemoryFileSpec("AGENTS.md", AGENTS_MD_PATH, load_in_modes={"main"}, description="Legacy project rules"),
            MemoryFileSpec("SOUL.md", SOUL_MD_PATH, load_in_modes={"main"}, description="Global assistant style guidance"),
            MemoryFileSpec("MEMORY.md", MEMORY_MD_PATH, load_in_modes={"main"}, description="Project auto-memory index"),
            MemoryFileSpec("global_MEMORY.md", GLOBAL_MEMORY_MD_PATH, load_in_modes={"main"}, description="Global durable memory"),
        ]
        if include_legacy_profile:
            specs.append(
                MemoryFileSpec(
                    "legacy_user_profile.md",
                    LEGACY_USER_PROFILE_PATH,
                    load_in_modes={"main"},
                    description="Legacy CyberClaw profile compatibility",
                )
            )
        return specs
    return [
        MemoryFileSpec("AGENTS.md", AGENTS_MD_PATH, description="Core runtime rules"),
        MemoryFileSpec("OPENCLAW.md", OPENCLAW_MD_PATH, description="Project instructions"),
        MemoryFileSpec("SOUL.md", SOUL_MD_PATH, description="Assistant style guidance"),
    ]


def load_injected_memory_blocks(
    session_mode: str = "main",
    daily_memory_days: int = DEFAULT_DAILY_MEMORY_DAYS,
    include_legacy_profile: bool = INCLUDE_LEGACY_PROFILE,
) -> list[LoadedMemoryBlock]:
    blocks: list[LoadedMemoryBlock] = []
    for spec in build_memory_specs(
        session_mode=session_mode,
        include_legacy_profile=include_legacy_profile,
    ):
        block = load_memory_file(spec)
        if block is not None:
            blocks.append(block)

    if session_mode == "main" and daily_memory_days > 0:
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
