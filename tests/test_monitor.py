import json
import os
import tempfile
import unittest

from rich.console import Console

from myopenclaw.core.monitor import build_monitor_renderable, load_audit_events, summarize_event


class TestMonitor(unittest.TestCase):
    def _write_jsonl(self, path: str, rows: list[dict]) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

    def test_load_audit_events_reads_and_limits_recent_events(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_jsonl(
                os.path.join(tmpdir, "local_main.jsonl"),
                [
                    {"ts": "2026-04-25T10:00:00Z", "thread_id": "local_main", "event": "llm_input", "message_count": 4},
                    {"ts": "2026-04-25T10:00:01Z", "thread_id": "local_main", "event": "tool_call", "tool": "calculator", "args": {"expression": "1+1"}},
                ],
            )
            self._write_jsonl(
                os.path.join(tmpdir, "tool.jsonl"),
                [
                    {"ts": "2026-04-25T10:00:02Z", "thread_id": "tool", "event": "shell_executed", "command": "ls", "exit_code": 0},
                ],
            )

            snapshot = load_audit_events(log_dir=tmpdir, limit=2)

        self.assertEqual(snapshot.total_events, 3)
        self.assertEqual(len(snapshot.events), 2)
        self.assertEqual(snapshot.latest_timestamp, "2026-04-25T10:00:02Z")
        self.assertEqual(snapshot.thread_counts["local_main"], 1)
        self.assertEqual(snapshot.thread_counts["tool"], 1)
        self.assertEqual(snapshot.event_counts["tool_call"], 1)
        self.assertEqual(snapshot.event_counts["shell_executed"], 1)

    def test_load_audit_events_filters_by_thread_and_event(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_jsonl(
                os.path.join(tmpdir, "mixed.jsonl"),
                [
                    {"ts": "2026-04-25T10:00:00Z", "thread_id": "local_main", "event": "llm_input", "message_count": 4},
                    {"ts": "2026-04-25T10:00:01Z", "thread_id": "local_main", "event": "tool_call", "tool": "calculator", "args": {"expression": "1+1"}},
                    {"ts": "2026-04-25T10:00:02Z", "thread_id": "tool", "event": "shell_executed", "command": "ls", "exit_code": 0},
                ],
            )

            snapshot = load_audit_events(
                log_dir=tmpdir,
                limit=50,
                thread_id="local_main",
                event_type="tool_call",
            )

        self.assertEqual(snapshot.total_events, 1)
        self.assertEqual(len(snapshot.events), 1)
        self.assertEqual(snapshot.events[0].event, "tool_call")
        self.assertEqual(snapshot.events[0].thread_id, "local_main")

    def test_build_monitor_renderable_contains_recent_event_details(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_jsonl(
                os.path.join(tmpdir, "local_main.jsonl"),
                [
                    {"ts": "2026-04-25T10:00:00Z", "thread_id": "local_main", "event": "ai_message", "content": "final answer"},
                ],
            )
            snapshot = load_audit_events(log_dir=tmpdir, limit=20)

            console = Console(record=True, width=120)
            console.print(build_monitor_renderable(snapshot, log_dir=tmpdir))
            rendered = console.export_text()

        self.assertIn("Recent Events", rendered)
        self.assertIn("ai_message", rendered)
        self.assertIn("final answer", rendered)

    def test_build_thread_renderable_contains_timeline_and_anomalies(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_jsonl(
                os.path.join(tmpdir, "local_main.jsonl"),
                [
                    {"ts": "2026-04-25T10:00:00Z", "thread_id": "local_main", "event": "llm_input", "message_count": 4},
                    {"ts": "2026-04-25T10:00:01Z", "thread_id": "local_main", "event": "tool_call", "tool": "execute_office_shell", "args": {"command": "ls"}},
                    {"ts": "2026-04-25T10:00:02Z", "thread_id": "local_main", "event": "tool_result", "tool": "execute_office_shell", "result_summary": "Exit Code: 0"},
                    {"ts": "2026-04-25T10:00:03Z", "thread_id": "local_main", "event": "shell_blocked", "command": "rm file.txt"},
                ],
            )
            snapshot = load_audit_events(log_dir=tmpdir, limit=20, thread_id="local_main")

            console = Console(record=True, width=140)
            console.print(
                build_monitor_renderable(
                    snapshot,
                    log_dir=tmpdir,
                    thread_id="local_main",
                    view_mode="thread",
                )
            )
            rendered = console.export_text()

        self.assertIn("Thread Timeline", rendered)
        self.assertIn("Execution Chain", rendered)
        self.assertIn("Anomalies", rendered)
        self.assertIn("shell_blocked", rendered)
        self.assertIn("blocked", rendered)

    def test_build_replay_renderable_contains_chronological_timeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_jsonl(
                os.path.join(tmpdir, "local_main.jsonl"),
                [
                    {"ts": "2026-04-25T10:00:00Z", "thread_id": "local_main", "event": "llm_input", "message_count": 4},
                    {"ts": "2026-04-25T10:00:01Z", "thread_id": "local_main", "event": "tool_call", "tool": "calculator", "args": {"expression": "1+1"}},
                    {"ts": "2026-04-25T10:00:02Z", "thread_id": "local_main", "event": "tool_result", "tool": "calculator", "result_summary": "2"},
                    {"ts": "2026-04-25T10:00:03Z", "thread_id": "local_main", "event": "ai_message", "content": "The answer is 2."},
                ],
            )
            snapshot = load_audit_events(log_dir=tmpdir, limit=20, thread_id="local_main")

            console = Console(record=True, width=140)
            console.print(
                build_monitor_renderable(
                    snapshot,
                    log_dir=tmpdir,
                    thread_id="local_main",
                    view_mode="replay",
                )
            )
            rendered = console.export_text()

        self.assertIn("Replay Timeline", rendered)
        self.assertIn("Turn Cycles", rendered)
        self.assertIn("The answer is 2.", rendered)
        self.assertIn("tool_call", rendered)

    def test_summarize_event_formats_known_event_types(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_jsonl(
                os.path.join(tmpdir, "local_main.jsonl"),
                [
                    {
                        "ts": "2026-04-25T10:00:00Z",
                        "schema_version": "myopenclaw.audit.v1",
                        "thread_id": "local_main",
                        "event": "tool_call",
                        "event_family": "tool",
                        "status": "requested",
                        "tool": "calculator",
                        "payload": {"args": {"expression": "1+1"}},
                    },
                ],
            )
            snapshot = load_audit_events(log_dir=tmpdir, limit=10)

        self.assertIn("tool=calculator", summarize_event(snapshot.events[0]))
        self.assertEqual(snapshot.events[0].status, "requested")


if __name__ == "__main__":
    unittest.main()
