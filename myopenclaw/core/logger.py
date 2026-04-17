import atexit
import json
import os
import queue
import threading
from datetime import datetime, timezone

from .config import LOG_DIR


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

    def log_event(self, thread_id: str, event: str, **kwargs) -> None:
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.log_queue.put(
            {
                "ts": now_utc,
                "thread_id": thread_id,
                "event": event,
                **kwargs,
            }
        )

    def shutdown(self) -> None:
        self.log_queue.put(None)
        self.log_queue.join()


audit_logger = JSONLEventLogger()
