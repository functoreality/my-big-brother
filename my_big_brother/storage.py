"""Disposable date directories and file locking, without a storage registry."""

import json
import os
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path


def read_json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object: " + str(path))
    return value


def write_json(path, value):
    """Atomic metadata replacement. Callers serialize writes to the same path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    pending = path.with_name(path.name + ".pending")
    with pending.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    pending.chmod(0o600)
    os.replace(pending, path)


@contextmanager
def file_lock(path, *, blocking=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "r+b") as stream:
        if os.fstat(stream.fileno()).st_size == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
                msvcrt.locking(stream.fileno(), mode, 1)
            else:
                import fcntl
                mode = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
                fcntl.flock(stream.fileno(), mode)
        except OSError as error:
            if not blocking:
                raise ValueError("Another review is running: " + str(path)) from error
            raise
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def timestamp(value=None):
    result = datetime.now().astimezone() if value is None else value
    if isinstance(result, str):
        result = datetime.fromisoformat(result.replace("Z", "+00:00"))
    if not isinstance(result, datetime) or result.utcoffset() is None:
        raise ValueError("An explicit timezone offset is required")
    return result.astimezone()


class Layout:
    def __init__(self, raw_logs):
        self.raw_logs = Path(raw_logs)

    def day(self, value=None):
        return timestamp(value).strftime("%Y-%m-%d")

    def directory(self, day):
        if date.fromisoformat(day).isoformat() != day:
            raise ValueError("Dates must use YYYY-MM-DD")
        return self.raw_logs / day

    def ensure_day(self, day):
        directory = self.directory(day)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        return directory

    def record(self, day):
        path = self.directory(day) / "review.json"
        if not path.exists():
            return None
        value = read_json(path)
        if value.get("date") != day or not isinstance(value.get("review"), dict):
            raise ValueError("Invalid dated review record: " + str(path))
        return value

    def update_review(self, day, review):
        directory = self.directory(day)
        if not directory.is_dir():
            raise ValueError("Review date directory no longer exists: " + day)
        write_json(directory / "review.json", {"date": day, "review": review})

    def check_run(self, run_dir):
        directory = Path(run_dir).resolve()
        parts = directory.relative_to(self.raw_logs.resolve()).parts
        if len(parts) != 3 or parts[1] != "_analysis" or not directory.is_dir():
            raise ValueError("Not an existing dated review run")
        self.directory(parts[0])

    def launch_directory(self, preferred_day=None):
        # Log ownership only. The executing Agent selects the review date.
        day = preferred_day or (date.fromisoformat(self.day()) - timedelta(days=1)).isoformat()
        launch = self.ensure_day(day) / "_launches" / uuid.uuid4().hex
        launch.mkdir(parents=True, mode=0o700)
        return launch
