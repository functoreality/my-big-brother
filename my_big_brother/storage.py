"""Storage v2 protocol for managed application writes.

Persistent storage is separate from the independent recorder path contract.
All writers register a calendar date before creating it. Missing registered
workspaces are abandoned, even if a review or a collector failed.
"""

import json
import os
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from .collector_paths import capture_root, platform_paths


class DiscardedDay(ValueError):
    pass


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
def file_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("a+b") as stream:
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
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
    def __init__(self, value, raw_logs_root=None):
        if (set(value) != {"schema_version", "data_root"}
                or type(value["schema_version"]) is not int or value["schema_version"] != 2):
            raise ValueError("storage.json requires the version 2 storage contract")
        root = value["data_root"]
        if (not isinstance(root, str) or not root or "\n" in root or "\r" in root
                or not Path(root).is_absolute()):
            raise ValueError("storage.data_root must be an absolute path")
        self.settings = value
        self.root = Path(root)
        self.raw_logs = Path(raw_logs_root) if raw_logs_root is not None else self.root / "raw-logs"
        self.memory = self.root / "memory"
        self.system = self.memory / "_system"
        raw_logs, memory = self.raw_logs.resolve(), self.memory.resolve()
        if raw_logs == memory or raw_logs in memory.parents or memory in raw_logs.parents:
            raise ValueError('Capture storage and permanent memory must not overlap')

    @classmethod
    def load(cls, config_dir, *, default_data_root=None):
        path = Path(config_dir) / "storage.json"
        if not path.exists():
            raise ValueError("Storage v2 is not initialized. Run init.")
        settings = read_json(path)
        default = platform_paths()[1] if default_data_root is None else default_data_root
        result = cls(settings, capture_root(config_dir, default))
        result.check()
        return result

    @classmethod
    def install(cls, config_dir, data_root):
        path = Path(config_dir) / "storage.json"
        settings = {"schema_version": 2, "data_root": str(data_root)}
        if path.exists():
            result = cls.load(config_dir, default_data_root=data_root)
            if result.settings != settings:
                raise ValueError("Existing storage preserved. Changing its root in place is unsupported.")
            return result
        result = cls(settings, capture_root(config_dir, data_root)).initialize_data()
        write_json(path, settings)
        locator = Path(config_dir) / 'raw-logs-path.txt'
        if not locator.exists():
            with locator.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(str(result.raw_logs) + '\n')
            locator.chmod(0o600)
        return result

    @classmethod
    def for_collector(cls, config_dir, data_root):
        """Optional shared configuration, otherwise ordinary platform defaults.

        Create runtime metadata, never an application configuration file.
        Collectors do not need the main application installed or initialized.
        """
        path = Path(config_dir) / "storage.json"
        settings = read_json(path) if path.exists() else {
            "schema_version": 2, "data_root": str(data_root)}
        return cls(settings, capture_root(config_dir, data_root)).initialize_data()

    def initialize_data(self):
        with file_lock(self.system / "locks" / "initialization.lock"):
            marker = self.system / "identity.json"
            if marker.exists():
                self.check()
                return self
            if any(path.name != "locks" for path in self.system.iterdir()):
                raise ValueError("Existing persistent storage has no marker. Do not reset it.")
            self.raw_logs.mkdir(parents=True, exist_ok=True, mode=0o700)
            (self.system / "days").mkdir(mode=0o700)
            write_json(marker, self.settings)
        return self

    def check(self):
        if read_json(self.system / "identity.json") != self.settings:
            raise ValueError("Storage identity changed or persistent metadata is unavailable")
        if not (self.system / "days").is_dir():
            raise ValueError("Persistent day registry is missing. Do not initialize an empty replacement.")

    def day(self, value=None):
        return timestamp(value).strftime("%Y-%m-%d")

    def launch_directory(self, preferred_day=None):
        # Log ownership only. The executing Agent chooses its review plan.
        preferred = preferred_day or (date.fromisoformat(self.day()) - timedelta(days=1)).isoformat()
        try:
            directory = self.ensure_day(preferred)
        except DiscardedDay:
            directory = self.ensure_day(self.day())
        launch = directory / "_launches" / uuid.uuid4().hex
        launch.mkdir(parents=True, mode=0o700)
        return launch

    def validate_day(self, day):
        parsed = date.fromisoformat(day)
        if parsed.isoformat() != day:
            raise ValueError("Dates must use YYYY-MM-DD")

    def _record(self, day):
        self.check()
        self.validate_day(day)
        path = self.system / "days" / (day + ".json")
        value = read_json(path) if path.exists() else None
        if value is not None:
            if (value.get("date") != day or value.get("disposition") not in ("retained", "discarded")
                    or not isinstance(value.get("workspace_id"), str)):
                raise ValueError("Invalid persistent day record: " + str(path))
            marker = self.raw_logs / day / "_workspace.json"
            missing = not marker.exists()
            mismatched = not missing and read_json(marker).get("workspace_id") != value["workspace_id"]
            if value["disposition"] == "retained" and (missing or mismatched):
                value["disposition"] = "discarded"
                write_json(path, value)
        return value

    def record(self, day):
        self.check()
        self.validate_day(day)
        with file_lock(self.system / "locks" / "storage" / (day + ".lock")):
            return self._record(day)

    def ensure_day(self, day, *, recreate=False):
        self.check()
        self.validate_day(day)
        with file_lock(self.system / "locks" / "storage" / (day + ".lock")):
            record = self._record(day)
            if record and record["disposition"] == "discarded" and not recreate:
                raise DiscardedDay("Day workspace was discarded: " + day)
            directory = self.raw_logs / day
            if record is None or record["disposition"] == "discarded":
                record = {"date": day, "workspace_id": uuid.uuid4().hex,
                          "disposition": "retained", "review": (record or {}).get("review", {})}
                write_json(self.system / "days" / (day + ".json"), record)
                directory.mkdir(parents=True, exist_ok=True, mode=0o700)
                write_json(directory / "_workspace.json", {"workspace_id": record["workspace_id"]})
            return directory

    def update_review(self, day, review):
        self.check()
        self.validate_day(day)
        with file_lock(self.system / "locks" / "storage" / (day + ".lock")):
            value = self._record(day)
            if value is None or value["disposition"] == "discarded":
                raise DiscardedDay("Day workspace was discarded: " + day)
            value["review"] = review
            write_json(self.system / "days" / (day + ".json"), value)

    def check_run(self, run_dir, workspace_id=None):
        directory = Path(run_dir).resolve()
        parts = directory.relative_to(self.raw_logs.resolve()).parts
        if len(parts) != 3 or parts[1] != "_analysis":
            raise ValueError("Not a storage v2 review run")
        record = self.record(parts[0])
        if (not record or record["disposition"] == "discarded"
                or (workspace_id is not None and workspace_id != record["workspace_id"])):
            raise DiscardedDay("Run belongs to a discarded workspace")
        return record
