from typing import Optional

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .context import AgentState
from .logger import audit_logger, set_audit_context
from .permissions import set_permission_context, wrap_tool_call_with_permissions
from .provider import get_provider
from .session_state import build_session_context
from .skill_loader import load_dynamic_skills
from .tools.base import get_tool_contract
from .tools.builtins import BUILTIN_TOOLS
from .turn_manager import run_agent_turn


def create_runtime(
    provider_name: str = "openai",
    model_name: str = "gpt-4o-mini",
    tools: Optional[list[BaseTool]] = None,
    checkpointer=None,
):
    actual_tools = tools if tools is not None else BUILTIN_TOOLS + load_dynamic_skills()
    tool_contracts = {tool.name: get_tool_contract(tool) for tool in actual_tools}
    llm = get_provider(provider_name=provider_name, model_name=model_name)
    llm_with_tools = llm.bind_tools(actual_tools)
    tool_node = ToolNode(actual_tools, wrap_tool_call=wrap_tool_call_with_permissions)

    def agent_node(state: AgentState, config: RunnableConfig) -> dict:
        session_context = build_session_context(
            config=config,
            provider_name=provider_name,
            model_name=model_name,
        )
        set_audit_context(
            session_id=session_context.session_id,
            session_mode=session_context.session_mode,
            thread_id=session_context.thread_id,
            provider=session_context.provider_name,
            model=session_context.model_name,
        )
        configurable = (config or {}).get("configurable", {})
        set_permission_context(
            approval_policy=configurable.get("approval_policy", "auto"),
            approved_tools=configurable.get("approved_tools") or [],
            approved_permissions=configurable.get("approved_permissions") or [],
        )
        result = run_agent_turn(
            state=state,
            llm=llm,
            llm_with_tools=llm_with_tools,
            session_context=session_context,
            audit_logger=audit_logger,
            tool_contracts=tool_contracts,
        )
        return result.state_updates

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")
    return workflow.compile(checkpointer=checkpointer)
