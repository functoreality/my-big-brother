"""Read WorkBuddy project conversations without inferring completion from usage."""

import json
import re
from datetime import datetime
from pathlib import Path

from . import ANALYSIS_MARKER, SourceResult, message_text


REMINDER = re.compile(r"<system-reminder\b[^>]*>.*?</system-reminder>", re.S)
USER_QUERY = re.compile(r"<user_query>(.*?)</user_query>", re.S)


def user_text(text):
    text = REMINDER.sub("", text)
    if "<system-reminder" in text or "<user_query" in USER_QUERY.sub("", text):
        return None
    queries = USER_QUERY.findall(text)
    if queries:
        return "\n\n".join(part.strip() for part in queries).strip()
    return text.strip()


def timestamp(value):
    if isinstance(value, bool):
        return None
    try:
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value / 1000).astimezone()
    except (ValueError, OverflowError, OSError):
        pass
    return None


def collect(path: Path, start: datetime, end: datetime) -> SourceResult:
    if not path.is_dir():
        return SourceResult(status="unavailable", gaps=[f"WorkBuddy projects unavailable: {path}"])
    rows, gaps = [], []
    for session_path in sorted(path.glob("*/*.jsonl")):
        candidates, session_gaps = [], []
        excluded = False
        cwd, title = None, None
        try:
            with session_path.open(encoding="utf-8-sig") as handle:
                for ordinal, line in enumerate(handle, 1):
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        session_gaps.append(f"Invalid WorkBuddy JSON: {session_path}:{ordinal}")
                        continue
                    if not isinstance(event, dict):
                        session_gaps.append(f"Invalid WorkBuddy event: {session_path}:{ordinal}")
                        continue
                    if isinstance(event.get("cwd"), str):
                        cwd = event["cwd"]
                    if event.get("type") == "ai-title" and isinstance(event.get("aiTitle"), str):
                        title = event["aiTitle"]
                    role = event.get("role")
                    if event.get("type") != "message" or role not in ("user", "assistant"):
                        continue
                    content = message_text(event.get("content"))
                    if role == "user":
                        raw = content
                        content = user_text(raw)
                        if ANALYSIS_MARKER in raw[:400] or ANALYSIS_MARKER in (content or "")[:400]:
                            excluded = True
                            break
                        # Do not reinterpret a damaged host wrapper as a human request.
                        if content is None:
                            session_gaps.append(f"Incomplete WorkBuddy user wrapper: {session_path}:{ordinal}")
                            continue
                    if not content:
                        continue
                    created = timestamp(event.get("timestamp"))
                    if created is None:
                        session_gaps.append(f"Missing WorkBuddy timestamp: {session_path}:{ordinal}")
                        continue
                    if start <= created < end:
                        candidates.append({
                            "timestamp": created.isoformat(), "role": role, "content": content,
                            "session_path": str(session_path), "session_id": session_path.stem,
                            "project": session_path.parent.name, "cwd": cwd,
                            "event_ordinal": ordinal, "message_id": event.get("id"),
                        })
        except (OSError, UnicodeError) as error:
            session_gaps.append(f"Unreadable WorkBuddy session: {session_path} ({type(error).__name__})")
        if not excluded:
            for row in candidates:
                row["title"] = title
            rows.extend(candidates)
            gaps.extend(session_gaps)
    rows.sort(key=lambda row: (datetime.fromisoformat(row["timestamp"]), row["session_path"], row["event_ordinal"]))
    return SourceResult(rows, "partial" if gaps else "ok", gaps)
