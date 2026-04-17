from dataclasses import dataclass, field


@dataclass(frozen=True)
class MemoryFileSpec:
    name: str
    path: str
    required: bool = False
    max_chars: int = 4000
    load_in_modes: set[str] = field(default_factory=lambda: {"main"})
    description: str = ""


@dataclass(frozen=True)
class LoadedMemoryBlock:
    name: str
    path: str
    content: str
    truncated: bool = False
    source_type: str = "file"


@dataclass
class SummaryState:
    working_summary: str = ""
    open_loops: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    durable_memory_candidates: list[str] = field(default_factory=list)
