"""Read completed Bash recorder events from natural-date directories."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from . import SourceResult, parse_timestamp


def collect(path: Path, start: datetime, end: datetime) -> SourceResult:
    if not path.is_dir():
        return SourceResult(status="unavailable", gaps=[f"Raw logs unavailable: {path}"])
    files = []
    day = start.astimezone().date()
    last_day = (end - timedelta(microseconds=1)).astimezone().date()
    while day <= last_day:
        files.extend((path / day.isoformat() / "bash").glob("*.jsonl"))
        day += timedelta(days=1)
    rows, gaps = [], []
    time_fields = {"session_start": "started_at", "command": "completed_at", "session_end": "ended_at"}
    for session_path in sorted(files):
        try:
            with session_path.open(encoding="utf-8") as handle:
                for ordinal, line in enumerate(handle, 1):
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        gaps.append(f"Invalid or incomplete Bash event: {session_path}:{ordinal}")
                        continue
                    if not isinstance(event, dict):
                        gaps.append(f"Invalid Bash event: {session_path}:{ordinal}")
                        continue
                    event_type = event.get("event")
                    if not isinstance(event_type, str) or event_type not in time_fields:
                        continue
                    timestamp = parse_timestamp(event.get(time_fields[event_type], event.get("timestamp")))
                    if timestamp is None:
                        gaps.append(f"Missing Bash timestamp: {session_path}:{ordinal}")
                        continue
                    if not start <= timestamp < end:
                        continue
                    row = {**event, "timestamp": timestamp.isoformat(),
                        "timestamp_semantics": time_fields[event_type],
                        "session_path": str(session_path), "event_ordinal": ordinal}
                    if event_type == "command":
                        row["content"] = event.get("command", "")
                    rows.append(row)
        except (OSError, UnicodeError) as error:
            gaps.append(f"Unreadable Bash log: {session_path} ({type(error).__name__})")
    rows.sort(key=lambda row: (parse_timestamp(row["timestamp"]), row["session_path"], row["event_ordinal"]))
    return SourceResult(rows, "partial" if gaps else "ok", gaps)
