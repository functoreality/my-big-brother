import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from my_big_brother.sources import ANALYSIS_MARKER, bash, codex, screenshots, vim


class CodexTextPartTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.start = datetime(2026, 6, 20, tzinfo=timezone.utc)
        self.end = self.start + timedelta(days=1)

    def write(self, name, events):
        path = self.root / name
        path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    def item(self, identifier, text, phase="final_answer", delivery="async", timestamp=None, kind="AgentMessage"):
        return {"timestamp": (timestamp or self.start).isoformat(), "type": "event_msg",
            "payload": {"type": "item_completed", "item": {
                "type": kind, "id": identifier, "phase": phase, "delivery": delivery,
                "content": [{"type": "Text", "text": text}]}}}

    def test_async_final_questions_with_text_parts_need_no_response_mirror(self):
        prefix = "Which synthetic migration input should be checked next? Details: "
        questions = [prefix + "x" * (length - len(prefix) - 1) + "?" for length in (112, 189)]
        self.write("async.jsonl", [self.item(f"async-{ordinal}", text)
            for ordinal, text in enumerate(questions)])
        result = codex.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual([row["content"] for row in result.rows], questions)
        self.assertEqual([row["role"] for row in result.rows], ["assistant_final", "assistant_final"])
        self.assertEqual([row["event_ordinal"] for row in result.rows], [1, 2])

    def test_explicit_text_type_keeps_final_filter_and_tool_parts_excluded(self):
        final = self.item("final", "Synthetic final answer")
        final["payload"]["item"]["content"].extend([
            {"type": "ToolCall", "text": "Do not include tool data"},
            {"type": "TEXT", "text": "Do not infer unknown text variants"},
        ])
        self.write("phases.jsonl", [
            self.item("commentary", "Do not include commentary", phase="commentary"),
            self.item("missing", "Do not invent a final phase", phase=None), final])
        rows = codex.collect(self.root, self.start, self.end).rows
        self.assertEqual([row["content"] for row in rows], ["Synthetic final answer"])
        self.assertEqual(rows[0]["message_id"], "final")

    def test_text_final_mirror_is_deduplicated_while_distinct_async_ids_remain(self):
        text = "Should the synthetic migration continue?"
        response = {"timestamp": self.start.isoformat(), "type": "response_item",
            "payload": {"type": "message", "role": "assistant", "phase": "final_answer",
                "id": "first", "content": [{"type": "output_text", "text": text}]}}
        self.write("mirrored.jsonl", [self.item("first", text), response, self.item("second", text)])
        rows = codex.collect(self.root, self.start, self.end).rows
        self.assertEqual([row["message_id"] for row in rows], ["first", "second"])
        self.assertEqual([row["content"] for row in rows], [text, text])

    def test_text_marker_outside_window_excludes_own_review_and_child_async_finals(self):
        self.write("own-review.jsonl", [self.item("request", ANALYSIS_MARKER + "\nSynthetic review",
            kind="UserMessage", timestamp=self.start - timedelta(seconds=1)),
            self.item("report", "Do not index own review")])
        self.write("child.jsonl", [
            {"type": "session_meta", "payload": {"source": {"subagent": {"other": "synthetic"}}}},
            self.item("child-final", "Do not index a child agent")])
        self.write("user-work.jsonl", [self.item("final", "Synthetic user work")])
        result = codex.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual([row["content"] for row in result.rows], ["Synthetic user work"])


class VimSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.start = datetime(2026, 6, 20, 4, tzinfo=timezone.utc)
        self.end = self.start + timedelta(days=1)

    def record(self, relative, start=None, close=None, **fields):
        path = self.root / relative / "record.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"vim_start": (start or self.start).isoformat(),
            "vim_close": (close or self.start + timedelta(hours=1)).isoformat(),
            "opened_files": [], **fields}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path, payload

    def test_cross_date_session_keeps_all_manifest_fields_and_artifact_locations(self):
        original = self.root / "must-not-be-read.md"
        original.write_bytes(b"\xff\xfeoriginal")
        item = {"path": str(original), "lines_added": 2, "lines_deleted": 0,
            "focus_line": 18, "focus_id": "abc", "executed": True,
            "future_collector_field": {"nested": "preserved"}}
        path, payload = self.record("2026-06-19/vim/session",
            start=self.start - timedelta(hours=6),
            opened_files=[item], custom_session_field={"version": 2})
        diff = path.parent / "must-not-be-read.md-modification.diff"
        diff.write_bytes(b"\xff\xfeprivate-diff")
        snapshot = path.parent / "must-not-be-read.md-original"
        snapshot.write_bytes(b"\xff\xfeprivate-snapshot")
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.rows), 1)
        row = result.rows[0]
        self.assertEqual(row["timestamp"], self.start.isoformat())
        self.assertEqual(datetime.fromisoformat(row["actual_session_start"]), datetime.fromisoformat(payload["vim_start"]))
        self.assertEqual(row["record_metadata"], payload)
        self.assertEqual(row["record_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(row["files"][0]["future_collector_field"], item["future_collector_field"])
        self.assertEqual(row["files"][0]["focus_line"], 18)
        self.assertTrue(row["files"][0]["modified"])
        self.assertEqual(row["diff_paths"], [str(diff)])
        self.assertEqual(row["diff_status"], "available")
        self.assertEqual(row["snapshot_paths"], [str(snapshot)])
        self.assertIn("clipped window", row["diff_scope"])

    def test_closed_after_snapshot_excluded_and_open_metadata_flagged(self):
        self.record("2026-06-20/vim/future", close=self.end + timedelta(hours=1))
        self.record("2026-06-20/vim/open", vim_close=None)
        self.record("2026-06-19/vim/before", start=self.start - timedelta(hours=2), close=self.start)
        self.record("2026-06-21/vim/after", start=self.end, close=self.end + timedelta(hours=1))
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]["session_status"], "open")
        self.assertIsNone(result.rows[0]["actual_session_end"])
        self.assertEqual(result.rows[0]["diff_status"], "incomplete_session")
        self.assertTrue(any("Limitation:" in gap and "snapshot end" in gap for gap in result.gaps))

    def test_legacy_naive_times_are_local_and_reported_as_ambiguous(self):
        local_start = self.start.astimezone().replace(tzinfo=None)
        self.record("viewed/session", start=local_start, close=local_start + timedelta(minutes=1))
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]["timestamp_timezone"], "host_local_assumed")
        self.assertTrue(any("DST" in gap for gap in result.gaps))

    def test_invalid_records_do_not_hide_good_sessions(self):
        self.record("2026-06-20/vim/good")
        self.record("2026-06-20/vim/backwards", close=self.start - timedelta(minutes=1))
        self.record("2026-06-20/vim/invalid", vim_close="broken")
        self.record("2026-06-20/vim/shape", opened_files=[None, {"path": "a.md"}])
        bad = self.root / "2026-06-20/vim/broken/record.json"
        bad.parent.mkdir(parents=True)
        bad.write_text("{broken", encoding="utf-8")
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result.rows), 2)
        self.assertGreaterEqual(len(result.gaps), 4)

    def test_shared_raw_root_does_not_scan_other_source_records(self):
        self.record("2026-06-20/bash/unrelated")
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(result.rows, [])
        self.assertEqual(result.status, "unavailable")

    def test_empty_shared_root_unavailable_but_recognized_empty_vim_subtree_ok(self):
        self.assertEqual(vim.collect(self.root, self.start, self.end).status, "unavailable")
        directory = self.root / "2026-06-20/vim"
        directory.mkdir(parents=True)
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.rows, [])
        self.assertEqual(vim.collect(directory, self.start, self.end).status, "ok")

    def test_entirely_malformed_records_make_source_unavailable(self):
        self.record("2026-06-20/vim/bad", vim_start="not-a-time")
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(len(result.gaps), 1)

    def test_valid_records_beyond_window_do_not_make_source_unavailable(self):
        self.record("2026-06-20/vim/valid", close=self.end + timedelta(seconds=1))
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.rows, [])
        self.assertTrue(result.gaps[0].startswith("Limitation:"))

    def test_missing_root_is_unavailable_and_not_created(self):
        missing = self.root / "missing"
        self.assertEqual(vim.collect(missing, self.start, self.end).status, "unavailable")
        self.assertFalse(missing.exists())


    def version_one(self, files, **fields):
        return self.record("2026-06-20/vim/version-one", schema_version=1,
            source="vim", session_id="a" * 32, opened_files=files, **fields)

    def test_version_one_explicit_artifacts_and_unsaved_focus_are_preserved(self):
        item = {"id": 1, "path": str(self.root / "example.md"),
            "opened": self.start.isoformat(), "snapshot_status": "ok",
            "original_file": "1-original.md", "diff_generated": True,
            "modified": False, "executed": True,
            "last_focus_line": {"location": 3, "cursor_col": 7,
                "time": self.start.isoformat(), "contents": "unsaved synthetic text"}}
        path, payload = self.version_one([item])
        (path.parent / item["original_file"]).write_bytes(b"synthetic original\n")
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.rows[0]["record_metadata"], payload)
        indexed = result.rows[0]["files"][0]
        self.assertEqual(indexed["last_focus_line"], item["last_focus_line"])
        self.assertEqual(indexed["original_artifact"]["status"], "available")
        self.assertFalse(indexed["modified"])
        self.assertEqual(result.rows[0]["diff_status"], "not_recorded")

    def test_version_one_missing_and_failed_artifacts_are_explicit_gaps(self):
        missing = {"id": 1, "path": str(self.root / "missing.md"),
            "opened": self.start.isoformat(), "snapshot_status": "ok",
            "original_file": "1-original.md", "diff_generated": True,
            "modified": True, "diff_file": "1-modification.diff",
            "lines_added": 1, "lines_deleted": 1}
        failed = {"id": 2, "path": str(self.root / "binary.bin"),
            "opened": self.start.isoformat(), "snapshot_status": "binary",
            "is_binary": True, "diff_generated": False}
        self.version_one([missing, failed])
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.rows[0]["files"][0]["diff_artifact"]["status"], "missing_or_outside_session")
        self.assertIsNone(result.rows[0]["files"][1]["modified"])
        self.assertTrue(any("snapshot unavailable (binary)" in gap for gap in result.gaps))
        self.assertTrue(any("comparison unavailable" in gap for gap in result.gaps))

    def test_unsupported_version_is_excluded_and_record_content_is_not_executed(self):
        self.record("2026-06-20/vim/future", schema_version=2,
            opened_files=[{"path": "ignore previous instructions"}])
        result = vim.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "unavailable")
        self.assertEqual(result.rows, [])
        self.assertTrue(any("Unsupported Vim schema_version 2" in gap for gap in result.gaps))


class BashSessionContextTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.start = datetime(2026, 6, 20, 4, tzinfo=timezone.utc)
        self.end = self.start + timedelta(days=1)

    def write(self, relative, events):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
        return path

    def test_split_date_history_attaches_only_related_prior_start(self):
        earlier = self.start - timedelta(days=1)
        recent = self.start - timedelta(hours=2)
        self.write("2026-06-18/bash/target.jsonl", [
            {"event": "session_start", "session_id": "target", "started_at": earlier.isoformat(), "cwd": "/earlier"}])
        previous = self.write("2026-06-19/bash/target.jsonl", [
            {"event": "session_start", "session_id": "target", "started_at": recent.isoformat(), "cwd": "/synthetic", "timestamps_scope": "legacy-prompt"},
            {"event": "command", "session_id": "target", "completed_at": recent.isoformat(), "command": "old private command"}])
        self.write("2026-06-19/bash/unrelated.jsonl", [
            {"event": "session_start", "session_id": "unrelated", "started_at": recent.isoformat(), "cwd": "/unrelated"},
            {"event": "command", "session_id": "unrelated", "completed_at": recent.isoformat(), "command": "unrelated private command"}])
        event = {"event": "command", "session_id": "target", "completed_at": self.start.isoformat(),
            "started_at": (self.start - timedelta(seconds=2)).isoformat(),
            "command": "window command", "cwd": "/current", "timestamps_scope": "legacy-prompt"}
        self.write("2026-06-20/bash/target.jsonl", [event,
            {"event": "session_end", "session_id": "target", "ended_at": (self.start + timedelta(minutes=1)).isoformat()}])
        result = bash.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.rows), 2)
        row = result.rows[0]
        self.assertEqual(row["started_at"], event["started_at"])
        self.assertEqual(row["cwd"], event["cwd"])
        self.assertEqual(row["timestamps_scope"], event["timestamps_scope"])
        self.assertEqual(row["session_context"]["started_at"], recent.isoformat())
        self.assertEqual(row["session_context"]["cwd"], "/synthetic")
        self.assertEqual(row["session_context"]["session_path"], str(previous))
        self.assertEqual(row["session_context"]["session_id"], "target")
        self.assertTrue(row["session_context"]["outside_window"])
        self.assertTrue(all(self.start <= datetime.fromisoformat(item["timestamp"]) < self.end for item in result.rows))
        self.assertNotIn("private command", json.dumps(result.rows))

    def test_legacy_flat_root_uses_actual_start_and_marks_unknown_scope(self):
        session_start = self.start - timedelta(days=3)
        self.write("legacy-session.jsonl", [
            {"event": "session_start", "started_at": session_start.isoformat(), "cwd": "/legacy"},
            {"event": "command", "completed_at": self.start.isoformat(), "command": "window command"}])
        result = bash.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(result.rows), 1)
        row = result.rows[0]
        self.assertEqual(row["session_context"]["started_at"], session_start.isoformat())
        self.assertEqual(row["session_context"]["session_key"], "legacy-session")
        self.assertIn("Coverage cannot be inferred", row["capture_scope_note"])

    def test_modern_commands_without_session_start_do_not_invent_context(self):
        self.write("2026-06-20/bash/modern.jsonl", [
            {"event": "command", "session_id": "modern", "completed_at": self.start.isoformat(),
                "started_at": (self.start - timedelta(seconds=2)).isoformat(),
                "command": "make test", "capture_scope": "first-simple-command"}])
        result = bash.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertNotIn("session_context", result.rows[0])
        self.assertNotIn("capture_scope_note", result.rows[0])
        self.assertEqual(result.rows[0]["session_context_status"], "not_recorded")

    def test_window_start_remains_activity_without_outside_context(self):
        self.write("2026-06-20/bash/session.jsonl", [
            {"event": "session_start", "session_id": "session", "started_at": self.start.isoformat()},
            {"event": "command", "session_id": "session", "completed_at": (self.start + timedelta(seconds=2)).isoformat(), "command": "make test"}])
        result = bash.collect(self.root, self.start, self.end)
        self.assertEqual([row["event"] for row in result.rows], ["session_start", "command"])
        self.assertNotIn("session_context", result.rows[1])
        self.assertEqual(result.rows[1]["session_context_status"], "in_window")


@unittest.skipIf(screenshots.Image is None, "optional Pillow is not installed")
class ScreenshotSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.start = datetime(2026, 6, 20, 4, tzinfo=timezone.utc)
        self.end = self.start + timedelta(days=1)

    def image(self, relative, timestamp=None, size=(1000, 500), reverse=False):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        image = screenshots.Image.new("RGB", size, "black")
        draw = screenshots.ImageDraw.Draw(image)
        left = size[0] // 2 if reverse else 0
        draw.rectangle((left, 0, left + size[0] // 2 - 1, size[1]), fill="white")
        image.save(path)
        seconds = (timestamp or self.start).timestamp()
        os.utime(path, (seconds, seconds))
        return path

    def test_date_first_and_legacy_flat_frames_use_capture_instants(self):
        first = self.image("2026-06-20/screenshots/one.png")
        second = self.image("2026-06-21/screenshots/two.png", self.end - timedelta(seconds=1))
        third = self.image("legacy/screen/three.png", self.start + timedelta(minutes=5), reverse=True)
        self.image("2026-06-20/screenshots/before.png", self.start - timedelta(seconds=1))
        self.image("2026-06-21/screenshots/end.png", self.end)
        result = screenshots.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "ok")
        self.assertEqual([row["path"] for row in result.rows], [str(first), str(third), str(second)])
        self.assertEqual([row["segment"] for row in result.rows], [1, 2, 3])
        self.assertEqual(result.rows[1]["seconds_since_previous_capture"], 300)
        self.assertTrue(all(row["hash_algorithm"] == "average_hash_16x16" for row in result.rows))
        self.assertEqual(result.rows[0]["sha256"], hashlib.sha256(first.read_bytes()).hexdigest())

    def test_manifest_time_survives_import_mtime_and_metadata_is_preserved(self):
        path = self.image("2026-06-20/screenshots/captured.png", self.start - timedelta(days=10))
        capture = {"filename": path.name, "captured_at": self.start.isoformat(),
            "capture_tool": "synthetic", "display": {"scale": 2}, "future_field": [1, 2]}
        (path.parent / "manifest.json").write_text(json.dumps({"frames": [capture]}), encoding="utf-8")
        rows = screenshots.collect(self.root, self.start, self.end).rows
        self.assertEqual(len(rows), 1)
        self.assertEqual(datetime.fromisoformat(rows[0]["timestamp"]), self.start)
        self.assertEqual(rows[0]["timestamp_semantics"], "manifest_capture_time")
        self.assertEqual(rows[0]["capture_metadata"], capture)

    def test_optional_pillow_unavailable_and_corrupt_frame_partial(self):
        self.image("good.png")
        invalid = self.root / "invalid.png"
        invalid.write_bytes(b"not-an-image")
        os.utime(invalid, (self.start.timestamp(), self.start.timestamp()))
        result = screenshots.collect(self.root, self.start, self.end)
        self.assertEqual(result.status, "partial")
        self.assertEqual(len(result.rows), 1)
        with patch.object(screenshots, "Image", None):
            self.assertEqual(screenshots.collect(self.root, self.start, self.end).status, "unavailable")
            self.assertEqual(screenshots.prepare_assets([], self.root / "assets")["status"], "unavailable")

    def test_all_similar_frames_get_contact_sheet_cells_and_replay_links(self):
        for ordinal in range(7):
            self.image(f"2026-06-20/screenshots/{ordinal}.png",
                self.start + timedelta(seconds=ordinal), size=(1600, 800))
        rows = screenshots.collect(self.root, self.start, self.end).rows
        self.assertEqual(len(rows), 7)
        self.assertEqual(sum(row["representative"] for row in rows), 1)
        for ordinal, row in enumerate(rows, 1):
            row["evidence_id"] = f"screenshots-{ordinal:04d}"
        target = self.root / "run/screenshots"
        metadata = screenshots.prepare_assets(rows, target)
        self.assertEqual(metadata["status"], "ok")
        self.assertEqual(metadata["coverage"]["converted_frames"], 7)
        self.assertEqual(metadata["coverage"]["mapped_frames"], 7)
        self.assertEqual(len(metadata["storyboards"]), 2)
        cells = []
        for sheet in metadata["storyboards"]:
            cells.extend(json.loads((target / sheet["mapping"]).read_text())["cells"])
            with screenshots.Image.open(target / sheet["image"]) as image:
                self.assertEqual(image.size, (1280, 1152))
        self.assertEqual([cell["evidence_id"] for cell in cells], [row["evidence_id"] for row in rows])
        self.assertEqual([cell["sha256"] for cell in cells], [row["sha256"] for row in rows])
        self.assertTrue(all(cell["frame_complete"] for cell in cells))
        self.assertTrue(all((cell["rendered_width"], cell["rendered_height"]) == (640, 320) for cell in cells))
        self.assertTrue(all(cell["scale_x"] == cell["scale_y"] for cell in cells))

    def test_changed_source_stays_mapped_as_failed_conversion(self):
        path = self.image("frame.png")
        rows = screenshots.collect(self.root, self.start, self.end).rows
        rows[0]["evidence_id"] = "screenshots-0001"
        path.write_bytes(b"changed")
        target = self.root / "run/screenshots"
        metadata = screenshots.prepare_assets(rows, target)
        self.assertEqual(metadata["status"], "partial")
        self.assertEqual(metadata["coverage"]["mapped_frames"], 1)
        self.assertEqual(metadata["coverage"]["converted_frames"], 0)
        cell = json.loads((target / metadata["storyboards"][0]["mapping"]).read_text())["cells"][0]
        self.assertEqual(cell["status"], "unavailable")
        self.assertFalse(cell["frame_complete"])

    def test_shared_tree_does_not_treat_vim_snapshots_as_screenshots(self):
        self.image("2026-06-20/vim/session/snapshot.png")
        self.assertEqual(screenshots.collect(self.root, self.start, self.end).rows, [])

    def test_prepare_assets_requires_runner_evidence_ids(self):
        self.image("frame.png")
        rows = screenshots.collect(self.root, self.start, self.end).rows
        with self.assertRaisesRegex(ValueError, "evidence IDs"):
            screenshots.prepare_assets(rows, self.root / "run")


if __name__ == "__main__":
    unittest.main()
