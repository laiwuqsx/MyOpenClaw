import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Type

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.types import Command
from pydantic import BaseModel, Field

from .control import build_approval_state, clear_approval_state, merge_command_update
from .logger import audit_logger
from .tools.base import get_tool_contract


READ_ONLY_PERMISSION_MODES = {
    "read_only",
    "workspace_read",
}
WRITE_PERMISSION_MODES = {
    "workspace_write",
    "workspace_patch",
    "memory_write",
    "memory_append",
    "memory_patch",
}

_PERMISSION_CONTEXT: ContextVar["PermissionContext"] = ContextVar(
    "myopenclaw_permission_context",
    default=None,
)


@dataclass(frozen=True)
class PermissionContext:
    approval_policy: str = "auto"
    approved_tools: frozenset[str] = field(default_factory=frozenset)
    approved_permissions: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ToolPermissionDecision:
    allowed: bool
    status: str
    reason: str
    risk: str
    permission_mode: str
    approval_required: bool
    tool_name: str
    write_scope: str
    contract: dict[str, Any]


def set_permission_context(
    approval_policy: str = "auto",
    approved_tools: list[str] | None = None,
    approved_permissions: list[str] | None = None,
) -> None:
    _PERMISSION_CONTEXT.set(
        build_permission_context(
            approval_policy=approval_policy,
            approved_tools=approved_tools,
            approved_permissions=approved_permissions,
        )
    )


def get_permission_context() -> PermissionContext:
    context = _PERMISSION_CONTEXT.get()
    return context if context is not None else PermissionContext()


def clear_permission_context() -> None:
    _PERMISSION_CONTEXT.set(PermissionContext())


def build_permission_context(
    approval_policy: str = "auto",
    approved_tools: list[str] | None = None,
    approved_permissions: list[str] | None = None,
) -> PermissionContext:
    return PermissionContext(
        approval_policy=approval_policy,
        approved_tools=frozenset(approved_tools or []),
        approved_permissions=frozenset(approved_permissions or []),
    )


def permission_context_from_config(config: dict[str, Any] | None) -> PermissionContext:
    configurable = dict((config or {}).get("configurable", {}) or {})
    return build_permission_context(
        approval_policy=str(configurable.get("approval_policy", "auto")),
        approved_tools=list(configurable.get("approved_tools") or []),
        approved_permissions=list(configurable.get("approved_permissions") or []),
    )


def evaluate_tool_permission(
    tool_name: str,
    contract: dict[str, Any],
    permission_context: PermissionContext | None = None,
) -> ToolPermissionDecision:
    if not contract:
        return ToolPermissionDecision(
            allowed=False,
            status="blocked",
            reason="Tool is missing an explicit permission contract.",
            risk="blocked",
            permission_mode="unknown",
            approval_required=False,
            tool_name=tool_name,
            write_scope="unknown",
            contract={},
        )

    context = permission_context or get_permission_context()
    permission_mode = str(contract.get("permission_mode", "unknown"))
    risk = str(contract.get("risk", "unknown"))
    requires_approval = bool(contract.get("requires_approval", False))
    read_only = bool(contract.get("read_only", False))
    write_scope = str(contract.get("write_scope", "unknown"))

    if permission_mode == "unknown":
        return ToolPermissionDecision(
            allowed=False,
            status="blocked",
            reason="Tool contract has no permission_mode.",
            risk="blocked",
            permission_mode=permission_mode,
            approval_required=False,
            tool_name=tool_name,
            write_scope=write_scope,
            contract=contract,
        )

    if read_only and permission_mode in WRITE_PERMISSION_MODES:
        return ToolPermissionDecision(
            allowed=False,
            status="blocked",
            reason="Tool contract is inconsistent: read_only tool cannot use a write permission mode.",
            risk="blocked",
            permission_mode=permission_mode,
            approval_required=False,
            tool_name=tool_name,
            write_scope=write_scope,
            contract=contract,
        )

    if not read_only and permission_mode in READ_ONLY_PERMISSION_MODES and permission_mode != "structured_shell_policy":
        return ToolPermissionDecision(
            allowed=False,
            status="blocked",
            reason="Tool contract is inconsistent: write-capable tool cannot use a read-only permission mode.",
            risk="blocked",
            permission_mode=permission_mode,
            approval_required=False,
            tool_name=tool_name,
            write_scope=write_scope,
            contract=contract,
        )

    auto_approved = (
        tool_name in context.approved_tools or permission_mode in context.approved_permissions
    )

    if requires_approval and not auto_approved:
        return ToolPermissionDecision(
            allowed=False,
            status="approval_required",
            reason="Tool requires explicit approval before execution.",
            risk=risk,
            permission_mode=permission_mode,
            approval_required=True,
            tool_name=tool_name,
            write_scope=write_scope,
            contract=contract,
        )

    if context.approval_policy == "deny_writes" and not read_only and not auto_approved:
        return ToolPermissionDecision(
            allowed=False,
            status="approval_required",
            reason="Current permission policy requires approval for write-capable tools.",
            risk=risk,
            permission_mode=permission_mode,
            approval_required=True,
            tool_name=tool_name,
            write_scope=write_scope,
            contract=contract,
        )

    return ToolPermissionDecision(
        allowed=True,
        status="allowed",
        reason="Tool contract allowed by current permission policy.",
        risk=risk,
        permission_mode=permission_mode,
        approval_required=requires_approval,
        tool_name=tool_name,
        write_scope=write_scope,
        contract=contract,
    )


def build_permission_denied_message(decision: ToolPermissionDecision) -> str:
    lines = [
        "Permission denied by runtime policy.",
        f"Tool: {decision.tool_name}",
        f"Permission: {decision.permission_mode}",
        f"Risk: {decision.risk}",
        f"Write Scope: {decision.write_scope}",
        f"Approval Required: {'yes' if decision.approval_required else 'no'}",
        f"Reason: {decision.reason}",
    ]
    return "\n".join(lines)


def wrap_tool_call_with_permissions(request, execute):
    tool_name = request.tool_call["name"]
    contract = get_tool_contract(request.tool)
    started = time.monotonic()
    runtime_config = getattr(getattr(request, "runtime", None), "config", None)
    permission_context = permission_context_from_config(runtime_config)
    decision = evaluate_tool_permission(
        tool_name=tool_name,
        contract=contract,
        permission_context=permission_context,
    )
    audit_logger.log_event(
        thread_id="tool",
        event="tool_permission",
        event_family="tool",
        status=decision.status,
        tool=tool_name,
        permission=decision.permission_mode,
        approval_required=decision.approval_required,
        risk=decision.risk,
        contract=decision.contract,
        payload={
            "reason": decision.reason,
            "write_scope": decision.write_scope,
        },
    )

    if not decision.allowed:
        message = build_permission_denied_message(decision)
        audit_logger.log_event(
            thread_id="tool",
            event="tool_blocked",
            event_family="tool",
            status=decision.status,
            tool=tool_name,
            permission=decision.permission_mode,
            approval_required=decision.approval_required,
            risk=decision.risk,
            contract=decision.contract,
            error=decision.reason,
            payload={
                "reason": decision.reason,
                "write_scope": decision.write_scope,
                "args": request.tool_call.get("args", {}),
            },
        )
        tool_message = ToolMessage(
            content=message,
            name=tool_name,
            tool_call_id=request.tool_call["id"],
            status="error",
        )
        if decision.status == "approval_required":
            approval_state = build_approval_state(
                tool_name=tool_name,
                permission_mode=decision.permission_mode,
                risk=decision.risk,
                write_scope=decision.write_scope,
                reason=decision.reason,
                tool_args=request.tool_call.get("args", {}),
            )
            audit_logger.log_event(
                thread_id="tool",
                event="approval_requested",
                event_family="runtime",
                status="pending",
                tool=tool_name,
                permission=decision.permission_mode,
                approval_required=True,
                risk=decision.risk,
                contract=decision.contract,
                payload=approval_state,
            )
            return Command(
                update={
                    "approval_state": approval_state,
                    "messages": [tool_message],
                }
            )
        return tool_message

    result = execute(request)
    duration_ms = int((time.monotonic() - started) * 1000)
    audit_logger.log_event(
        thread_id="tool",
        event="tool_permission_result",
        event_family="tool",
        status="ok",
        tool=tool_name,
        permission=decision.permission_mode,
        approval_required=decision.approval_required,
        risk=decision.risk,
        duration_ms=duration_ms,
        contract=decision.contract,
        payload={
            "write_scope": decision.write_scope,
        },
    )

    approval_update = None
    state = request.state if isinstance(request.state, dict) else {}
    if (
        (state.get("approval_state") or {}).get("status") == "pending"
        and (state.get("approval_state") or {}).get("tool_name") == tool_name
    ):
        approval_update = clear_approval_state()

    if approval_update is not None and isinstance(result, Command):
        return merge_command_update(result, {"approval_state": approval_update})
    if approval_update is not None and isinstance(result, ToolMessage):
        return Command(update={"approval_state": approval_update, "messages": [result]})
    return result


class PermissionGatedTool(BaseTool):
    name: str
    description: str
    args_schema: Type[BaseModel]
    inner_tool: BaseTool = Field(exclude=True)

    def _run(self, **kwargs: Any) -> Any:
        contract = get_tool_contract(self.inner_tool)
        started = time.monotonic()
        decision = evaluate_tool_permission(tool_name=self.name, contract=contract)
        audit_logger.log_event(
            thread_id="tool",
            event="tool_permission",
            event_family="tool",
            status=decision.status,
            tool=self.name,
            permission=decision.permission_mode,
            approval_required=decision.approval_required,
            risk=decision.risk,
            contract=decision.contract,
            payload={
                "reason": decision.reason,
                "write_scope": decision.write_scope,
            },
        )
        if not decision.allowed:
            audit_logger.log_event(
                thread_id="tool",
                event="tool_blocked",
                event_family="tool",
                status=decision.status,
                tool=self.name,
                permission=decision.permission_mode,
                approval_required=decision.approval_required,
                risk=decision.risk,
                contract=decision.contract,
                error=decision.reason,
                payload={
                    "reason": decision.reason,
                    "write_scope": decision.write_scope,
                    "args": kwargs,
                },
            )
            return build_permission_denied_message(decision)

        try:
            result = self.inner_tool.invoke(kwargs)
            return result
        except Exception as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            audit_logger.log_event(
                thread_id="tool",
                event="tool_permission_result",
                event_family="tool",
                status="error",
                tool=self.name,
                permission=decision.permission_mode,
                approval_required=decision.approval_required,
                risk=decision.risk,
                duration_ms=duration_ms,
                contract=decision.contract,
                error=str(exc),
                payload={
                    "write_scope": decision.write_scope,
                },
            )
            raise
        finally:
            if "result" in locals():
                duration_ms = int((time.monotonic() - started) * 1000)
                audit_logger.log_event(
                    thread_id="tool",
                    event="tool_permission_result",
                    event_family="tool",
                    status="ok",
                    tool=self.name,
                    permission=decision.permission_mode,
                    approval_required=decision.approval_required,
                    risk=decision.risk,
                    duration_ms=duration_ms,
                    contract=decision.contract,
                    payload={
                        "write_scope": decision.write_scope,
                    },
                )


def build_permission_gated_tools(tools: list[BaseTool]) -> list[BaseTool]:
    gated_tools: list[BaseTool] = []
    for tool_obj in tools:
        gated_tools.append(
            PermissionGatedTool(
                name=tool_obj.name,
                description=tool_obj.description,
                args_schema=tool_obj.args_schema,
                inner_tool=tool_obj,
                metadata=dict(getattr(tool_obj, "metadata", {}) or {}),
            )
        )
    return gated_tools
