from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Type

import asyncio
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel

CONTRACT_METADATA_KEY = "myopenclaw/contract"


@dataclass(frozen=True)
class ToolContract:
    name: str
    risk: str = "low"
    permission_mode: str = "read_only"
    requires_approval: bool = False
    read_only: bool = True
    write_scope: str = "none"
    tags: tuple[str, ...] = field(default_factory=tuple)


def serialize_tool_contract(contract: ToolContract) -> dict[str, Any]:
    payload = asdict(contract)
    payload["tags"] = list(contract.tags)
    return payload


def get_tool_contract(tool_obj: BaseTool) -> dict[str, Any]:
    metadata = dict(getattr(tool_obj, "metadata", {}) or {})
    contract = metadata.get(CONTRACT_METADATA_KEY)
    return contract if isinstance(contract, dict) else {}


def myopenclaw_tool(
    func: Callable | None = None,
    *,
    risk: str = "low",
    permission_mode: str = "read_only",
    requires_approval: bool = False,
    read_only: bool = True,
    write_scope: str = "none",
    tags: tuple[str, ...] = (),
):
    def decorator(inner: Callable) -> BaseTool:
        tool_obj = tool(inner)
        contract = ToolContract(
            name=tool_obj.name,
            risk=risk,
            permission_mode=permission_mode,
            requires_approval=requires_approval,
            read_only=read_only,
            write_scope=write_scope,
            tags=tuple(tags),
        )
        metadata = dict(getattr(tool_obj, "metadata", {}) or {})
        metadata[CONTRACT_METADATA_KEY] = serialize_tool_contract(contract)
        tool_obj.metadata = metadata
        return tool_obj

    if func is not None:
        return decorator(func)
    return decorator


class MyOpenClawBaseTool(BaseTool, ABC):
    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    def _run(self, **kwargs: Any) -> Any:
        raise NotImplementedError

    async def _arun(self, **kwargs: Any) -> Any:
        return await asyncio.to_thread(self._run, **kwargs)
