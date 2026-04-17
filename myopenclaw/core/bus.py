import asyncio


task_queue: asyncio.Queue[str] = asyncio.Queue()


async def emit_task(content: str) -> None:
    await task_queue.put(content)
