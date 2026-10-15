"""Small JSON configuration, with explicit enabled inputs."""

import json
import hashlib
import os
import tempfile
from pathlib import Path
from string import Formatter

from .paths import Paths, absolute, raw_logs_root, is_within
from .storage import Layout

DEFAULT_OUTPUTS = ("worklog", "time-use", "insights", "time-estimates")
OUTPUTS = DEFAULT_OUTPUTS + ("user-model", "machine-context")
SOURCES = ("codex", "opencode", "bash", "vim", "screenshots")
KNOWLEDGE_KEYS = ("user_model", "machine_context")
OUTPUT_KEYS = ("worklog", "time_use_markdown", "time_use_json", "insights", "time_estimates") + KNOWLEDGE_KEYS


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
        "results_root": str(paths.data / "memory"),
        "local_profile": None,
        "sources": {
            "codex": {"enabled": True, "path": str(codex_home / "sessions")},
            "opencode": {"enabled": True, "path": str(opencode_data / "opencode" / "opencode.db")},
            "bash": {"enabled": True},
            "vim": {"enabled": False},
            "screenshots": {"enabled": False},
        },
        "outputs": list(DEFAULT_OUTPUTS),
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
    layout = paths.layout
    if config["day_start_hour"] != layout.hour:
        raise ValueError("day_start_hour differs from the fixed shared storage calendar")
    if not isinstance(config["analyzer"], str) or not config["analyzer"].strip():
        raise ValueError("analyzer must be a nonempty Agent name")
    if not isinstance(config["language"], str) or not config["language"].strip():
        raise ValueError("language must be a language name or code")
    hour = config["day_start_hour"]
    if type(hour) is not int or not 0 <= hour <= 23:
        raise ValueError("day_start_hour must be an integer from 0 to 23")
    absolute(config["results_root"], "results_root")
    result_root = Path(config["results_root"])
    if is_within(result_root, layout.daily) or is_within(layout.daily, result_root):
        raise ValueError("Formal results must be outside disposable daily storage")
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
        if type(spec.get("required", False)) is not bool:
            raise ValueError(f"sources.{name}.required must be a boolean")
        if name in {"codex", "opencode"} and spec.get("enabled", True):
            absolute(spec.get("path"), f"sources.{name}.path")
        if "path" in spec:
            absolute(spec["path"], f"sources.{name}.path")
        if set(spec) - {"enabled", "path", "required"}:
            raise ValueError(f"Invalid fields for sources.{name}")
    raw_logs_root(paths)
    profile = load_profile(config)
    if profile and any(is_within(Path(name.format(date="2020-01-15")), layout.daily)
                       for name in profile["output_paths"].values()):
        raise ValueError("Profile output paths must be outside disposable daily storage")
    return config


def path_list(value, name, *, files=False, must_exist=True):
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array of absolute paths")
    for item in value:
        path = absolute(item, name)
        if must_exist and (not path.exists() or (files and not path.is_file())):
            raise ValueError(f"{name} path is not available: {path}")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} contains duplicate paths")
    return value


def validation_argv(value, name):
    if not isinstance(value, list) or not value or any(not isinstance(x, str) for x in value):
        raise ValueError(f"{name} must be a nonempty argument array")
    executable = absolute(value[0], name)
    if not executable.is_file():
        raise ValueError(f"{name} executable is not available: {executable}")
    for argument in value:
        try:
            fields = {field for _, field, _, _ in Formatter().parse(argument) if field is not None}
            if fields - {"run_dir", "date"}:
                raise ValueError("unsupported placeholder")
            argument.format(run_dir="/example/run", date="2020-01-15")
        except (ValueError, KeyError, IndexError) as error:
            raise ValueError(f"{name} supports only {{run_dir}} and {{date}} placeholders") from error
    return value


def load_profile(config):
    """Load one explicitly selected local policy, without reading its context files."""
    selected = config.get("local_profile")
    if selected is None:
        return None
    path = absolute(selected, "local_profile")
    payload = path.read_bytes()
    value = json.loads(payload)
    allowed = {"schema_version", "instructions", "context_files", "output_paths",
               "output_schema", "output_file_mode", "validation_command", "post_review"}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("local_profile contains unsupported fields")
    if type(value.get("schema_version", 1)) is not int or value.get("schema_version", 1) != 1:
        raise ValueError("local_profile requires schema_version 1")
    instructions = path_list(value.get("instructions", []), "profile.instructions", files=True)
    context_files = path_list(value.get("context_files", []), "profile.context_files")
    output_paths = value.get("output_paths", {})
    if not isinstance(output_paths, dict) or set(output_paths) - set(OUTPUT_KEYS):
        raise ValueError("profile.output_paths contains unknown output keys")
    for key, template in output_paths.items():
        absolute(template, f"profile.output_paths.{key}")
        if key not in KNOWLEDGE_KEYS and "{date}" not in template:
            raise ValueError(f"profile.output_paths.{key} must contain {{date}}")
        try:
            if any(field != "date" for _, field, _, _ in Formatter().parse(template) if field is not None):
                raise ValueError("unsupported placeholder")
            template.format(date="2020-01-15")
        except (ValueError, KeyError, IndexError) as error:
            raise ValueError(f"profile.output_paths.{key} supports only {{date}}") from error
    schema = value.get("output_schema", "default")
    output_file_mode = value.get('output_file_mode')
    if output_file_mode is not None:
        if (not isinstance(output_file_mode, str) or len(output_file_mode) != 4
            or output_file_mode[0] != '0' or any(x not in '01234567' for x in output_file_mode)):
            raise ValueError('profile.output_file_mode must be a four-digit octal string')
    if not isinstance(schema, str) or not schema:
        raise ValueError("profile.output_schema must be a nonempty name")
    validator = value.get("validation_command")
    if validator is not None:
        validator = validation_argv(validator, "profile.validation_command")
    if schema != "default" and validator is None:
        raise ValueError("A custom output_schema requires validation_command")
    post = value.get("post_review")
    if post is not None:
        if not isinstance(post, dict) or set(post) - {"task", "read_paths", "write_paths", "validation_command"}:
            raise ValueError("profile.post_review contains unsupported fields")
        task = str(absolute(post.get("task"), "profile.post_review.task"))
        path_list([task], "profile.post_review.task", files=True)
        read_paths = path_list(post.get("read_paths", []), "profile.post_review.read_paths")
        write_paths = path_list(post.get("write_paths", []), "profile.post_review.write_paths", must_exist=False)
        for target in write_paths:
            if Path(target).exists() and not Path(target).is_dir():
                raise ValueError("profile.post_review.write_paths must be directories")
        post = {"task": task, "read_paths": read_paths, "write_paths": write_paths,
                "validation_command": validation_argv(post.get("validation_command"),
                                                       "profile.post_review.validation_command")}
    fingerprint = hashlib.sha256(payload)
    # Policy content affects completion. Evolving data files deliberately do not.
    policy_files = list(instructions) + ([post["task"]] if post else [])
    for command in [validator, post["validation_command"] if post else None]:
        for argument in command or []:
            candidate = Path(argument)
            if candidate.is_absolute() and candidate.suffix in {".py", ".sh", ".js", ".ps1"} and candidate.is_file():
                policy_files.append(argument)
    for name in sorted(set(policy_files)):
        fingerprint.update(name.encode("utf-8"))
        fingerprint.update(Path(name).read_bytes())
    profile = {"path": str(path), "digest": fingerprint.hexdigest(), "instructions": instructions,
            "context_files": context_files, "output_paths": output_paths, "output_schema": schema,
            "validation_command": validator, "post_review": post}
    if output_file_mode is not None:
        profile["output_file_mode"] = output_file_mode
    return profile


def initialize(paths, *, sources=None, results_root=None, raw_root=None, data_root=None, day_start_hour=0):
    paths.config.mkdir(parents=True, exist_ok=True, mode=0o700)
    config_path = paths.config / "config.json"
    locator = paths.config / "raw-logs-path.txt"
    if config_path.exists() and not (paths.config / "storage.json").exists():
        raise ValueError("Existing v1 configuration preserved. Run migrate-storage first.")
    if raw_root is not None:
        raise ValueError("Storage v2 uses --data-root, with a daily child, instead of --raw-logs-root")
    if (paths.config / "storage.json").exists():
        layout = paths.layout
        if data_root is not None and Path(data_root) != layout.root:
            raise ValueError("Existing storage preserved. Moving it requires migration.")
    else:
        layout = Layout.install(paths.config, data_root or paths.data, day_start_hour)
    if not config_path.exists():
        config = defaults(paths)
        config["day_start_hour"] = layout.hour
        config["results_root"] = str(layout.memory)
        enabled = SOURCES if sources is None else sources
        config["sources"] = {name: spec for name, spec in config["sources"].items() if name in enabled}
        if sources is not None:
            for spec in config["sources"].values():
                spec["enabled"] = True
        if results_root:
            config["results_root"] = str(absolute(results_root, "results_root"))
        write_json(config_path, config)
    elif sources is not None or results_root:
        raise ValueError("Existing config preserved. Edit config.json to change settings.")
    config = load(paths)
    for directory in (raw_logs_root(paths), Path(config["results_root"]), paths.state):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return config
