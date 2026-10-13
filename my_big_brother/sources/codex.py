"""Extract user messages and final answers from Codex JSONL histories.

Supported forms are response_item messages, event_msg item_completed items,
and legacy event_msg user_message/agent_message records. Response-only
assistant messages need an explicit final phase or end_turn flag. Ambiguous
ones are excluded and reported as coverage gaps.
"""

import json
from datetime import datetime
from pathlib import Path

from . import ANALYSIS_MARKER, SourceResult, message_text, parse_timestamp


def _candidate(event: dict) -> tuple[str, str, str | None, str] | None:
    payload = event.get("payload")
    if not isinstance(payload, dict):
        return None
    representation = event.get("type")
    if representation == "response_item" and payload.get("type") == "message":
        if payload.get("role") == "user":
            role = "user"
        elif payload.get("role") == "assistant" and (
            payload.get("phase") in ("final_answer", "final")
            or payload.get("end_turn") is True
        ):
            role = "assistant_final"
        else:
            return None
        return role, message_text(payload.get("content")), payload.get("id"), "response"
    if representation != "event_msg":
        return None
    item = payload.get("item")
    if isinstance(item, dict):
        if item.get("type") == "UserMessage":
            role = "user"
        elif item.get("type") == "AgentMessage" and item.get("phase") in (
            "final_answer", "final"
        ):
            role = "assistant_final"
        else:
            return None
        return role, message_text(item.get("content")), item.get("id"), "event"
    if payload.get("type") == "user_message":
        return "user", message_text(payload.get("message")), payload.get("id"), "legacy"
    if payload.get("type") == "agent_message" and payload.get("phase") in (
        None, "final_answer", "final"
    ):
        return "assistant_final", message_text(payload.get("message")), payload.get("id"), "legacy"
    return None


def collect(path: Path, start: datetime, end: datetime) -> SourceResult:
    if not path.is_dir():
        return SourceResult(status="unavailable", gaps=[f"Codex sessions unavailable: {path}"])
    rows, gaps = [], []
    for session_path in sorted(path.rglob("*.jsonl")):
        candidates = []
        session_gaps = []
        thread_source = "unknown_legacy"
        excluded = False
        try:
            with session_path.open(encoding="utf-8") as handle:
                for ordinal, line in enumerate(handle, 1):
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        session_gaps.append(f"Invalid Codex JSON: {session_path}:{ordinal}")
                        continue
                    if not isinstance(event, dict):
                        session_gaps.append(f"Invalid Codex event: {session_path}:{ordinal}")
                        continue
                    payload = event.get("payload")
                    if event.get("type") == "session_meta" and isinstance(payload, dict):
                        source = payload.get("thread_source")
                        if source is not None:
                            thread_source = source
                            excluded |= source != "user"
                        origin = payload.get("source")
                        excluded |= isinstance(origin, dict) and "subagent" in origin
                    if (event.get("type") == "response_item" and isinstance(payload, dict)
                        and payload.get("type") == "message" and payload.get("role") == "assistant"
                        and payload.get("phase") is None and payload.get("end_turn") is not True):
                        timestamp = parse_timestamp(event.get("timestamp"))
                        if timestamp and start <= timestamp < end:
                            session_gaps.append(f"Codex assistant message has no final-answer marker: {session_path}:{ordinal}")
                    candidate = _candidate(event)
                    if candidate is None:
                        continue
                    role, content, identifier, representation = candidate
                    identifier = identifier if isinstance(identifier, str) else None
                    if role == "user" and content.startswith(ANALYSIS_MARKER):
                        excluded = True
                    timestamp = parse_timestamp(event.get("timestamp"))
                    if timestamp is None:
                        session_gaps.append(f"Missing Codex message timestamp: {session_path}:{ordinal}")
                        continue
                    if content and start <= timestamp < end:
                        candidates.append((timestamp, ordinal, role, content, identifier, representation))
        except (OSError, UnicodeError) as error:
            if not excluded:
                gaps.append(f"Unreadable Codex session: {session_path} ({type(error).__name__})")
            continue
        if excluded:
            continue
        gaps.extend(session_gaps)
        seen_ids = set()
        mirrored = {}
        for timestamp, ordinal, role, content, identifier, representation in candidates:
            if identifier and (role, identifier) in seen_ids:
                continue
            # Older logs mirror messages without IDs. Match only different
            # representations nearby, so repeated human messages remain intact.
            fingerprint = (role, content)
            previous_messages = mirrored.setdefault(fingerprint, [])
            duplicate = next((previous for previous in reversed(previous_messages)
                if representation not in previous["representations"]
                and abs((timestamp - previous["timestamp"]).total_seconds()) <= 5
                and not (identifier and previous["id"] and identifier != previous["id"])), None)
            if duplicate is not None:
                duplicate["representations"].add(representation)
                if identifier:
                    seen_ids.add((role, identifier))
                continue
            if identifier:
                seen_ids.add((role, identifier))
            previous_messages.append({"timestamp": timestamp, "id": identifier,
                "representations": {representation}})
            rows.append({
                "timestamp": timestamp.isoformat(), "role": role, "content": content,
                "thread_source": thread_source, "session_path": str(session_path),
                "event_ordinal": ordinal, "message_id": identifier,
            })
    rows.sort(key=lambda row: (parse_timestamp(row["timestamp"]), row["session_path"], row["event_ordinal"]))
    return SourceResult(rows, "partial" if gaps else "ok", gaps)
