"""Index full screenshot frames and prepare replayable low-resolution assets.

Pillow is optional. Perceptual hashes retain the legacy 16x16 average-hash
algorithm, despite the historical field name ``perceptual_hash``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from . import SourceResult, parse_timestamp
from ..paths import is_within

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    Image = ImageDraw = ImageOps = None


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
CELL_WIDTH, IMAGE_HEIGHT, LABEL_HEIGHT = 640, 352, 32
SHEET_COLUMNS, SHEET_ROWS = 2, 3


def _directories(root: Path) -> list[Path]:
    directories = sorted(path for name in ('screenshots', 'screen_record')
                         for path in root.glob('*/' + name) if path.is_dir())
    for relative in ("screenshots", "legacy/screenshots", "legacy/screen", "legacy/screen_record"):
        candidate = root / relative
        if candidate.is_dir() and candidate not in directories:
            directories.append(candidate)
    # A configured legacy screenshot root can contain its original flat files.
    if not directories or any(path.suffix.lower() in IMAGE_SUFFIXES for path in root.iterdir()):
        directories.append(root)
    return directories


def _manifest(directory: Path, gaps: list[str]) -> dict[Path, dict]:
    records = {}
    for name in ("manifest.json", "manifest.jsonl"):
        path = directory / name
        if not path.is_file():
            continue
        try:
            contents = path.read_text(encoding="utf-8")
            entries = [json.loads(line) for line in contents.splitlines() if line.strip()] if name.endswith("jsonl") else json.loads(contents)
            if isinstance(entries, dict):
                entries = entries.get("frames", [])
            if not isinstance(entries, list):
                raise ValueError("frames must be a list")
        except (OSError, UnicodeError, ValueError) as error:
            gaps.append(f"Unreadable screenshot manifest: {path} ({type(error).__name__})")
            continue
        for ordinal, item in enumerate(entries, 1):
            if not isinstance(item, dict):
                gaps.append(f"Invalid screenshot manifest entry: {path}:{ordinal}")
                continue
            value = item.get("path", item.get("filename"))
            if not isinstance(value, str):
                gaps.append(f"Missing screenshot path: {path}:{ordinal}")
                continue
            candidate = Path(value)
            candidate = candidate if candidate.is_absolute() else directory / candidate
            if candidate.suffix.lower() not in IMAGE_SUFFIXES:
                gaps.append(f"Unsupported screenshot manifest extension: {path}:{ordinal}")
                continue
            if not is_within(candidate, directory):
                gaps.append(f"Screenshot manifest path outside source directory: {path}:{ordinal}")
                continue
            records[candidate.resolve()] = item
    return records


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _image_metadata(path: Path) -> tuple[str, int, int]:
    with Image.open(path) as image:
        width, height = image.size
        tiny = ImageOps.grayscale(image).resize((16, 16))
        values = list(tiny.get_flattened_data() if hasattr(tiny, "get_flattened_data") else tiny.getdata())
    average = sum(values) / len(values)
    bits = "".join("1" if value >= average else "0" for value in values)
    return f"{int(bits, 2):064x}", width, height


def collect(raw_root: Path, start: datetime, end: datetime) -> SourceResult:
    if not raw_root.is_dir():
        return SourceResult(status="unavailable", gaps=[f"Screenshot source unavailable: {raw_root}"])
    if Image is None:
        return SourceResult(status="unavailable", gaps=["Screenshot source requires optional Pillow dependency"])
    rows, gaps, seen = [], [], set()
    for directory in _directories(raw_root):
        manifest = _manifest(directory, gaps)
        files = directory.iterdir() if directory == raw_root else directory.rglob("*")
        candidates = {path.resolve() for path in files
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
            and is_within(path, directory)}
        candidates.update(manifest)
        for path in sorted(candidates):
            if path in seen:
                continue
            seen.add(path)
            metadata = manifest.get(path, {})
            value = metadata.get("timestamp", metadata.get("captured_at"))
            timestamp = parse_timestamp(value)
            semantics = "manifest_capture_time" if timestamp is not None else "file_mtime"
            if timestamp is not None and not start <= timestamp < end:
                continue
            try:
                stat = path.stat()
                if timestamp is None:
                    timestamp = datetime.fromtimestamp(stat.st_mtime).astimezone()
                if not start <= timestamp < end:
                    continue
                if value is not None and semantics == "file_mtime":
                    gaps.append(f"Invalid screenshot capture timestamp, using mtime: {path}")
                if semantics == "manifest_capture_time" and datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is None:
                    gaps.append(f"Screenshot naive timestamp assumes host local timezone, DST may be ambiguous: {path}")
                digest = file_digest(path)
                fingerprint, width, height = _image_metadata(path)
            except (OSError, ValueError, OverflowError) as error:
                gaps.append(f"Unreadable screenshot: {path} ({type(error).__name__})")
                continue
            rows.append({
                "path": str(path), "timestamp": timestamp.isoformat(),
                "timestamp_semantics": semantics, "sha256": digest,
                "perceptual_hash": fingerprint, "hash_algorithm": "average_hash_16x16",
                "width": width, "height": height, "size_bytes": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
                "capture_metadata": metadata, "frame_status": "available",
            })
    rows.sort(key=lambda row: (parse_timestamp(row["timestamp"]), row["path"]))
    previous, segment = None, 0
    for row in rows:
        distance = None if previous is None else bin(int(previous["perceptual_hash"], 16) ^ int(row["perceptual_hash"], 16)).count("1")
        representative = distance is None or distance > 16
        if representative:
            segment += 1
        row.update({
            "segment": segment, "representative": representative,
            "hamming_distance_from_previous": distance,
            "previous_capture_timestamp": previous["timestamp"] if previous else None,
            "seconds_since_previous_capture": (parse_timestamp(row["timestamp"]) - parse_timestamp(previous["timestamp"])).total_seconds() if previous else None,
        })
        previous = row
    return SourceResult(rows, "partial" if gaps else "ok", gaps)


def prepare_assets(rows: list[dict], run_target: Path) -> dict:
    """Create full-frame contact sheets after the runner assigns evidence IDs.

    Return source-manifest metadata with run-relative asset paths. Every row
    gets one cell, including similar frames and failed conversions. Failures
    stay visible in the cell mapping and coverage counts.
    """
    coverage = {
        "indexed_frames": len(rows), "mapped_frames": 0, "converted_frames": 0,
        "first_capture": rows[0]["timestamp"] if rows else None,
        "last_capture": rows[-1]["timestamp"] if rows else None,
        "time_semantics": "Observed capture instants only. No attention or work duration inferred.",
    }
    metadata = {"status": "ok", "gaps": [], "storyboards": [], "coverage": coverage}
    if Image is None:
        metadata.update(status="unavailable", gaps=["Screenshot assets require optional Pillow dependency"])
        return metadata
    if any(not isinstance(row.get("evidence_id"), str) for row in rows):
        raise ValueError("Screenshot evidence IDs must be assigned before prepare_assets")
    if not rows:
        return metadata
    directory = run_target
    directory.mkdir(parents=True, exist_ok=True)
    per_sheet = SHEET_COLUMNS * SHEET_ROWS
    for chunk_start in range(0, len(rows), per_sheet):
        chunk = rows[chunk_start:chunk_start + per_sheet]
        canvas = Image.new("RGB", (SHEET_COLUMNS * CELL_WIDTH, SHEET_ROWS * (IMAGE_HEIGHT + LABEL_HEIGHT)), "#1e1e1e")
        draw = ImageDraw.Draw(canvas)
        mapping = []
        for offset, row in enumerate(chunk):
            x = (offset % SHEET_COLUMNS) * CELL_WIDTH
            y = (offset // SHEET_COLUMNS) * (IMAGE_HEIGHT + LABEL_HEIGHT)
            cell = {
                "cell": offset + 1, "evidence_id": row["evidence_id"],
                "source_path": row["path"], "timestamp": row["timestamp"],
                "sha256": row["sha256"], "segment": row["segment"],
                "width": row["width"], "height": row["height"],
                "frame_complete": True, "status": "converted",
            }
            try:
                path = Path(row["path"])
                if file_digest(path) != row["sha256"]:
                    raise ValueError("source changed after indexing")
                with Image.open(path) as original:
                    thumb = original.convert("RGB")
                    thumb.thumbnail((CELL_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
                left = x + (CELL_WIDTH - thumb.width) // 2
                top = y + (IMAGE_HEIGHT - thumb.height) // 2
                canvas.paste(thumb, (left, top))
                cell.update({
                    "rendered_width": thumb.width, "rendered_height": thumb.height,
                    "image_box": [left, top, left + thumb.width, top + thumb.height],
                    "scale_x": thumb.width / row["width"], "scale_y": thumb.height / row["height"],
                    "conversion": "RGB, aspect-preserving thumbnail, no crop or upscaling",
                })
                coverage["converted_frames"] += 1
            except (OSError, ValueError) as error:
                cell.update(status="unavailable", frame_complete=False, error=str(error))
                metadata["gaps"].append(f"Screenshot asset unavailable: {row['path']} ({error})")
            draw.rectangle((x, y + IMAGE_HEIGHT, x + CELL_WIDTH, y + IMAGE_HEIGHT + LABEL_HEIGHT), fill="#111111")
            label = f"{offset + 1:02d} {row['evidence_id']} {row['timestamp']} seg {row['segment']}"
            draw.text((x + 4, y + IMAGE_HEIGHT + 8), label, fill="white")
            mapping.append(cell)
            coverage["mapped_frames"] += 1
        number = chunk_start // per_sheet + 1
        image_path = directory / f"storyboard-{number:04d}.jpg"
        mapping_path = image_path.with_suffix(".json")
        canvas.save(image_path, quality=85)
        mapping_path.write_text(json.dumps({"cells": mapping}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        metadata["storyboards"].append({
            "image": image_path.relative_to(run_target).as_posix(),
            "mapping": mapping_path.relative_to(run_target).as_posix(),
            "cells": len(mapping), "width": canvas.width, "height": canvas.height,
        })
    metadata["status"] = "partial" if metadata["gaps"] else "ok"
    return metadata
