"""Discover machine-local paths independently of the checkout location."""

from dataclasses import dataclass
from pathlib import Path

from .storage import Layout
from .collector_paths import platform_paths


@dataclass(frozen=True)
class Paths:
    config: Path
    data: Path

    @property
    def state(self) -> Path:
        return self.layout.system

    @property
    def layout(self):
        return Layout.load(self.config, default_data_root=self.data)

    @property
    def raw_logs(self):
        return self.layout.raw_logs

    @property
    def memory(self):
        return self.layout.memory


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
