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
                timestamp = parse_timestamp(event.get(TIME_FIELDS[event_type]))
                if timestamp is None:
                    gaps.append(f"Missing Bash timestamp: {path}:{ordinal}")
                    continue
                yield ordinal, event, timestamp
    except (OSError, UnicodeError) as error:
        gaps.append(f"Unreadable Bash log: {path} ({type(error).__name__})")


def collect(path: Path, start: datetime, end: datetime) -> SourceResult:
    if not path.is_dir():
        return SourceResult(status="unavailable", gaps=[f"Bash source unavailable: {path}"])
    # A shell keeps its opening file for its entire lifetime, even for months.
    # Search retained start dates, but never join separate session files.
    rows, gaps = [], []
    for session_path in sorted(path.glob("????-??-??/bash/*.jsonl")):
        context = None
        for ordinal, event, timestamp in _events(session_path, gaps):
            event_type = event["event"]
            if event_type == "session_start":
                context = (timestamp, event, ordinal)
            if not start <= timestamp < end:
                continue
            row = {**event, "timestamp": timestamp.isoformat(),
                   "timestamp_semantics": TIME_FIELDS[event_type],
                   "session_path": str(session_path), "event_ordinal": ordinal}
            if event_type == "command":
                row["content"] = event.get("command", "")
                row["capture_scope_note"] = "History input is not a complete terminal transcript. Coverage cannot be inferred."
            if event_type != "session_start":
                if context is None or context[0] > timestamp:
                    row["session_context_status"] = "not_recorded"
                elif context[0] >= start:
                    row["session_context_status"] = "in_window"
                else:
                    context_time, boundary, boundary_ordinal = context
                    row["session_context"] = {
                        **boundary, "timestamp": context_time.isoformat(),
                        "timestamp_semantics": "started_at", "outside_window": True,
                        "session_path": str(session_path), "event_ordinal": boundary_ordinal,
                    }
                    row["session_context_status"] = "outside_window"
            rows.append(row)
    rows.sort(key=lambda row: (parse_timestamp(row["timestamp"]), row["session_path"], row["event_ordinal"]))
    return SourceResult(rows, "partial" if gaps else "ok", gaps)
