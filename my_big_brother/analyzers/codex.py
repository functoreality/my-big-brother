"""Launch the installed Codex CLI without changing its authentication."""

import argparse
import json
import os
import signal
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def validate_settings(value):
    if not isinstance(value, dict) or set(value) - {"executable", "timeout_seconds", "model"}:
        raise ValueError("codex supports executable, timeout_seconds, and optional model")
    settings = {"executable": "codex", "timeout_seconds": 1800, **value}
    if not isinstance(settings["executable"], str) or not settings["executable"]:
        raise ValueError("codex.executable must be a program name or absolute path")
    if type(settings["timeout_seconds"]) is not int or settings["timeout_seconds"] < 1:
        raise ValueError("codex.timeout_seconds must be a positive integer")
    if "model" in settings and (not isinstance(settings["model"], str) or not settings["model"]):
        raise ValueError("codex.model must be a nonempty string")
    return settings


def command(settings, run_dir, *, write_paths=()):
    settings = validate_settings(settings)
    executable = shutil.which(settings["executable"])
    if executable is None:
        raise ValueError("Codex executable not found. Install it and log in before using this launcher.")
    prefix = [executable]
    if os.name == "nt" and Path(executable).suffix.lower() in {".cmd", ".bat"}:
        script = Path(executable).parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        node = shutil.which("node.exe")
        if not script.is_file() or not node:
            raise ValueError("Unrecognized Windows Codex wrapper. Set codex.executable to the native codex.exe path.")
        prefix = [node, str(script)]
    args = prefix + ["-c", 'approval_policy="never"', "exec",
            "--sandbox", "workspace-write", "--skip-git-repo-check",
            "--ephemeral", "--color", "never", "--cd", str(run_dir),
            "--output-last-message", str(run_dir / "logs" / "last-message.txt")]
    if settings.get("model"):
        args.extend(["--model", settings["model"]])
    for name in write_paths:
        path = Path(name)
        if not path.is_absolute() or not path.is_dir():
            raise ValueError(f"Additional writable root must be an absolute directory: {name}")
        args.extend(["--add-dir", str(path)])
    args.append("-")
    return args


def launch(settings, run_dir, prompt, *, write_paths=(), environment=None):
    settings = validate_settings(settings)
    args = command(settings, run_dir, write_paths=write_paths)
    (run_dir / "logs" / "command.json").write_text(
        json.dumps(args, indent=2) + "\n", encoding="utf-8")
    with (run_dir / "logs" / "stdout.log").open("w", encoding="utf-8") as out:
        with (run_dir / "logs" / "stderr.log").open("w", encoding="utf-8") as err:
            process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                       start_new_session=os.name != "nt", env=environment)
            try:
                process.communicate(prompt.encode("utf-8"), timeout=settings["timeout_seconds"])
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                if os.name == "nt":
                    process.kill()
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                process.communicate()
                raise
    if process.returncode:
        raise ValueError(f"Codex exited with {process.returncode}. See {run_dir / 'logs' / 'stderr.log'}")


def writable_roots(paths, settings):
    """Expose only runtime destinations selected by this installation."""
    from .. import config, runner
    profile = config.load_profile(settings)
    result_root = Path(settings["results_root"]).resolve()
    raw_logs = paths.raw_logs.resolve()
    if result_root == raw_logs or raw_logs in result_root.parents:
        raise ValueError("Formal results overlap disposable raw-log storage: " + str(result_root))
    roots = [paths.state, paths.raw_logs, Path(settings["results_root"])]
    if profile:
        for template in profile["output_paths"].values():
            prefix = template.split("{date}", 1)[0]
            roots.append(Path(prefix) if prefix.endswith(("/", "\\")) else Path(prefix).parent)
        if profile["post_review"]:
            roots.extend(Path(name) for name in profile["post_review"]["write_paths"])
    roots = sorted(set(path.resolve() for path in roots))
    protected = [runner.REPO.resolve(), paths.config.resolve()]
    protected.extend(Path(spec["path"]).resolve() for spec in settings["sources"].values()
                     if spec.get("enabled", True) and spec.get("path")
                     and Path(spec["path"]).resolve() != paths.raw_logs.resolve())
    for root in roots:
        if root in paths.raw_logs.resolve().parents:
            raise ValueError("Writable root contains protected raw-log storage: " + str(root))
        for path in protected:
            if root == path or root in path.parents or path in root.parents:
                raise ValueError(f"Writable root overlaps protected checkout, configuration or source logs: {root}")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return [str(root) for root in roots]


def automate(paths, settings, *, review_date=None, max_days=7, snapshot_end=None, allow_empty=False, task=None, write_dirs=()):
    """Start one Agent. It owns the common prepare, review and finish workflow."""
    from .. import config, runner
    backend = validate_settings(settings["codex"])
    if not 1 <= max_days <= 31:
        raise ValueError("max_days must be from 1 to 31")
    if not review_date and (snapshot_end is not None or allow_empty):
        raise ValueError("snapshot-end and allow-empty require --date")
    if snapshot_end is not None and (
        not isinstance(snapshot_end, datetime) or snapshot_end.utcoffset() is None
    ):
        raise ValueError("snapshot_end must be a datetime with a timezone offset")
    selected_task = Path(task) if task is not None else runner.REPO / "tasks/daily-review/AUTOMATION.md"
    if not selected_task.is_absolute() or not selected_task.is_file() or not os.access(selected_task, os.R_OK):
        raise ValueError("task must be a readable absolute task file")
    write_paths = writable_roots(paths, settings)
    # Extra roots are an explicit installation grant, for example a private importer.
    for name in write_dirs:
        root = Path(name)
        if not root.is_absolute():
            raise ValueError("write-dir must be absolute")
        root = root.resolve()
        for protected in (runner.REPO.resolve(), paths.config.resolve()):
            if root == protected or root in protected.parents or protected in root.parents:
                raise ValueError("Explicit writable root overlaps protected checkout or configuration")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if str(root) not in write_paths:
            write_paths.append(str(root))
    launch_dir = paths.layout.launch_directory(review_date)
    invocation_id = launch_dir.name
    (launch_dir / "logs").mkdir(mode=0o700)
    context = {"invocation_id": invocation_id, "checkout": str(runner.REPO),
               "python_executable": sys.executable, "config": str(paths.config / "config.json"),
               "date": review_date, "max_days": None if review_date else max_days,
               "snapshot_end": snapshot_end.isoformat() if snapshot_end else None,
               "allow_empty": allow_empty, "task": str(selected_task),
               "extra_write_paths": [str(Path(name).resolve()) for name in write_dirs]}
    config.write_json(launch_dir / "context.json", context)
    prompt = ("<!-- my-big-brother:analysis -->\n"
              "Perform the shared unattended review workflow in the current Agent session.\n"
              f"Task: {selected_task}\n"
              f"Launch context: {launch_dir / 'context.json'}\n"
              "Read that task and context, then invoke the common CLI yourself.\n"
              "Do not invoke another startup entry. Do not modify configuration or the checkout.\n")
    (launch_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    environment = dict(os.environ)
    environment.update(PYTHONPATH=str(runner.REPO), PYTHONDONTWRITEBYTECODE="1")
    temporary_root = launch_dir / "tmp"
    temporary_root.mkdir(mode=0o700)
    environment.update(TMPDIR=str(temporary_root), TMP=str(temporary_root), TEMP=str(temporary_root))
    runner.state(launch_dir, "running", invocation_id=invocation_id)
    try:
        launch(backend, launch_dir, prompt, write_paths=write_paths, environment=environment)
    except BaseException as error:
        runner.state(launch_dir, "failed", invocation_id=invocation_id, error=str(error))
        raise
    runner.state(launch_dir, "agent-exited", invocation_id=invocation_id)
    return {"status": "agent-exited", "launch_dir": str(launch_dir)}


def main(argv=None):
    from .. import config
    from ..paths import discover
    parser = argparse.ArgumentParser(prog="python -m my_big_brother.analyzers.codex")
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--date")
    selector.add_argument("--max-days", type=int, default=7)
    parser.add_argument("--write-dir", action="append", default=[], help="Explicit additional Agent write permission")
    parser.add_argument("--task", help="Absolute task file, default the shared automation task")
    parser.add_argument("--snapshot-end")
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args(argv)
    try:
        paths = discover()
        cutoff = datetime.fromisoformat(args.snapshot_end.replace("Z", "+00:00")) if args.snapshot_end else None
        result = automate(paths, config.load(paths), review_date=args.date, max_days=args.max_days,
                          snapshot_end=cutoff, allow_empty=args.allow_empty, task=args.task, write_dirs=args.write_dir)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(f"my-big-brother Codex launcher: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("my-big-brother Codex launcher: cancelled, diagnostics preserved", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
