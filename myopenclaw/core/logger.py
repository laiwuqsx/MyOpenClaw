import atexit
import json
import os
import queue
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from .config import LOG_DIR


AUDIT_SCHEMA_VERSION = "myopenclaw.audit.v1"
_AUDIT_CONTEXT: ContextVar[dict[str, Any]] = ContextVar(
    "myopenclaw_audit_context",
    default={},
)
_EVENT_FAMILY_BY_PREFIX = {
    "llm_": "llm",
    "tool_": "tool",
    "shell_": "tool",
    "ai_": "assistant",
}
_KNOWN_EVENT_FIELDS = {
    "session_id",
    "session_mode",
    "provider",
    "model",
    "event_family",
    "status",
    "tool",
    "duration_ms",
    "error",
    "risk",
    "permission",
    "approval_required",
    "contract",
}


def set_audit_context(**values: Any) -> None:
    current = dict(_AUDIT_CONTEXT.get())
    current.update({key: value for key, value in values.items() if value is not None})
    _AUDIT_CONTEXT.set(current)


def clear_audit_context() -> None:
    _AUDIT_CONTEXT.set({})


def get_audit_context() -> dict[str, Any]:
    return dict(_AUDIT_CONTEXT.get())


def infer_event_family(event: str) -> str:
    for prefix, family in _EVENT_FAMILY_BY_PREFIX.items():
        if event.startswith(prefix):
            return family
    return "runtime"


def infer_event_status(event: str) -> str:
    if event.endswith("_blocked"):
        return "blocked"
    if event.endswith("_timeout"):
        return "timeout"
    if event.endswith("_error"):
        return "error"
    return "ok"


def build_audit_event(thread_id: str | None, event: str, **kwargs: Any) -> dict[str, Any]:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    context = get_audit_context()
    event_fields = {key: kwargs.pop(key) for key in list(kwargs) if key in _KNOWN_EVENT_FIELDS}

    payload = kwargs.pop("payload", {})
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        payload = {"value": payload}
    payload = dict(payload)
    payload.update(kwargs)

    normalized = {
        "ts": now_utc,
        "schema_version": AUDIT_SCHEMA_VERSION,
        "thread_id": thread_id or context.get("thread_id") or "system",
        "session_id": event_fields.get("session_id") or context.get("session_id") or "",
        "session_mode": event_fields.get("session_mode") or context.get("session_mode") or "",
        "provider": event_fields.get("provider") or context.get("provider") or "",
        "model": event_fields.get("model") or context.get("model") or "",
        "event": event,
        "event_family": event_fields.get("event_family") or infer_event_family(event),
        "status": event_fields.get("status") or infer_event_status(event),
        "tool": event_fields.get("tool") or "",
        "duration_ms": event_fields.get("duration_ms"),
        "error": event_fields.get("error"),
        "risk": event_fields.get("risk") or "",
        "permission": event_fields.get("permission") or "",
        "approval_required": bool(event_fields.get("approval_required", False)),
        "contract": event_fields.get("contract") or {},
        "payload": payload,
    }
    return normalized


class JSONLEventLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, log_dir: str = LOG_DIR):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_logger(log_dir)
            return cls._instance

    def _init_logger(self, log_dir: str) -> None:
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_queue: queue.Queue[dict | None] = queue.Queue()
        self.worker_thread = threading.Thread(target=self._write_loop, daemon=True)
        self.worker_thread.start()
        atexit.register(self.shutdown)

    def _write_loop(self) -> None:
        while True:
            log_item = self.log_queue.get()
            if log_item is None:
                self.log_queue.task_done()
                break

            try:
                thread_id = log_item.get("thread_id", "system")
                safe_id = "".join(c for c in thread_id if c.isalnum() or c in "-_") or "default"
                file_path = os.path.join(self.log_dir, f"{safe_id}.jsonl")
                with open(file_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(log_item, ensure_ascii=False) + "\n")
            finally:
                self.log_queue.task_done()

    def log_event(self, thread_id: str | None = None, event: str = "", **kwargs: Any) -> None:
        self.log_queue.put(build_audit_event(thread_id=thread_id, event=event, **kwargs))

    def shutdown(self) -> None:
        self.log_queue.put(None)
        self.log_queue.join()


audit_logger = JSONLEventLogger()
