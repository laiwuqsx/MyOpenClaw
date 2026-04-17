from dataclasses import dataclass

from .config import WORKSPACE_DIR


@dataclass(frozen=True)
class SessionContext:
    session_id: str
    session_mode: str
    thread_id: str
    workspace_dir: str
    provider_name: str
    model_name: str


def build_session_context(config: dict | None, provider_name: str, model_name: str) -> SessionContext:
    config = config or {}
    configurable = config.get("configurable", {})
    thread_id = configurable.get("thread_id", "system_default")
    session_mode = configurable.get("session_mode", "main")
    session_id = configurable.get("session_id", thread_id)
    return SessionContext(
        session_id=session_id,
        session_mode=session_mode,
        thread_id=thread_id,
        workspace_dir=WORKSPACE_DIR,
        provider_name=provider_name,
        model_name=model_name,
    )
