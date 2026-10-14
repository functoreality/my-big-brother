"""Launch the installed Codex CLI without changing its authentication."""

import argparse
import json
import os
import signal
import shutil
import subprocess
import sys
import uuid
from datetime import date, datetime, timedelta
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


def invocation_dates(settings, review_date, max_days):
    from .. import runner
    if review_date:
        date.fromisoformat(review_date)
        return [review_date]
    latest = date.fromisoformat(runner.latest_closed_date(settings["day_start_hour"]))
    return [(latest - timedelta(days=offset)).isoformat() for offset in reversed(range(max_days))]


def writable_roots(paths, settings, review_dates):
    """Expose only runtime destinations selected by this installation."""
    from .. import config, runner
    from ..paths import raw_logs_root
    profile = config.load_profile(settings)
    roots = [paths.state, Path(settings["results_root"])]
    if profile:
        roots.extend(Path(template.format(date=review_date)).parent
                     for review_date in review_dates
                     for template in profile["output_paths"].values())
        if profile["post_review"]:
            roots.extend(Path(name) for name in profile["post_review"]["write_paths"])
    roots = sorted(set(path.resolve() for path in roots))
    protected = [runner.REPO.resolve(), paths.config.resolve(), raw_logs_root(paths).resolve()]
    protected.extend(Path(spec["path"]).resolve() for spec in settings["sources"].values()
                     if spec.get("enabled", True) and spec.get("path"))
    for root in roots:
        for path in protected:
            if root == path or root in path.parents or path in root.parents:
                raise ValueError(f"Writable root overlaps protected checkout, configuration or source logs: {root}")
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return [str(root) for root in roots]


def validate_launch_receipt(paths, settings, launch_dir, context):
    from .. import runner
    receipt = runner.read_object(launch_dir / "completion.json")
    tickets = json.loads((launch_dir / "tickets.json").read_text(encoding="utf-8"))
    results = receipt.get("results")
    if receipt.get("invocation_id") != context["invocation_id"]:
        raise ValueError("Launcher receipt invocation mismatch")
    if not isinstance(tickets, list) or not isinstance(results, list):
        raise ValueError("Launcher requires ticket and result arrays")
    expected = context["dates"]
    if (len(tickets) != len(expected) or len(results) != len(expected)
        or not all(isinstance(item, dict) for item in tickets + results)
        or [item.get("date") for item in tickets] != expected
        or [item.get("date") for item in results] != expected):
        raise ValueError("Launcher receipt must cover exactly the requested dates, oldest first")
    for ticket, result in zip(tickets, results):
        review_date = result["date"]
        status = result.get("status")
        run_dir = result.get("run_dir")
        if status == "already-completed":
            if (ticket.get("status") != status or not runner.completed(paths, settings, review_date)
                or run_dir != runner.day_entry(paths, review_date).get("run_dir")):
                raise ValueError("Unverified already-completed launcher result")
        elif status == "completed":
            entry = runner.day_entry(paths, review_date)
            if (ticket.get("status") not in {"prepared", "actions-pending", "completed"}
                or ticket.get("run_dir") != run_dir or entry.get("run_dir") != run_dir
                or entry.get("status") != "completed"):
                raise ValueError("Launcher result is not a completed prepared review")
            review = runner.read_object(Path(run_dir) / "context.json")
            from ..config import load_profile
            selected = load_profile(settings)
            expected_outputs = [item["final"] for item in runner.output_layout(
                settings, review_date, paths.state, selected)]
            if (review.get("date") != review_date or review.get("run_id") != entry.get("run_id")
                or entry.get("profile_digest") != (selected["digest"] if selected else None)
                or entry.get("review_configuration") != runner.review_configuration(paths, settings)
                or entry.get("results_root") != settings["results_root"]
                or entry.get("outputs") != expected_outputs
                or entry.get("window") != review.get("window")
                or not all(Path(name).is_file() for name in expected_outputs)):
                raise ValueError("Launcher completion no longer matches this configuration")
            cutoff = context.get("snapshot_end")
            if cutoff is not None:
                requested = runner.snapshot_window(review_date, settings["day_start_hour"],
                                                    datetime.fromisoformat(cutoff))[1]
                if datetime.fromisoformat(entry["window"]["end"]) != requested:
                    raise ValueError("Launcher completion snapshot mismatch")
            elif context["date"] is None and not entry.get("closed_day"):
                raise ValueError("Launcher requires a closed day without an explicit snapshot")
        elif status == "empty":
            if ticket.get("status") != "empty" or ticket.get("run_dir") != run_dir or context["allow_empty"]:
                raise ValueError("Unverified empty launcher result")
            directory = Path(run_dir).resolve()
            directory.relative_to((paths.state / "runs").resolve())
            manifest = runner.read_object(directory / "manifest.json")
            review = runner.read_object(directory / "context.json")
            enabled = {name for name, spec in settings["sources"].items() if spec.get("enabled", True)}
            if (manifest["window"]["date"] != review_date
                or set(manifest["sources"]) != enabled
                or review.get("review_configuration") != runner.review_configuration(paths, settings)
                or review.get("run_id") != directory.name
                or manifest.get("run_id") != directory.name
                or any(item["entries"] or (item["required"] and item["status"] == "unavailable")
                       for item in manifest["sources"].values())):
                raise ValueError("Empty result has evidence or blocked required input")
        else:
            raise ValueError(f"Launcher did not complete {review_date}: {status}")
    return results


def automate(paths, settings, *, review_date=None, max_days=7, snapshot_end=None, allow_empty=False):
    """Start one Agent. It owns the common prepare, review and finish workflow."""
    from .. import config, runner
    backend = validate_settings(settings["codex"])
    if not 1 <= max_days <= 31:
        raise ValueError("max_days must be from 1 to 31")
    if not review_date and (snapshot_end is not None or allow_empty):
        raise ValueError("snapshot-end and allow-empty require --date")
    if snapshot_end is not None:
        runner.snapshot_window(review_date, settings["day_start_hour"], snapshot_end)
    dates = invocation_dates(settings, review_date, max_days)
    write_paths = writable_roots(paths, settings, dates)
    invocation_id = uuid.uuid4().hex
    launch_dir = paths.state / "launches" / invocation_id
    launch_dir.mkdir(parents=True, mode=0o700)
    (launch_dir / "logs").mkdir(mode=0o700)
    context = {"invocation_id": invocation_id, "checkout": str(runner.REPO),
               "python_executable": sys.executable, "config": str(paths.config / "config.json"),
               "date": review_date, "max_days": None if review_date else max_days,
               "dates": dates, "snapshot_end": snapshot_end.isoformat() if snapshot_end else None,
               "allow_empty": allow_empty, "tickets_path": str(launch_dir / "tickets.json"),
               "receipt_path": str(launch_dir / "completion.json"),
               "receipt_example": {"invocation_id": invocation_id,
                                   "results": [{"date": item, "status": "completed", "run_dir": "<run_dir>"}
                                               for item in dates]}}
    config.write_json(launch_dir / "context.json", context)
    prompt = ("<!-- my-big-brother:analysis -->\n"
              "Perform the shared unattended review workflow in the current Agent session.\n"
              f"Task: {runner.REPO / 'tasks/daily-review/AUTOMATION.md'}\n"
              f"Launch context: {launch_dir / 'context.json'}\n"
              "Read that task and context, then invoke the common CLI yourself.\n"
              "Do not invoke another startup entry. Do not modify configuration or the checkout.\n")
    (launch_dir / "prompt.md").write_text(prompt, encoding="utf-8")
    environment = dict(os.environ)
    environment.update(PYTHONPATH=str(runner.REPO), PYTHONDONTWRITEBYTECODE="1")
    runner.state(launch_dir, "running", invocation_id=invocation_id)
    try:
        launch(backend, launch_dir, prompt, write_paths=write_paths, environment=environment)
        results = validate_launch_receipt(paths, settings, launch_dir, context)
    except BaseException as error:
        runner.state(launch_dir, "failed", invocation_id=invocation_id, error=str(error))
        raise
    runner.state(launch_dir, "completed", invocation_id=invocation_id)
    return {"status": "completed", "launch_dir": str(launch_dir), "results": results}


def main(argv=None):
    from .. import config
    from ..paths import discover
    parser = argparse.ArgumentParser(prog="python -m my_big_brother.analyzers.codex")
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--date")
    selector.add_argument("--max-days", type=int, default=7)
    parser.add_argument("--snapshot-end")
    parser.add_argument("--allow-empty", action="store_true")
    args = parser.parse_args(argv)
    try:
        paths = discover()
        cutoff = datetime.fromisoformat(args.snapshot_end.replace("Z", "+00:00")) if args.snapshot_end else None
        result = automate(paths, config.load(paths), review_date=args.date, max_days=args.max_days,
                          snapshot_end=cutoff, allow_empty=args.allow_empty)
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
