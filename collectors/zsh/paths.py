"""Platform discovery and the one-line shared capture-root locator."""

import os
from pathlib import Path
import sys


def platform_paths(system=None, home=None, environ=None):
    system = sys.platform if system is None else system
    home = Path.home() if home is None else Path(home)
    env = os.environ if environ is None else environ
    if system == "darwin":
        base = home / "Library" / "Application Support" / "my-big-brother"
        return base / "configs", base / "data"
    if system == "win32":
        base = Path(env.get("LOCALAPPDATA") or home / "AppData" / "Local") / "my-big-brother"
        return base / "configs", base / "data"

    def xdg(name, fallback):
        value = Path(env.get(name, ""))
        return value if value.is_absolute() else fallback

    return (xdg("XDG_CONFIG_HOME", home / ".config") / "my-big-brother",
            xdg("XDG_DATA_HOME", home / ".local" / "share") / "my-big-brother")


def capture_root(config_dir, data_dir):
    locator = Path(config_dir) / 'raw-logs-path.txt'
    if not locator.exists():
        return Path(data_dir) / 'raw-logs'
    value = locator.read_bytes().decode('utf-8')
    if value.endswith('\r\n'):
        value = value[:-2]
    elif value.endswith('\n'):
        value = value[:-1]
    if not value or '\n' in value or '\r' in value or not Path(value).is_absolute():
        raise ValueError('raw-logs-path.txt must contain one absolute path without quotes or expansion')
    return Path(value)
