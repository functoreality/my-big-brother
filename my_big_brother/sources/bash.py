"""Read completed Bash events by timestamp across natural-date directories."""

import json
from datetime import datetime
from pathlib import Path

from . import SourceResult, parse_timestamp


TIME_FIELDS = {"session_start": "started_at", "command": "completed_at", "session_end": "ended_at"}


def _events(path: Path, gaps: list[str]):
    try:
        with path.open(encoding="utf-8") as handle:
            for ordinal, line in enumerate(handle, 1):
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    gaps.append(f"Invalid or incomplete Bash event: {path}:{ordinal}")
                    continue
                if not isinstance(event, dict):
                    gaps.append(f"Invalid Bash event: {path}:{ordinal}")
                    continue
                event_type = event.get("event")
                if not isinstance(event_type, str) or event_type not in TIME_FIELDS:
                    continue
                timestamp = parse_timestamp(event.get(TIME_FIELDS[event_type], event.get("timestamp")))
                if timestamp is None:
                    gaps.append(f"Missing Bash timestamp: {path}:{ordinal}")
                    continue
                yield ordinal, event, timestamp
    except (OSError, UnicodeError) as error:
        gaps.append(f"Unreadable Bash log: {path} ({type(error).__name__})")


def _session_key(event: dict, path: Path) -> str:
    identifier = event.get("session_id")
    return identifier if isinstance(identifier, str) and identifier else path.stem


def collect(path: Path, start: datetime, end: datetime) -> SourceResult:
    if not path.is_dir():
        return SourceResult(status="unavailable", gaps=[f"Bash source unavailable: {path}"])
    files = list(path.glob("*.jsonl"))
    # A shell keeps its opening file for its entire lifetime, even for months.
    # Discover all retained sessions, then select events by actual timestamps.
    files.extend(path.glob("????-??-??/bash/*.jsonl"))
    rows, gaps, starts = [], [], {}
    files = sorted(set(files))
    for session_path in files:
        for ordinal, event, timestamp in _events(session_path, gaps):
            event_type = event["event"]
            key = _session_key(event, session_path)
            if event_type == "session_start" and timestamp < end:
                starts.setdefault(key, []).append((timestamp, event, session_path, ordinal))
            if not start <= timestamp < end:
                continue
            row = {**event, "timestamp": timestamp.isoformat(),
                "timestamp_semantics": TIME_FIELDS[event_type],
                "session_path": str(session_path), "event_ordinal": ordinal}
            if event_type == "command":
                row["content"] = event.get("command", "")
                if not any(field in event for field in ("capture_scope", "timestamps_scope", "timestamp_scope")):
                    row["capture_scope_note"] = "Legacy history has no recorded capture scope. Coverage cannot be inferred."
            rows.append(row)
    for row in rows:
        if row["event"] == "session_start":
            continue
        key = _session_key(row, Path(row["session_path"]))
        timestamp = parse_timestamp(row["timestamp"])
        candidates = [item for item in starts.get(key, []) if item[0] <= timestamp]
        if not candidates:
            row["session_context_status"] = "not_recorded"
            continue
        context_time, event, context_path, ordinal = max(candidates, key=lambda item: item[0])
        if context_time >= start:
            row["session_context_status"] = "in_window"
            continue
        row["session_context"] = {
            **event, "timestamp": context_time.isoformat(), "timestamp_semantics": "started_at",
            "outside_window": True, "session_key": key,
            "session_path": str(context_path), "event_ordinal": ordinal,
        }
        row["session_context_status"] = "outside_window"
    rows.sort(key=lambda row: (parse_timestamp(row["timestamp"]), row["session_path"], row["event_ordinal"]))
    return SourceResult(rows, "partial" if gaps else "ok", gaps)
