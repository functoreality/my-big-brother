"""Discover machine-local paths independently of the checkout location."""

from dataclasses import dataclass
from pathlib import Path

from .storage import Layout
from .collector_paths import capture_root, platform_paths


@dataclass(frozen=True)
class Paths:
    config: Path
    data: Path

    @property
    def layout(self):
        return Layout(self.raw_logs)

    @property
    def raw_logs(self):
        return capture_root(self.config, self.data)

    @property
    def memory(self):
        config = self.config / "config.json"
        if config.exists():
            import json
            return Path(json.loads(config.read_text(encoding="utf-8")).get("results_root", str(self.data / "memory")))
        return self.data / "memory"


def discover(*, system=None, home=None, environ=None) -> Paths:
    return Paths(*platform_paths(system, home, environ))


def absolute(value, name) -> Path:
    if not isinstance(value, str) or not value or "\n" in value or "\r" in value:
        raise ValueError(f"{name} must be a nonempty absolute path")
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"{name} must be absolute (no ~ or variable expansion)")
    return path


def is_within(path: Path, root: Path) -> bool:
    """Check resolved containment using APIs available before Python 3.9."""
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True
