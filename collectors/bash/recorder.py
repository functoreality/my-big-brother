#!/usr/bin/env python3
"""Standard-library writer for the opt-in interactive Bash collector."""

import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import uuid


def locations():
    home = Path.home()
    if sys.platform == "darwin":
        base = home / "Library" / "Application Support" / "my-big-brother"
        return base / "configs", base / "data"
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        return base / "my-big-brother" / "configs", base / "my-big-brother" / "data"

    def xdg(name, fallback):
        value = Path(os.environ.get(name, str(fallback)))
        return value if value.is_absolute() else fallback

    return (
        xdg("XDG_CONFIG_HOME", home / ".config") / "my-big-brother",
        xdg("XDG_DATA_HOME", home / ".local" / "share") / "my-big-brother",
    )


def raw_root():
    config, data = locations()
    pointer = config / "raw-logs-path.txt"
    if not pointer.exists():
        return data / "raw-logs"
    text = pointer.read_bytes().decode("utf-8")
    if text.endswith("\r\n"):
        text = text[:-2]
    elif text.endswith("\n"):
        text = text[:-1]
    path = Path(text)
    if not text or "\n" in text or "\r" in text or not path.is_absolute():
        raise ValueError(f"{pointer} must contain one absolute path")
    return path


SECRET = re.compile(
    r"(?i)(?:password|passwd|secret|token|api[_-]?key)\s*(?:=|:|\s)|"
    r"authorization\s*:|\bsshpass\b|https?://[^\s/@]+:[^\s/@]+@"
)


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="microseconds")


def record():
    fields = sys.stdin.buffer.read().split(b"\0")
    if len(fields) != 6 or fields[-1]:
        raise ValueError("invalid recorder payload")
    session, started, cwd, status, command = [
        value.decode("utf-8", errors="replace") for value in fields[:-1]
    ]
    if not re.fullmatch(r"[a-f0-9]{32}", session):
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
    directory = raw_root() / completed[:10] / "bash"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(directory / f"{session}.jsonl", flags, 0o600)
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    operation = sys.argv[1]
    if operation == "check":
        raw_root()
    elif operation == "session":
        print(uuid.uuid4().hex)
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
