import json
import os
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import LOG_DIR


@dataclass(frozen=True)
class AuditEvent:
    ts: str
    thread_id: str
    event: str
    event_family: str = ""
    status: str = ""
    tool: str = ""
    duration_ms: int | None = None
    error: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    source_file: str = ""


@dataclass(frozen=True)
class MonitorSnapshot:
    events: list[AuditEvent]
    total_events: int
    parse_errors: int
    thread_counts: dict[str, int]
    event_counts: dict[str, int]
    latest_timestamp: str


ANOMALY_EVENTS = {
    "tool_blocked": "blocked",
    "shell_blocked": "blocked",
    "shell_error": "error",
    "shell_timeout": "timeout",
}


def _snapshot_signature(snapshot: MonitorSnapshot) -> tuple:
    last_event = snapshot.events[-1] if snapshot.events else None
    return (
        snapshot.total_events,
        snapshot.parse_errors,
        snapshot.latest_timestamp,
        tuple(sorted(snapshot.thread_counts.items())),
        tuple(sorted(snapshot.event_counts.items())),
        (
            last_event.ts,
            last_event.thread_id,
            last_event.event,
            tuple(sorted(last_event.payload.items())),
        )
        if last_event
        else None,
    )


def _event_sort_key(event: AuditEvent) -> tuple[str, str, str]:
    return (event.ts or "", event.thread_id or "", event.event or "")


def load_audit_events(
    log_dir: str = LOG_DIR,
    limit: int = 200,
    thread_id: str | None = None,
    event_type: str | None = None,
) -> MonitorSnapshot:
    parsed_events: list[AuditEvent] = []
    parse_errors = 0

    if not os.path.isdir(log_dir):
        return MonitorSnapshot(
            events=[],
            total_events=0,
            parse_errors=0,
            thread_counts={},
            event_counts={},
            latest_timestamp="",
        )

    for name in sorted(os.listdir(log_dir)):
        if not name.endswith(".jsonl"):
            continue
        path = os.path.join(log_dir, name)
        if not os.path.isfile(path):
            continue

        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    parse_errors += 1
                    continue

                current_thread_id = str(raw.get("thread_id", "system"))
                current_event_type = str(raw.get("event", "unknown"))
                if thread_id and current_thread_id != thread_id:
                    continue
                if event_type and current_event_type != event_type:
                    continue

                payload = raw.get("payload", {})
                if not isinstance(payload, dict):
                    payload = {}
                payload = dict(payload)
                for key in {
                    "schema_version",
                    "session_id",
                    "session_mode",
                    "provider",
                    "model",
                    "tool",
                    "duration_ms",
                    "error",
                    "risk",
                    "permission",
                    "approval_required",
                    "contract",
                    "status",
                }:
                    if key in raw and key not in payload:
                        payload[key] = raw[key]
                for key, value in raw.items():
                    if key not in {"ts", "thread_id", "event", "payload", "event_family"} and key not in payload:
                        payload[key] = value
                parsed_events.append(
                    AuditEvent(
                        ts=str(raw.get("ts", "")),
                        thread_id=current_thread_id,
                        event=current_event_type,
                        event_family=str(raw.get("event_family", "")),
                        status=str(raw.get("status", "")),
                        tool=str(raw.get("tool", "")),
                        duration_ms=raw.get("duration_ms"),
                        error=raw.get("error"),
                        payload=payload,
                        source_file=name,
                    )
                )

    parsed_events.sort(key=_event_sort_key)
    total_events = len(parsed_events)
    if limit > 0:
        parsed_events = parsed_events[-limit:]

    thread_counts = Counter(event.thread_id for event in parsed_events)
    event_counts = Counter(event.event for event in parsed_events)
    latest_timestamp = parsed_events[-1].ts if parsed_events else ""
    return MonitorSnapshot(
        events=parsed_events,
        total_events=total_events,
        parse_errors=parse_errors,
        thread_counts=dict(thread_counts),
        event_counts=dict(event_counts),
        latest_timestamp=latest_timestamp,
    )


def _format_payload_value(value: Any) -> str:
    if isinstance(value, dict):
        items = list(value.items())[:3]
        rendered = ", ".join(f"{key}={val}" for key, val in items)
        return "{" + rendered + ("..." if len(value) > 3 else "") + "}"
    if isinstance(value, list):
        preview = ", ".join(str(item) for item in value[:3])
        return "[" + preview + (", ..." if len(value) > 3 else "") + "]"
    return str(value)


def _event_style(event: AuditEvent) -> str:
    if event.event in {"shell_error", "shell_timeout"}:
        return "bold red"
    if event.event == "shell_blocked":
        return "bold yellow"
    if event.event == "tool_call":
        return "cyan"
    if event.event == "tool_result":
        return "green"
    if event.event == "ai_message":
        return "bright_white"
    return "white"


def _is_anomaly_event(event: AuditEvent) -> bool:
    if event.event in ANOMALY_EVENTS:
        return True
    if event.status == "error":
        return True
    if event.event == "shell_executed" and int(event.payload.get("exit_code", 0) or 0) != 0:
        return True
    return False


def _anomaly_label(event: AuditEvent) -> str:
    if event.event in ANOMALY_EVENTS:
        return ANOMALY_EVENTS[event.event]
    if event.event == "shell_executed" and int(event.payload.get("exit_code", 0) or 0) != 0:
        return "nonzero_exit"
    return ""


def summarize_event(event: AuditEvent) -> str:
    if event.event == "tool_call":
        tool_name = event.tool or event.payload.get("tool", "unknown")
        return f"tool={tool_name} args={_format_payload_value(event.payload.get('args', {}))}"
    if event.event == "tool_permission":
        tool_name = event.tool or event.payload.get("tool", "unknown")
        return (
            f"tool={tool_name} permission={event.payload.get('permission', '') or event.payload.get('permission_mode', '')} "
            f"status={event.status or event.payload.get('status', '')}"
        )
    if event.event == "tool_blocked":
        tool_name = event.tool or event.payload.get("tool", "unknown")
        return f"tool={tool_name} blocked={event.payload.get('reason', event.error or '')}"
    if event.event == "tool_result":
        tool_name = event.tool or event.payload.get("tool", "unknown")
        return f"tool={tool_name} result={str(event.payload.get('result_summary', ''))[:80]}"
    if event.event == "llm_input":
        return f"messages={event.payload.get('message_count', '?')}"
    if event.event == "ai_message":
        return str(event.payload.get("content", ""))[:100]
    if event.event.startswith("shell_"):
        command = event.payload.get("command", "")
        exit_code = event.payload.get("exit_code")
        if exit_code is None:
            return f"command={command}"
        return f"command={command} exit={exit_code}"

    if not event.payload:
        return ""
    items = list(event.payload.items())[:3]
    return " ".join(f"{key}={_format_payload_value(value)}" for key, value in items)


def build_dashboard_renderable(snapshot: MonitorSnapshot, log_dir: str = LOG_DIR):
    if snapshot.total_events == 0:
        return Panel(
            f"No audit events found in {log_dir}.\nStart `myopenclaw run` and keep this monitor open.",
            title="MYCLAW Monitor",
            border_style="yellow",
        )

    overview = Table.grid(expand=True)
    overview.add_column(justify="left")
    overview.add_column(justify="left")
    overview.add_column(justify="left")
    overview.add_row(
        f"Visible events: {len(snapshot.events)} / {snapshot.total_events}",
        f"Threads: {len(snapshot.thread_counts)}",
        f"Parse errors: {snapshot.parse_errors}",
    )
    overview.add_row(
        f"Latest ts: {snapshot.latest_timestamp or 'n/a'}",
        f"Top thread: {max(snapshot.thread_counts, key=snapshot.thread_counts.get)}" if snapshot.thread_counts else "Top thread: n/a",
        f"Top event: {max(snapshot.event_counts, key=snapshot.event_counts.get)}" if snapshot.event_counts else "Top event: n/a",
    )

    event_counts_table = Table(title="Event Counts", expand=True)
    event_counts_table.add_column("Event", style="cyan")
    event_counts_table.add_column("Count", justify="right", style="green")
    for event_name, count in sorted(snapshot.event_counts.items(), key=lambda item: (-item[1], item[0]))[:8]:
        event_counts_table.add_row(event_name, str(count))

    thread_counts_table = Table(title="Thread Counts", expand=True)
    thread_counts_table.add_column("Thread", style="magenta")
    thread_counts_table.add_column("Count", justify="right", style="green")
    for name, count in sorted(snapshot.thread_counts.items(), key=lambda item: (-item[1], item[0]))[:8]:
        thread_counts_table.add_row(name, str(count))

    recent_table = Table(title="Recent Events", expand=True)
    recent_table.add_column("Time", style="dim", width=20, no_wrap=True)
    recent_table.add_column("Thread", style="magenta", width=14)
    recent_table.add_column("Event", style="cyan", width=16)
    recent_table.add_column("Details", style="white")
    for event in reversed(snapshot.events[-15:]):
        recent_table.add_row(
            event.ts or "-",
            event.thread_id,
            event.event,
            summarize_event(event),
        )

    header = Panel(
        Group(
            Text("Live audit view for MYCLAW runtime events.", style="bold white"),
            Text("Press Ctrl+C to exit.", style="dim"),
            overview,
        ),
        title="MYCLAW Monitor",
        border_style="cyan",
    )

    return Group(
        header,
        Group(event_counts_table, thread_counts_table),
        recent_table,
    )


def build_thread_renderable(
    snapshot: MonitorSnapshot,
    thread_id: str,
    log_dir: str = LOG_DIR,
):
    if snapshot.total_events == 0:
        return Panel(
            f"No audit events found for thread `{thread_id}` in {log_dir}.",
            title="MYCLAW Thread View",
            border_style="yellow",
        )

    events = snapshot.events
    tool_calls = sum(1 for event in events if event.event == "tool_call")
    tool_results = sum(1 for event in events if event.event == "tool_result")
    ai_messages = sum(1 for event in events if event.event == "ai_message")
    anomalies = [event for event in events if _is_anomaly_event(event)]

    overview = Table.grid(expand=True)
    overview.add_column(justify="left")
    overview.add_column(justify="left")
    overview.add_column(justify="left")
    overview.add_row(
        f"Thread: {thread_id}",
        f"Visible events: {len(events)} / {snapshot.total_events}",
        f"Latest ts: {snapshot.latest_timestamp or 'n/a'}",
    )
    overview.add_row(
        f"Tool calls/results: {tool_calls}/{tool_results}",
        f"AI messages: {ai_messages}",
        f"Anomalies: {len(anomalies)}",
    )

    timeline_table = Table(title="Thread Timeline", expand=True)
    timeline_table.add_column("Time", style="dim", width=20, no_wrap=True)
    timeline_table.add_column("Event", width=16)
    timeline_table.add_column("Details", style="white")
    timeline_table.add_column("Source", style="dim", width=18)
    for event in reversed(events[-25:]):
        timeline_table.add_row(
            event.ts or "-",
            Text(event.event, style=_event_style(event)),
            summarize_event(event),
            event.source_file or "-",
        )

    chain_table = Table(title="Execution Chain", expand=True)
    chain_table.add_column("#", style="dim", width=4, justify="right")
    chain_table.add_column("Step", width=16)
    chain_table.add_column("Summary", style="white")
    for index, event in enumerate(events[-12:], start=max(1, len(events) - 11)):
        chain_table.add_row(
            str(index),
            Text(event.event, style=_event_style(event)),
            summarize_event(event),
        )

    if anomalies:
        anomaly_table = Table(title="Anomalies", expand=True)
        anomaly_table.add_column("Time", style="dim", width=20, no_wrap=True)
        anomaly_table.add_column("Type", width=14)
        anomaly_table.add_column("Details", style="white")
        for event in reversed(anomalies[-10:]):
            anomaly_table.add_row(
                event.ts or "-",
                Text(_anomaly_label(event) or event.event, style=_event_style(event)),
                summarize_event(event),
            )
    else:
        anomaly_table = Panel(
            "No anomalies in the visible window.",
            title="Anomalies",
            border_style="green",
        )

    header = Panel(
        Group(
            Text("Thread drill-down view for MYCLAW runtime events.", style="bold white"),
            Text("Use `--thread <id>` to inspect another execution chain.", style="dim"),
            overview,
        ),
        title="MYCLAW Thread View",
        border_style="cyan",
    )

    return Group(
        header,
        anomaly_table,
        chain_table,
        timeline_table,
    )


def build_replay_renderable(
    snapshot: MonitorSnapshot,
    thread_id: str,
    log_dir: str = LOG_DIR,
):
    if snapshot.total_events == 0:
        return Panel(
            f"No audit events found for replay thread `{thread_id}` in {log_dir}.",
            title="MYCLAW Replay",
            border_style="yellow",
        )

    events = snapshot.events
    overview = Table.grid(expand=True)
    overview.add_column(justify="left")
    overview.add_column(justify="left")
    overview.add_column(justify="left")
    overview.add_row(
        f"Thread: {thread_id}",
        f"Replay events: {len(events)} / {snapshot.total_events}",
        f"Latest ts: {snapshot.latest_timestamp or 'n/a'}",
    )
    overview.add_row(
        f"Tool calls: {sum(1 for event in events if event.event == 'tool_call')}",
        f"Tool results: {sum(1 for event in events if event.event == 'tool_result')}",
        f"AI messages: {sum(1 for event in events if event.event == 'ai_message')}",
    )

    replay_table = Table(title="Replay Timeline", expand=True)
    replay_table.add_column("#", style="dim", width=4, justify="right")
    replay_table.add_column("Time", style="dim", width=20, no_wrap=True)
    replay_table.add_column("Event", width=16)
    replay_table.add_column("Summary", style="white")
    replay_table.add_column("Source", style="dim", width=18)
    for index, event in enumerate(events, start=1):
        replay_table.add_row(
            str(index),
            event.ts or "-",
            Text(event.event, style=_event_style(event)),
            summarize_event(event),
            event.source_file or "-",
        )

    cycle_table = Table(title="Turn Cycles", expand=True)
    cycle_table.add_column("Cycle", style="dim", width=6, justify="right")
    cycle_table.add_column("LLM Input", width=10, justify="right")
    cycle_table.add_column("Tool Call", width=10, justify="right")
    cycle_table.add_column("Tool Result", width=11, justify="right")
    cycle_table.add_column("AI Message", width=10, justify="right")

    cycle_index = 0
    cycle_llm = cycle_tool_call = cycle_tool_result = cycle_ai = 0
    cycle_rows: list[tuple[str, str, str, str, str]] = []
    for event in events:
        if event.event == "llm_input":
            if cycle_index > 0:
                cycle_rows.append(
                    (
                        str(cycle_index),
                        str(cycle_llm),
                        str(cycle_tool_call),
                        str(cycle_tool_result),
                        str(cycle_ai),
                    )
                )
            cycle_index += 1
            cycle_llm = 1
            cycle_tool_call = 0
            cycle_tool_result = 0
            cycle_ai = 0
            continue
        if cycle_index == 0:
            cycle_index = 1
        if event.event == "tool_call":
            cycle_tool_call += 1
        elif event.event == "tool_result":
            cycle_tool_result += 1
        elif event.event == "ai_message":
            cycle_ai += 1

    if cycle_index > 0:
        cycle_rows.append(
            (
                str(cycle_index),
                str(cycle_llm),
                str(cycle_tool_call),
                str(cycle_tool_result),
                str(cycle_ai),
            )
        )

    for row in cycle_rows[-12:]:
        cycle_table.add_row(*row)

    anomaly_events = [event for event in events if _is_anomaly_event(event)]
    if anomaly_events:
        anomaly_panel = Table(title="Replay Anomalies", expand=True)
        anomaly_panel.add_column("Time", style="dim", width=20, no_wrap=True)
        anomaly_panel.add_column("Type", width=14)
        anomaly_panel.add_column("Summary", style="white")
        for event in anomaly_events[-12:]:
            anomaly_panel.add_row(
                event.ts or "-",
                Text(_anomaly_label(event) or event.event, style=_event_style(event)),
                summarize_event(event),
            )
    else:
        anomaly_panel = Panel(
            "No anomalies in the replay window.",
            title="Replay Anomalies",
            border_style="green",
        )

    header = Panel(
        Group(
            Text("Replay view for one MYCLAW thread.", style="bold white"),
            Text("This view preserves chronological order for post-run inspection.", style="dim"),
            overview,
        ),
        title="MYCLAW Replay",
        border_style="cyan",
    )

    return Group(
        header,
        cycle_table,
        anomaly_panel,
        replay_table,
    )


def build_monitor_renderable(
    snapshot: MonitorSnapshot,
    log_dir: str = LOG_DIR,
    thread_id: str | None = None,
    view_mode: str = "dashboard",
):
    if view_mode == "thread":
        target_thread = thread_id or (snapshot.events[-1].thread_id if snapshot.events else "unknown")
        return build_thread_renderable(snapshot, thread_id=target_thread, log_dir=log_dir)
    if view_mode == "replay":
        target_thread = thread_id or (snapshot.events[-1].thread_id if snapshot.events else "unknown")
        return build_replay_renderable(snapshot, thread_id=target_thread, log_dir=log_dir)
    return build_dashboard_renderable(snapshot, log_dir=log_dir)


def run_live_monitor(
    refresh_interval: float = 1.0,
    log_dir: str = LOG_DIR,
    limit: int = 200,
    thread_id: str | None = None,
    event_type: str | None = None,
    fullscreen: bool = False,
    view_mode: str = "dashboard",
):
    from rich.live import Live

    snapshot = load_audit_events(
        log_dir=log_dir,
        limit=limit,
        thread_id=thread_id,
        event_type=event_type,
    )
    previous_signature = _snapshot_signature(snapshot)

    with Live(
        build_monitor_renderable(
            snapshot,
            log_dir=log_dir,
            thread_id=thread_id,
            view_mode=view_mode,
        ),
        refresh_per_second=max(1, int(1 / refresh_interval)) if refresh_interval > 0 else 4,
        screen=fullscreen,
        vertical_overflow="visible",
        auto_refresh=False,
    ) as live:
        while True:
            snapshot = load_audit_events(
                log_dir=log_dir,
                limit=limit,
                thread_id=thread_id,
                event_type=event_type,
            )
            current_signature = _snapshot_signature(snapshot)
            if current_signature != previous_signature:
                live.update(
                    build_monitor_renderable(
                        snapshot,
                        log_dir=log_dir,
                        thread_id=thread_id,
                        view_mode=view_mode,
                    ),
                    refresh=True,
                )
                previous_signature = current_signature
            time.sleep(refresh_interval)
