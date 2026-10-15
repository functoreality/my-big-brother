import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from my_big_brother.sources import ANALYSIS_MARKER
from my_big_brother.sources import bash, codex, opencode


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.start = datetime(2026, 6, 20, tzinfo=timezone.utc)
        self.end = self.start + timedelta(days=1)

    def write_events(self, filename, events):
        path = self.root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
        return path

    def response(self, role, content, identifier=None, phase=None, timestamp=None):
        return {"timestamp": timestamp or self.start.isoformat(), "type": "response_item",
            "payload": {"type": "message", "role": role, "phase": phase, "id": identifier,
                "content": [{"type": "input_text", "text": content}]}}

    def test_codex_current_ids_deduplicate_and_keep_only_final(self):
        self.write_events("session.jsonl", [
            {"type": "session_meta", "payload": {"source": "cli", "thread_source": "user"}},
            self.response("user", "Investigate failing migration", "u1"),
            {"timestamp": self.start.isoformat(), "type": "event_msg", "payload": {
                "type": "item_completed", "item": {"type": "UserMessage", "id": "u1",
                    "content": [{"type": "text", "text": "Investigate failing migration"}]}}},
            self.response("assistant", "Working", "c1", "commentary"),
            self.response("developer", "private setup", "d1"),
            self.response("assistant", "Fixed the migration", "a1", "final_answer"),
            {"timestamp": self.start.isoformat(), "type": "event_msg", "payload": {
                "type": "item_completed", "item": {"type": "AgentMessage", "id": "a1",
                    "phase": "final_answer", "content": [{"type": "text", "text": "Fixed the migration"}]}}},
        ])
        result = codex.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual([(r["role"], r["content"]) for r in result.rows], [
            ("user", "Investigate failing migration"), ("assistant_final", "Fixed the migration")])
        self.assertTrue(all(r["event_ordinal"] for r in result.rows))

    def test_codex_legacy_mirrors_preserve_repeated_requests(self):
        events = []
        for seconds in (0, 2):
            timestamp = (self.start + timedelta(seconds=seconds)).isoformat()
            events.extend([
                {"timestamp": timestamp, "type": "event_msg", "payload": {
                    "type": "user_message", "message": "Run again"}},
                self.response("user", "Run again", timestamp=timestamp),
            ])
        events.append({"timestamp": self.start.isoformat(), "type": "event_msg",
            "payload": {"type": "agent_message", "message": "Done"}})
        self.write_events("legacy.jsonl", events)
        rows = codex.collect(self.root, self.start, self.end).rows
        self.assertEqual(len([r for r in rows if r["role"] == "user"]), 2)
        self.assertEqual(len([r for r in rows if r["role"] == "assistant_final"]), 1)

    def test_codex_mirrors_with_distinct_ids_preserve_repeated_requests(self):
        events = []
        for number, seconds in enumerate((0, 2)):
            timestamp = (self.start + timedelta(seconds=seconds)).isoformat()
            events.extend([
                self.response("user", "Run again", f"msg-{number}", timestamp=timestamp),
                {"timestamp": timestamp, "type": "event_msg", "payload": {
                    "type": "item_completed", "item": {"type": "UserMessage",
                        "id": f"item-{number}", "content": [{"type": "text", "text": "Run again"}]}}},
            ])
        self.write_events("distinct-mirrors.jsonl", events)
        rows = codex.collect(self.root, self.start, self.end).rows
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["message_id"] for row in rows], ["msg-0", "msg-1"])

    def test_codex_same_id_mirror_does_not_hide_next_event_request(self):
        events = [self.response("user", "Run again", "first")]
        for identifier, seconds in (("first", 0), ("second", 2)):
            events.append({"timestamp": (self.start + timedelta(seconds=seconds)).isoformat(),
                "type": "event_msg", "payload": {"type": "item_completed", "item": {
                    "type": "UserMessage", "id": identifier,
                    "content": [{"type": "text", "text": "Run again"}]}}})
        self.write_events("same-id-mirror.jsonl", events)
        rows = codex.collect(self.root, self.start, self.end).rows
        self.assertEqual([row["message_id"] for row in rows], ["first", "second"])

    def test_codex_injected_context_metadata_is_not_user_activity(self):
        events = []
        for kinds in (["environments.environment_context"],
                      ["agents_md.instructions", "environments.environment_context"]):
            event = self.response("user", "Host context")
            event["payload"]["internal_chat_message_metadata_passthrough"] = {
                "content_item_kinds": kinds}
            events.append(event)
        event = self.response("user", "Host context", "actual-user")
        event["payload"]["internal_chat_message_metadata_passthrough"] = {
            "content_item_kinds": ["user.text"]}
        events.append(event)
        self.write_events("host-context.jsonl", events)
        rows = codex.collect(self.root, self.start, self.end).rows
        self.assertEqual([row["message_id"] for row in rows], ["actual-user"])

    def test_codex_unknown_or_mixed_metadata_preserves_user_text(self):
        events = []
        for number, kinds in enumerate(([], ["future.kind"],
                                       ["environments.environment_context", "user.text"],
                                       {"unexpected": "shape"})):
            event = self.response("user", f"Request {number}")
            event["payload"]["internal_chat_message_metadata_passthrough"] = {
                "content_item_kinds": kinds}
            events.append(event)
        self.write_events("unknown-metadata.jsonl", events)
        self.assertEqual(len(codex.collect(self.root, self.start, self.end).rows), 4)

    def test_codex_window_boundary_and_partial_line(self):
        path = self.write_events("session.jsonl", [
            self.response("user", "Before", timestamp=(self.start - timedelta(seconds=1)).isoformat()),
            self.response("user", "Inside"),
            self.response("user", "End", timestamp=self.end.isoformat()),
        ])
        with path.open("a") as handle:
            handle.write('{"incomplete":')
        result = codex.collect(self.root, self.start, self.end)
        self.assertEqual([row["content"] for row in result.rows], ["Inside"])
        self.assertEqual(result.status, "partial")

    def test_codex_missing_phase_reports_gap_instead_of_inventing_final(self):
        unmarked = self.response("assistant", "Ambiguous")
        terminal = self.response("assistant", "Explicit terminal")
        terminal["payload"]["end_turn"] = True
        self.write_events("session.jsonl", [unmarked, terminal])
        result = codex.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "partial")
        self.assertEqual([row["content"] for row in result.rows], ["Explicit terminal"])

    def test_codex_malformed_event_shapes_do_not_crash(self):
        self.write_events("session.jsonl", [
            [], {"timestamp": self.start.isoformat(), "type": "event_msg", "payload": []},
            {"timestamp": self.start.isoformat(), "type": "event_msg", "payload": {"item": []}},
            {"timestamp": self.start.isoformat(), "type": "event_msg", "payload": {
                "item": {"type": "AgentMessage", "phase": [], "content": "bad phase"}}},
            {"timestamp": self.start.isoformat(), "type": "response_item", "payload": {
                "type": "message", "role": "assistant", "phase": {}, "content": "bad phase"}},
            {"timestamp": self.start.isoformat(), "type": "response_item", "payload": {
                "type": "message", "role": "user", "content": [{"type": [], "text": "bad text type"}]}},
            {"timestamp": self.start.isoformat(), "type": "event_msg", "payload": {
                "item": {"type": "UserMessage", "id": {}, "content": [{"type": "text", "text": "Valid"}]}}},
        ])
        result = codex.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "partial")
        self.assertEqual([row["content"] for row in result.rows], ["Valid"])

    def test_codex_child_and_own_analyzer_excluded_even_marker_outside_window(self):
        for name, metadata in [
            ("child", {"thread_source": "subagent"}),
            ("guardian", {"source": {"subagent": {"other": "guardian"}}}),
        ]:
            self.write_events(name + ".jsonl", [
                {"type": "session_meta", "payload": metadata}, self.response("user", "Child work")])
        self.write_events("analysis.jsonl", [
            self.response("user", ANALYSIS_MARKER + "\nReview", timestamp=(self.start - timedelta(seconds=1)).isoformat()),
            self.response("assistant", "Report", phase="final_answer")])
        self.write_events("exec.jsonl", [
            {"type": "session_meta", "payload": {"source": "exec"}}, self.response("user", "User batch work")])
        result = codex.collect(self.root, self.start, self.end)
        self.assertEqual([row["content"] for row in result.rows], ["User batch work"])

    def create_database(self, filename=None, part_created=True):
        if filename is None:
            filename = "data # space.db" if os.name == "nt" else "data # space?.db"
        path = self.root / filename
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE session (id TEXT PRIMARY KEY, parent_id TEXT)")
        connection.execute("CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER, data TEXT)")
        time_column = ", time_created INTEGER" if part_created else ""
        connection.execute(f"CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT, data TEXT{time_column})")
        connection.executemany("INSERT INTO session VALUES (?, ?)", [("top", None), ("child", "top"), ("analysis", None)])
        return path, connection

    def add_message(self, connection, identifier, role, parts, session="top", finish=None, milliseconds=None):
        milliseconds = milliseconds if milliseconds is not None else int(self.start.timestamp() * 1000)
        connection.execute("INSERT INTO message VALUES (?, ?, ?, ?)",
            (identifier, session, milliseconds, json.dumps({"role": role, "finish": finish})))
        columns = {row[1] for row in connection.execute("PRAGMA table_info(part)")}
        for part_id, part_data, order in parts:
            values = [part_id, identifier, json.dumps(part_data)]
            if "time_created" in columns:
                values.append(order)
            connection.execute("INSERT INTO part VALUES (" + ",".join("?" for _ in values) + ")", values)

    def test_opencode_readonly_uri_parts_final_and_children(self):
        path, connection = self.create_database()
        self.add_message(connection, "user", "user", [
            ("z", {"type": "text", "text": "First"}, 1),
            ("a", {"type": "text", "text": "Second"}, 2),
            ("tool", {"type": "tool", "text": "Not evidence"}, 3)])
        self.add_message(connection, "final", "assistant", [("finalp", {"type": "text", "text": "Done"}, 1)], finish="stop")
        self.add_message(connection, "interim", "assistant", [("ip", {"type": "text", "text": "Thinking"}, 1)], finish="tool-calls")
        self.add_message(connection, "child", "user", [("cp", {"type": "text", "text": "Child"}, 1)], session="child")
        connection.commit()
        connection.close()
        before = path.read_bytes()
        result = opencode.collect(path, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual({r["content"] for r in result.rows}, {"First\nSecond", "Done"})
        self.assertEqual(before, path.read_bytes())

    def test_opencode_excludes_marked_sessions_and_system_synthetic_messages(self):
        path, connection = self.create_database(part_created=False)
        self.add_message(connection, "marker", "user", [("markerpart", {"type": "text", "text": ANALYSIS_MARKER}, 1)],
            session="analysis", milliseconds=int(self.start.timestamp() * 1000) - 1)
        self.add_message(connection, "report", "assistant", [("reportpart", {"type": "text", "text": "Report"}, 1)], session="analysis", finish="stop")
        self.add_message(connection, "system", "user", [("sp", {"type": "text", "text": "<system-reminder>setup"}, 1)])
        self.add_message(connection, "prefix", "user", [("pp", {"type": "text", "text": "[search-mode]\nMAXIMIZE SEARCH EFFORT.\n---\n\nFind migration bug"}, 1)])
        connection.commit()
        connection.close()
        self.assertEqual([r["content"] for r in opencode.collect(path, self.start, self.end).rows], ["Find migration bug"])

    def test_opencode_corrupt_records_partial_and_schema_mismatch_unavailable(self):
        path, connection = self.create_database()
        self.add_message(connection, "good", "user", [("goodp", {"type": "text", "text": "Work"}, 1)])
        connection.execute("INSERT INTO part VALUES (?, ?, ?, ?)", ("badp", "good", "{broken", 2))
        connection.commit()
        connection.close()
        result = opencode.collect(path, self.start, self.end)
        self.assertEqual(result.status, "partial")
        self.assertEqual([r["content"] for r in result.rows], ["Work"])
        empty = self.root / "empty.db"
        sqlite3.connect(empty).close()
        self.assertEqual(opencode.collect(empty, self.start, self.end).status, "unavailable")

    def test_missing_sources_do_not_create_originals(self):
        missing = self.root / "missing"
        for adapter in (codex, opencode, bash):
            self.assertEqual(adapter.collect(missing, self.start, self.end).status, "unavailable")
        self.assertFalse(missing.exists())

    def test_bash_old_session_directory_keeps_later_commands(self):
        earlier = self.start - timedelta(days=3)
        folder = earlier.astimezone().date().isoformat()
        path = self.write_events(f"{folder}/bash/persistent-session.jsonl", [
            {"event": "session_start", "started_at": earlier.isoformat()},
            {"event": "command", "command": "historical command",
             "completed_at": (earlier + timedelta(hours=1)).isoformat()},
            {"event": "command", "command": "current command",
             "completed_at": (self.start + timedelta(hours=1)).isoformat()},
            {"event": "session_end", "ended_at": self.end.isoformat()},
        ])
        original = path.read_bytes()
        result = bash.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual([row["content"] for row in result.rows], ["current command"])
        self.assertEqual(result.rows[0]["session_context_status"], "outside_window")
        self.assertEqual(result.rows[0]["session_context"]["started_at"], earlier.isoformat())
        self.assertEqual(path.read_bytes(), original)

    def test_bash_date_first_logical_window_and_incomplete_line(self):
        start = self.start + timedelta(hours=4)
        end = start + timedelta(days=1)
        first_day = start.astimezone().date().isoformat()
        last_day = (end - timedelta(seconds=1)).astimezone().date().isoformat()
        first = self.write_events(f"{first_day}/bash/first-session.jsonl", [
            {"event": [], "completed_at": start.isoformat()},
            {"event": "command", "command": "too early", "completed_at": self.start.isoformat()},
            {"event": "command", "command": "make test", "completed_at": start.isoformat(), "exit_status": 0},
        ])
        self.write_events(f"{last_day}/bash/last-session.jsonl", [
            {"event": "command", "command": "git status", "completed_at": (end - timedelta(seconds=1)).isoformat()},
            {"event": "command", "command": "too late", "completed_at": end.isoformat()},
        ])
        with first.open("a") as handle:
            handle.write('{"event":')
        result = bash.collect(self.root, start, end)
        self.assertEqual(result.status, "partial")
        self.assertEqual([r["content"] for r in result.rows], ["make test", "git status"])
        self.assertTrue(all(r["event_ordinal"] > 0 for r in result.rows))


if __name__ == "__main__":
    unittest.main()
