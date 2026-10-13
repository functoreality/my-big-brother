"""Small JSON configuration, with explicit enabled inputs."""

import json
import os
import tempfile
from pathlib import Path

from .paths import Paths, absolute, raw_logs_root

OUTPUTS = ("worklog", "time-use", "insights", "time-estimates")
SOURCES = ("codex", "opencode", "bash")


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".mbb-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if Path(temporary).exists():
            # Preserve an interrupted write for diagnosis instead of deleting it.
            backup = path.parent / (Path(temporary).name + ".unfinished")
            os.replace(temporary, backup)


def defaults(paths: Paths):
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    xdg = Path(os.environ.get("XDG_DATA_HOME", ""))
    opencode_data = xdg if xdg.is_absolute() else Path.home() / ".local" / "share"
    return {
        "analyzer": "codex",
        "language": "en",
        "day_start_hour": 0,
        "results_root": str(paths.data / "results"),
        "sources": {
            "codex": {"enabled": True, "path": str(codex_home / "sessions")},
            "opencode": {"enabled": True, "path": str(opencode_data / "opencode" / "opencode.db")},
            "bash": {"enabled": True},
        },
        "outputs": list(OUTPUTS),
        "codex": {"executable": "codex", "timeout_seconds": 1800},
    }


def load(paths: Paths):
    path = paths.config / "config.json"
    if not path.exists():
        raise ValueError(f"Configuration not found: {path}. Run init first.")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("config.json must contain a JSON object")
    unknown = set(value) - set(defaults(paths))
    if unknown:
        raise ValueError(f"Unknown configuration fields: {', '.join(sorted(unknown))}")
    config = defaults(paths)
    config.update(value)
    if config["analyzer"] != "codex":
        raise ValueError("This release supports codex as the unattended analyzer")
    if not isinstance(config["language"], str) or not config["language"].strip():
        raise ValueError("language must be a language name or code")
    hour = config["day_start_hour"]
    if type(hour) is not int or not 0 <= hour <= 23:
        raise ValueError("day_start_hour must be an integer from 0 to 23")
    absolute(config["results_root"], "results_root")
    outputs = config["outputs"]
    if not isinstance(outputs, list) or not outputs or any(x not in OUTPUTS for x in outputs):
        raise ValueError(f"outputs must be a nonempty list of {', '.join(OUTPUTS)}")
    if len(outputs) != len(set(outputs)):
        raise ValueError("outputs must not contain duplicates")
    source_config = config["sources"]
    if not isinstance(source_config, dict) or set(source_config) - set(SOURCES):
        raise ValueError(f"sources must be an object with entries from {', '.join(SOURCES)}")
    for name, spec in source_config.items():
        if not isinstance(spec, dict) or type(spec.get("enabled", True)) is not bool:
            raise ValueError(f"sources.{name}.enabled must be a boolean")
        if name != "bash" and spec.get("enabled", True):
            absolute(spec.get("path"), f"sources.{name}.path")
        if set(spec) - {"enabled", "path"} or (name == "bash" and "path" in spec):
            raise ValueError(f"Invalid fields for sources.{name}")
    backend = config["codex"]
    if not isinstance(backend, dict) or set(backend) - {"executable", "timeout_seconds", "model"}:
        raise ValueError("codex supports executable, timeout_seconds, and optional model")
    backend.setdefault("executable", "codex")
    backend.setdefault("timeout_seconds", 1800)
    if not isinstance(backend["executable"], str) or not backend["executable"]:
        raise ValueError("codex.executable must be a program name or absolute path")
    if type(backend["timeout_seconds"]) is not int or backend["timeout_seconds"] < 1:
        raise ValueError("codex.timeout_seconds must be a positive integer")
    if "model" in backend and (not isinstance(backend["model"], str) or not backend["model"]):
        raise ValueError("codex.model must be a nonempty string")
    raw_logs_root(paths)
    return config


def initialize(paths, *, sources=None, results_root=None, raw_root=None):
    paths.config.mkdir(parents=True, exist_ok=True, mode=0o700)
    config_path = paths.config / "config.json"
    locator = paths.config / "raw-logs-path.txt"
    if not config_path.exists():
        config = defaults(paths)
        enabled = SOURCES if sources is None else sources
        config["sources"] = {name: spec for name, spec in config["sources"].items() if name in enabled}
        if results_root:
            config["results_root"] = str(absolute(results_root, "results_root"))
        write_json(config_path, config)
    elif sources is not None or results_root:
        raise ValueError("Existing config preserved. Edit config.json to change settings.")
    if locator.exists():
        if raw_root:
            raise ValueError("Existing raw-logs-path.txt preserved. Edit it to move logs.")
        raw_logs_root(paths)
    else:
        root = absolute(raw_root, "raw_root") if raw_root else paths.data / "raw-logs"
        with locator.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(str(root) + "\n")
    config = load(paths)
    for directory in (raw_logs_root(paths), Path(config["results_root"]), paths.state):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return config
