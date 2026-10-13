"""Discover machine-local paths independently of the checkout location."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    config: Path
    data: Path

    @property
    def state(self) -> Path:
        return self.data / "state"


def discover(*, system=None, home=None, environ=None) -> Paths:
    system = sys.platform if system is None else system
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    if system == "darwin":
        base = home / "Library" / "Application Support" / "my-big-brother"
        return Paths(base / "configs", base / "data")
    if system == "win32":
        base = Path(environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
        base = base / "my-big-brother"
        return Paths(base / "configs", base / "data")

    def xdg(name, fallback):
        value = Path(environ.get(name, ""))
        return value if value.is_absolute() else fallback

    return Paths(
        xdg("XDG_CONFIG_HOME", home / ".config") / "my-big-brother",
        xdg("XDG_DATA_HOME", home / ".local" / "share") / "my-big-brother",
    )


def absolute(value, name) -> Path:
    if not isinstance(value, str) or not value or "\n" in value or "\r" in value:
        raise ValueError(f"{name} must be a nonempty absolute path")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{name} must be absolute (no ~ or variable expansion)")
    return path


def raw_logs_root(paths: Paths) -> Path:
    locator = paths.config / "raw-logs-path.txt"
    if not locator.exists():
        return paths.data / "raw-logs"
    text = locator.read_bytes().decode("utf-8")
    if text.endswith("\r\n"):
        text = text[:-2]
    elif text.endswith("\n"):
        text = text[:-1]
    return absolute(text, str(locator))
