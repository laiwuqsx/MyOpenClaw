from typing import Optional

from langchain_core.tools import BaseTool

from .runtime import create_runtime


def create_agent_app(
    provider_name: str = "openai",
    model_name: str = "gpt-4o-mini",
    tools: Optional[list[BaseTool]] = None,
    checkpointer=None,
):
    """
    Thin compatibility layer.

    The heavy lifting lives in `runtime.create_runtime()`.
    """
    return create_runtime(
        provider_name=provider_name,
        model_name=model_name,
        tools=tools,
        checkpointer=checkpointer,
    )
