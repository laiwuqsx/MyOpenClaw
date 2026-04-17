from abc import ABC, abstractmethod
from typing import Any, Type

import asyncio
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel


myopenclaw_tool = tool


class MyOpenClawBaseTool(BaseTool, ABC):
    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def _arun(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._run, **kwargs)
