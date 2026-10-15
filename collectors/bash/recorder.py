#!/usr/bin/env python3
"""Standard-library writer for the opt-in interactive Bash collector."""

import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import importlib.util

_spec = importlib.util.spec_from_file_location("mbb_storage", Path(__file__).with_name("storage.py"))
_storage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_storage)


def locations():
    return _storage.platform_paths()


def daily_root():
    return _storage.Layout.for_collector(*locations()).daily


SECRET = re.compile(
    r"(?i)(?:password|passwd|secret|token|api[_-]?key)\s*(?:=|:|\s)|"
    r"authorization\s*:|\bsshpass\b|https?://[^\s/@]+:[^\s/@]+@"
)


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="microseconds")


def new_session(pid):
    if not re.fullmatch(r"[1-9][0-9]*", pid):
        raise ValueError("invalid Bash process identifier")
    timestamp = dt.datetime.fromisoformat(now()).strftime("%Y-%m-%dT%H%M%S%z")
    return f"{timestamp}-{pid}"


def record():
    fields = sys.stdin.buffer.read().split(b"\0")
    if len(fields) != 6 or fields[-1]:
        raise ValueError("invalid recorder payload")
    session, started, cwd, status, command = [
        value.decode("utf-8", errors="replace") for value in fields[:-1]
    ]
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}[+-][0-9]{4}-[1-9][0-9]*", session):
        raise ValueError("invalid session identifier")
    completed = now()
    redacted = bool(SECRET.search(command))
    row = {
        "event": "command",
        "session_id": session,
        "started_at": started,
        "completed_at": completed,
        "cwd": cwd,
        "command": "<redacted: possible secret>" if redacted else command,
        "exit_status": int(status),
        "capture_scope": "first-simple-command",
        "redacted": redacted,
    }
    layout = _storage.Layout.for_collector(*locations())
    try:
        directory = layout.ensure_day(completed[:10]) / "bash"
    except _storage.DiscardedDay:
        return
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(directory / f"{session}.jsonl", flags, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    operation = sys.argv[1]
    if operation == "check":
        daily_root()
    elif operation == "session":
        print(new_session(sys.argv[2]))
    elif operation == "time":
        print(now())
    elif operation == "record":
        record()
    else:
        raise ValueError("unknown recorder operation")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, IndexError, UnicodeError) as error:
        print(f"my-big-brother Bash recorder: {error}", file=sys.stderr)
        sys.exit(1)
