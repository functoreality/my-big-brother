"""Read top-level OpenCode conversation text from a read-only SQLite connection."""

import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from . import ANALYSIS_MARKER, SourceResult


def _user_text(content: str) -> str:
    if content.startswith("[search-mode]\nMAXIMIZE SEARCH EFFORT."):
        boundary = re.search(r"\n---\n\n(?=\S)", content)
        if boundary:
            return content[boundary.end():].strip()
    return content


def collect(path: Path, start: datetime, end: datetime) -> SourceResult:
    if not path.is_file():
        return SourceResult(status="unavailable", gaps=[f"OpenCode database unavailable: {path}"])
    connection = None
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        columns = {row[1] for row in connection.execute("PRAGMA table_info(part)")}
        part_order = "p.time_created, p.id" if "time_created" in columns else "p.id"
        query = f"""
            SELECT s.id AS session_id, m.id AS message_id,
                   m.time_created, m.data AS message_data,
                   p.id AS part_id, p.data AS part_data
            FROM session AS s
            JOIN message AS m ON m.session_id = s.id
            JOIN part AS p ON p.message_id = m.id
            WHERE s.parent_id IS NULL
              AND m.time_created >= ? AND m.time_created < ?
            ORDER BY m.time_created, m.id, {part_order}
        """
        records = connection.execute(query, (
            int(start.timestamp() * 1000), int(end.timestamp() * 1000)
        )).fetchall()
        # The analyzer marker may precede the requested window. Check user
        # messages across candidate sessions without materializing their content.
        marked = set()
        for session_id in {row["session_id"] for row in records}:
            for record in connection.execute("""
                SELECT m.data AS message_data, p.data AS part_data
                FROM message AS m JOIN part AS p ON p.message_id = m.id
                WHERE m.session_id = ?
            """, (session_id,)):
                try:
                    message, part = json.loads(record[0]), json.loads(record[1])
                except (ValueError, TypeError):
                    continue
                if (isinstance(message, dict) and message.get("role") == "user"
                    and isinstance(part, dict) and isinstance(part.get("text"), str)
                    and part["text"].startswith(ANALYSIS_MARKER)):
                    marked.add(session_id)
                    break
    except (sqlite3.Error, OSError, ValueError) as error:
        return SourceResult(status="unavailable", gaps=[
            f"OpenCode database or schema unavailable: {path} ({type(error).__name__})"
        ])
    finally:
        if connection is not None:
            connection.close()

    messages, gaps = {}, []
    for record in records:
        if record["session_id"] in marked:
            continue
        try:
            message = json.loads(record["message_data"])
            part = json.loads(record["part_data"])
        except (ValueError, TypeError):
            gaps.append(f"Invalid OpenCode JSON: message {record['message_id']}, part {record['part_id']}")
            continue
        if not isinstance(message, dict) or not isinstance(part, dict):
            gaps.append(f"Invalid OpenCode record: part {record['part_id']}")
            continue
        if part.get("type") != "text" or not isinstance(part.get("text"), str):
            continue
        entry = messages.setdefault(record["message_id"], {
            "session_id": record["session_id"], "message_id": record["message_id"],
            "timestamp": record["time_created"], "role": message.get("role"),
            "finish": message.get("finish"), "parts": [], "part_ids": [],
        })
        entry["parts"].append(part["text"])
        entry["part_ids"].append(record["part_id"])

    rows = []
    for entry in messages.values():
        content = "\n".join(entry["parts"]).strip()
        if entry["role"] == "user":
            if content.startswith("<system-reminder>") or "<!-- OMO_INTERNAL_INITIATOR -->" in content:
                continue
            content = _user_text(content)
            role = "user"
        elif entry["role"] == "assistant" and entry["finish"] == "stop":
            role = "assistant_final"
        else:
            continue
        if content:
            rows.append({
                "timestamp": datetime.fromtimestamp(entry["timestamp"] / 1000).astimezone().isoformat(),
                "role": role, "content": content, "session_id": entry["session_id"],
                "message_id": entry["message_id"], "part_ids": entry["part_ids"],
                "database_path": str(path),
            })
    rows.sort(key=lambda row: (datetime.fromisoformat(row["timestamp"]), row["message_id"]))
    return SourceResult(rows, "partial" if gaps else "ok", gaps)
