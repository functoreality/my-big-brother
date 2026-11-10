"""Read completed Bash events by timestamp across natural-date directories."""

from . import _shell


def collect(path, start, end):
    return _shell.collect(path, start, end, "bash")
