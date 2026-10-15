"""Index Vim session manifests without reading edited files or diff contents."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PureWindowsPath

from . import SourceResult, parse_timestamp
from ..paths import is_within


def _record_paths(root: Path) -> tuple[list[Path], bool]:
    # Sessions remain under their start dates, which can precede the window.
    directories = [path for path in root.glob("*/vim") if path.is_dir()]
    return sorted(path for directory in directories
                  for path in directory.glob("*/record.json")), bool(directories)


def _artifact_metadata(directory: Path) -> list[dict]:
    """Inventory recorder artifacts, leaving their contents at the source."""
    artifacts = []
    for path in sorted(directory.iterdir()):
        if path.name == "record.json" or not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError:
            artifacts.append({"path": str(path), "status": "unavailable"})
            continue
        artifacts.append({
            "path": str(path), "basename": path.name,
            "kind": "diff" if path.suffix == ".diff" else "snapshot",
            "size_bytes": stat.st_size,
            "mtime": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
            "status": "available",
        })
    return artifacts


def _artifact_reference(directory: Path, value: object) -> dict:
    if not isinstance(value, str) or not value or "/" in value or "\\" in value or value in (".", ".."):
        return {"reference": value, "status": "invalid_reference"}
    path = directory / value
    try:
        if not path.is_file() or not is_within(path, directory):
            return {"path": str(path), "status": "missing_or_outside_session"}
        return {"path": str(path), "status": "available", "size_bytes": path.stat().st_size}
    except OSError:
        return {"path": str(path), "status": "unavailable"}


def collect(source_root: Path, start: datetime, end: datetime) -> SourceResult:
    """Index whole sessions intersecting the analysis window across start dates.

    Source roots use DATE/vim/SESSION/record.json exclusively. Local timestamps
    use the host local zone. The complete original manifest stays
    in ``record_metadata``.
    """
    if not source_root.is_dir():
        return SourceResult(status="unavailable", gaps=[f"Vim source unavailable: {source_root}"])
    record_paths, source_present = _record_paths(source_root)
    if not source_present:
        return SourceResult(status="unavailable", gaps=[f"Vim source directory unavailable within source root: {source_root}"])
    rows, gaps, valid_records = [], [], 0
    for record_path in record_paths:
        try:
            raw = record_path.read_bytes()
            payload = json.loads(raw)
        except (OSError, UnicodeError, ValueError) as error:
            gaps.append(f"Unreadable Vim record: {record_path} ({type(error).__name__})")
            continue
        if not isinstance(payload, dict):
            gaps.append(f"Invalid Vim manifest: {record_path}")
            continue
        version = payload.get("schema_version")
        if "schema_version" in payload and (type(version) is not int or version != 1):
            gaps.append(f"Unsupported Vim schema_version {version!r}: {record_path}")
            continue
        if version == 1 and (
            payload.get("source") != "vim"
            or not isinstance(payload.get("session_id"), str)
            or re.fullmatch(r"[0-9a-f]{32}", payload["session_id"]) is None
        ):
            gaps.append(f"Invalid Vim version 1 source or session_id: {record_path}")
            continue
        session_start = parse_timestamp(payload.get("vim_start"))
        close_value = payload.get("vim_close")
        session_end = parse_timestamp(close_value)
        if session_start is None:
            gaps.append(f"Vim record lacks parseable start time: {record_path}")
            continue
        if close_value not in (None, "") and session_end is None:
            gaps.append(f"Vim record has an invalid close time: {record_path}")
            continue
        if session_end is not None and session_end < session_start:
            gaps.append(f"Vim record has an end before its start: {record_path}")
            continue
        valid_records += 1
        if session_start >= end or (session_end is not None and session_end <= start):
            continue
        if session_end is not None and session_end > end:
            gaps.append(f"Limitation: Vim record closes after snapshot end, complete diff excluded: {record_path}")
            continue
        local_naive = any(
            isinstance(value, str) and datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None
            for value in (payload.get("vim_start"), close_value) if value not in (None, "")
        )
        if local_naive:
            gaps.append(f"Vim legacy naive timestamp assumes host local timezone, DST may be ambiguous: {record_path}")
        session_status = "closed" if session_end is not None else "open"
        if session_end is None:
            gaps.append(f"Vim session is open at snapshot, complete diff unavailable: {record_path}")
        opened = payload.get("opened_files", [])
        if not isinstance(opened, list):
            gaps.append(f"Invalid Vim opened_files: {record_path}")
            opened = []
        try:
            artifacts = _artifact_metadata(record_path.parent)
        except OSError as error:
            artifacts = []
            gaps.append(f"Unreadable Vim artifact directory: {record_path.parent} ({type(error).__name__})")
        files = []
        file_ids = set()
        for ordinal, item in enumerate(opened, 1):
            if not isinstance(item, dict):
                gaps.append(f"Invalid Vim opened file: {record_path} entry {ordinal}")
                continue
            file_path = item.get("path", "")
            basename = (PureWindowsPath(file_path).name if "\\" in file_path else Path(file_path).name) if isinstance(file_path, str) else ""
            modified = item.get("modified")
            if type(modified) is not bool:
                modified = bool(item.get("lines_added", 0) or item.get("lines_deleted", 0)) if any(key in item for key in ("lines_added", "lines_deleted")) else None
            file_row = {
                **item, "basename": basename,
                "modified": modified,
            }
            if version == 1:
                identifier = item.get("id")
                valid_identifier = type(identifier) is int and identifier > 0 and identifier not in file_ids
                valid_path = isinstance(file_path, str) and (Path(file_path).is_absolute() or PureWindowsPath(file_path).is_absolute())
                if not valid_identifier or not valid_path or parse_timestamp(item.get("opened")) is None:
                    gaps.append(f"Malformed Vim version 1 file fields: {record_path} entry {ordinal}")
                if valid_identifier:
                    file_ids.add(identifier)
                if item.get("snapshot_status") != "ok":
                    gaps.append(f"Vim snapshot unavailable ({item.get('snapshot_status', 'missing status')}): {record_path} entry {ordinal}")
                if item.get("diff_generated") is not True:
                    gaps.append(f"Vim comparison unavailable ({item.get('error', item.get('snapshot_status', 'unknown'))}): {record_path} entry {ordinal}")
                for key, output_key in (("original_file", "original_artifact"), ("diff_file", "diff_artifact")):
                    expected = key in item or (key == "original_file" and item.get("snapshot_status") == "ok") or (key == "diff_file" and item.get("diff_generated") is True and modified is True)
                    if not expected:
                        continue
                    reference = _artifact_reference(record_path.parent, item.get(key))
                    file_row[output_key] = reference
                    if reference["status"] != "available":
                        gaps.append(f"Vim {key} {reference['status']}: {record_path} entry {ordinal}")
            files.append(file_row)
        row_time = max(start, session_start)
        digest = hashlib.sha256(raw).hexdigest()
        diff_paths = [item["path"] for item in artifacts if item.get("kind") == "diff"]
        rows.append({
            "timestamp": row_time.isoformat(),
            "timestamp_semantics": "session_overlap_start",
            "actual_session_start": session_start.isoformat(),
            "actual_session_end": session_end.isoformat() if session_end else None,
            "start": payload.get("vim_start"), "end": close_value,
            "record_path": str(record_path), "session_path": str(record_path.parent),
            "record_sha256": digest, "record_hash": digest,
            "record_metadata": payload, "files": files, "file_count": len(files),
            "artifacts": artifacts, "session_status": session_status,
            "diff_status": ("available" if diff_paths else "not_recorded") if session_end else "incomplete_session",
            "diff_paths": diff_paths,
            "snapshot_paths": [item["path"] for item in artifacts if item.get("kind") == "snapshot"],
            "diff_scope": "Whole-session diff. Changes cannot be attributed to a clipped window interval." if session_start < start else "Whole-session diff, not individual edit timestamps.",
            "timestamp_timezone": "host_local_assumed" if local_naive else "explicit_offset",
        })
    rows.sort(key=lambda row: (parse_timestamp(row["timestamp"]), row["record_path"]))
    status = "unavailable" if record_paths and valid_records == 0 else ("partial" if gaps else "ok")
    return SourceResult(rows, status, gaps)
