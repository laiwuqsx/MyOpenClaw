from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.types import Command


PLAN_STATUSES = {"pending", "in_progress", "completed"}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_plan_items(items: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    in_progress_count = 0
    for raw_item in items or []:
        step = str((raw_item or {}).get("step", "")).strip()
        status = str((raw_item or {}).get("status", "pending")).strip().lower()
        if not step:
            raise ValueError("Each plan item must include a non-empty step.")
        if status not in PLAN_STATUSES:
            raise ValueError(
                "Invalid plan status. Use one of: pending, in_progress, completed."
            )
        if status == "in_progress":
            in_progress_count += 1
        normalized.append({"step": step, "status": status})

    if in_progress_count > 1:
        raise ValueError("Only one plan item may be marked in_progress.")
    return normalized


def build_plan_state(
    items: list[dict[str, Any]] | None,
    explanation: str = "",
) -> dict[str, Any]:
    return {
        "items": normalize_plan_items(items),
        "explanation": (explanation or "").strip(),
        "updated_at": utc_timestamp(),
    }


def format_plan_state_for_prompt(plan_state: dict[str, Any] | None) -> str:
    if not plan_state:
        return ""

    items = plan_state.get("items") or []
    explanation = str(plan_state.get("explanation", "") or "").strip()
    if not items and not explanation:
        return ""

    lines: list[str] = []
    if explanation:
        lines.append(f"Explanation: {explanation}")
    for index, item in enumerate(items, start=1):
        lines.append(f"{index}. [{item.get('status', 'pending')}] {item.get('step', '')}")
    return "\n".join(lines).strip()


def build_approval_state(
    *,
    tool_name: str,
    permission_mode: str,
    risk: str,
    write_scope: str,
    reason: str,
    tool_args: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": "pending",
        "tool_name": tool_name,
        "permission_mode": permission_mode,
        "risk": risk,
        "write_scope": write_scope,
        "reason": reason,
        "tool_args": dict(tool_args or {}),
        "requested_at": utc_timestamp(),
    }


def clear_approval_state() -> dict[str, Any]:
    return {}


def format_approval_state_for_prompt(approval_state: dict[str, Any] | None) -> str:
    if not approval_state or approval_state.get("status") != "pending":
        return ""

    lines = [
        f"Tool: {approval_state.get('tool_name', '')}",
        f"Permission: {approval_state.get('permission_mode', '')}",
        f"Risk: {approval_state.get('risk', '')}",
        f"Write Scope: {approval_state.get('write_scope', '')}",
        f"Reason: {approval_state.get('reason', '')}",
    ]
    return "\n".join(lines)


def merge_command_update(command: Command, extra_update: dict[str, Any]) -> Command:
    merged = dict(command.update or {})
    merged.update(extra_update)
    return Command(
        graph=command.graph,
        update=merged,
        resume=command.resume,
        goto=command.goto,
    )
