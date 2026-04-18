from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .context import AgentState
from .logger import audit_logger
from .provider import get_provider
from .session_state import build_session_context
from .skill_loader import load_dynamic_skills
from .tools.builtins import BUILTIN_TOOLS
from .turn_manager import run_agent_turn


def create_runtime(
    provider_name: str = "openai",
    model_name: str = "gpt-4o-mini",
    tools: Optional[list[BaseTool]] = None,
    checkpointer=None,
):
    actual_tools = tools if tools is not None else BUILTIN_TOOLS + load_dynamic_skills()
    llm = get_provider(provider_name=provider_name, model_name=model_name)
    llm_with_tools = llm.bind_tools(actual_tools)
    tool_node = ToolNode(actual_tools)

    def agent_node(state: AgentState, config: RunnableConfig) -> dict:
        session_context = build_session_context(
            config=config,
            provider_name=provider_name,
            model_name=model_name,
        )
        result = run_agent_turn(
            state=state,
            llm=llm,
            llm_with_tools=llm_with_tools,
            session_context=session_context,
            audit_logger=audit_logger,
        )
        return result.state_updates

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    return workflow.compile(checkpointer=checkpointer)
