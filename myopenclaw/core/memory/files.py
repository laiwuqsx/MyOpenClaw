import os
import re
from datetime import date, datetime

from .models import LoadedMemoryBlock, MemoryFileSpec


def read_text_file_if_exists(path: str, max_chars: int | None = None) -> tuple[str, bool]:
    if not os.path.exists(path):
        return "", False

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            content = fh.read().strip()
    except Exception:
        return "", False

    if max_chars is not None and max_chars >= 0 and len(content) > max_chars:
        return content[:max_chars], True
    return content, False


def list_recent_daily_memory_files(memory_dir: str, days: int = 2) -> list[str]:
    if not os.path.isdir(memory_dir):
        return []

    today = date.today()
    dated_files: list[tuple[datetime, str]] = []
    for name in os.listdir(memory_dir):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.md", name):
            continue
        try:
            parsed = datetime.strptime(name[:-3], "%Y-%m-%d")
        except ValueError:
            continue
        if parsed.date() > today:
            continue
        dated_files.append((parsed, os.path.join(memory_dir, name)))

    dated_files.sort(key=lambda item: item[0], reverse=True)
    return [path for _, path in dated_files[:days]]


def load_memory_file(spec: MemoryFileSpec) -> LoadedMemoryBlock | None:
    content, truncated = read_text_file_if_exists(spec.path, max_chars=spec.max_chars)
    if not content and not spec.required:
        return None
    return LoadedMemoryBlock(
        name=spec.name,
        path=spec.path,
        content=content,
        truncated=truncated,
        source_type="file",
    )


def load_recent_daily_memory(
    memory_dir: str,
    days: int,
    max_chars_per_file: int,
) -> list[LoadedMemoryBlock]:
    blocks: list[LoadedMemoryBlock] = []
    for path in list_recent_daily_memory_files(memory_dir, days=days):
        content, truncated = read_text_file_if_exists(path, max_chars=max_chars_per_file)
        if not content:
            continue
        blocks.append(
            LoadedMemoryBlock(
                name=os.path.basename(path),
                path=path,
                content=content,
                truncated=truncated,
                source_type="daily_memory",
            )
        )
    return blocks
