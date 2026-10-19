"""Select one builtin or explicitly bound personal source implementation."""

import hashlib
import importlib
import importlib.util
import json
import sys
from pathlib import Path

from .sources import SourceResult


def identities(sources):
    """Fingerprint selected files without executing them or scanning directories."""
    selected = {}
    for name, spec in sources.items():
        if not spec.get("enabled", True) or "reader" not in spec:
            continue
        path = Path(spec["reader"])
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            digest = None  # Collection will record the actual file error.
        selected[name] = {"path": str(path), "sha256": digest}
    return selected


def load(name, spec, identity=None):
    if "reader" not in spec:
        return importlib.import_module("my_big_brother.sources." + name)
    path = Path(spec["reader"])
    code = path.read_bytes()
    if identity != {"path": str(path), "sha256": hashlib.sha256(code).hexdigest()}:
        raise ValueError("Personal reader changed during preparation. Prepare again.")
    module_name = "_mbb_reader_" + hashlib.sha256(str(path).encode("utf-8")).hexdigest()
    module = importlib.util.module_from_spec(importlib.util.spec_from_file_location(module_name, path))
    sys.modules[module_name] = module
    try:
        # Execute exactly the fingerprinted bytes, without stale or new .pyc files.
        exec(compile(code, str(path), "exec"), module.__dict__)
        if not callable(getattr(module, "collect", None)):
            raise ValueError("Personal reader requires collect(path, start, end)")
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def validate(result):
    """Report a broken personal reader as an unavailable source, not an empty day."""
    if (not isinstance(result, SourceResult)
            or result.status not in {"ok", "partial", "unavailable"}
            or not isinstance(result.rows, list)
            or any(not isinstance(row, dict) for row in result.rows)
            or not isinstance(result.gaps, list)
            or any(not isinstance(gap, str) for gap in result.gaps)):
        raise ValueError("Personal reader must return SourceResult with rows, status and gaps")
    json.dumps(result.rows)
