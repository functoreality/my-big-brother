"""Read-only, source-specific activity adapters."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SourceResult:
    rows: list[dict] = field(default_factory=list)
    status: str = "ok"
    gaps: list[str] = field(default_factory=list)


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone()
    except (ValueError, OverflowError, OSError):
        return None


def message_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, list):
        return ""
    return "\n".join(
        part["text"] for part in value
        if isinstance(part, dict) and isinstance(part.get("text"), str)
        and part.get("type") in (None, "text", "input_text", "output_text")
    ).strip()


ANALYSIS_MARKER = "<!-- my-big-brother:analysis -->"
