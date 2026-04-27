import os

from rich.console import Console

from myopenclaw.core.config import LOG_DIR
from myopenclaw.core.monitor import build_monitor_renderable, load_audit_events, run_live_monitor


console = Console()


def _read_bool_env(name: str) -> bool:
    return os.getenv(name, "").lower() in {"1", "true", "yes", "on"}


def main(
    refresh_interval: float | None = None,
    limit: int | None = None,
    once: bool | None = None,
    fullscreen: bool | None = None,
    thread_id: str | None = None,
    event_type: str | None = None,
    view_mode: str | None = None,
) -> None:
    refresh_interval = refresh_interval if refresh_interval is not None else float(
        os.getenv("MYOPENCLAW_MONITOR_INTERVAL", "1.0")
    )
    limit = limit if limit is not None else int(os.getenv("MYOPENCLAW_MONITOR_LIMIT", "200"))
    once = once if once is not None else _read_bool_env("MYOPENCLAW_MONITOR_ONCE")
    fullscreen = (
        fullscreen if fullscreen is not None else _read_bool_env("MYOPENCLAW_MONITOR_FULLSCREEN")
    )
    thread_id = thread_id if thread_id is not None else (os.getenv("MYOPENCLAW_MONITOR_THREAD") or None)
    event_type = event_type if event_type is not None else (os.getenv("MYOPENCLAW_MONITOR_EVENT") or None)
    view_mode = view_mode if view_mode is not None else (os.getenv("MYOPENCLAW_MONITOR_VIEW") or "dashboard")

    if once:
        snapshot = load_audit_events(
            log_dir=LOG_DIR,
            limit=limit,
            thread_id=thread_id,
            event_type=event_type,
        )
        console.print(
            build_monitor_renderable(
                snapshot,
                log_dir=LOG_DIR,
                thread_id=thread_id,
                view_mode=view_mode,
            )
        )
        return

    try:
        run_live_monitor(
            refresh_interval=refresh_interval,
            log_dir=LOG_DIR,
            limit=limit,
            thread_id=thread_id,
            event_type=event_type,
            fullscreen=fullscreen,
            view_mode=view_mode,
        )
    except KeyboardInterrupt:
        console.print("\n[dim]Monitor stopped.[/dim]")


if __name__ == "__main__":
    main()
