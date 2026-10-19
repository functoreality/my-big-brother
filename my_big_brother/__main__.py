"""Command-line entry, shared by users, installing Agents and schedulers."""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import __version__
from . import config, runner
from .paths import discover


def parser():
    result = argparse.ArgumentParser(prog="python -m my_big_brother")
    result.add_argument("--version", action="version", version=__version__)
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create missing configuration, preserving existing settings")
    init.add_argument("--sources", help="Comma-separated inputs: " + ",".join(config.SOURCES))
    init.add_argument("--results-root")
    init.add_argument("--data-root")
    init.add_argument("--day-start-hour", type=int, default=0)
    capture = commands.add_parser("capture-path", help="Allocate a calendar-date source directory")
    capture.add_argument("--source", required=True, choices=('bash', 'vim', 'screenshots'))
    capture.add_argument("--timestamp")
    screenshot = commands.add_parser("record-screenshot", help="Store an existing capture, without taking screenshots")
    screenshot.add_argument("--image", required=True)
    screenshot.add_argument("--timestamp", help="Capture time as ISO timestamp with offset, default current time, not file mtime")
    failure = commands.add_parser("log-startup-error", help="Append a diagnostic inside the previous closed day")
    failure.add_argument("--message", required=True)
    commands.add_parser("paths", help="Show resolved paths without changing them")
    commands.add_parser("doctor", help="Check configuration and input paths")
    for name in ("prepare", "analyze"):
        command = commands.add_parser(name)
        command.add_argument("--date", help="Review date YYYY-MM-DD, default last closed logical day")
        command.add_argument("--snapshot-end", help="Optional fixed ISO snapshot cutoff with UTC offset")
        if name == "analyze":
            command.add_argument("--allow-empty", action="store_true", help="Explicitly analyze a day with no evidence")
            command.add_argument("--skip-completed", action="store_true", help="Skip a matching completed daily review")
    finish = commands.add_parser("finish", help="Validate and publish a review from the current Agent")
    finish.add_argument("--run-dir", required=True)
    begin = commands.add_parser("begin-automation", help="Plan automation inside the current Agent")
    begin.add_argument("--launch-dir", required=True)
    begin.add_argument("--dates", nargs="*", help="Explicit oldest-first dates selected by a local task, including an empty list")
    complete = commands.add_parser("complete-automation", help="Verify automation completed by the current Agent")
    complete.add_argument("--launch-dir", required=True)
    commands.add_parser("due", help="Prepare the previous closed daily review for the current Agent")
    commands.add_parser("plan-due", help="List the previous closed review date without preparing evidence")
    return result


def resolved(paths, settings=None):
    settings = settings or config.defaults(paths)
    profile = config.load_profile(settings)
    return {"config": str(paths.config / "config.json"),
            "local_profile": profile["path"] if profile else None,
            "output_overrides": profile["output_paths"] if profile else {},
            "raw_logs": str(paths.raw_logs), "memory": str(paths.memory),
            "results": settings["results_root"],
            "checkout": str(runner.REPO)}


def main(argv=None):
    args = parser().parse_args(argv)
    paths = discover()
    try:
        if args.command == "init":
            names = args.sources.split(",") if args.sources else None
            if names is not None and (not names or set(names) - set(config.SOURCES)):
                raise ValueError("sources must be a comma-separated subset of " + ",".join(config.SOURCES))
            settings = config.initialize(paths, sources=names, results_root=args.results_root,
                                         data_root=args.data_root,
                                         day_start_hour=args.day_start_hour)
            value = resolved(paths, settings)
        elif args.command == "paths":
            settings = config.load(paths) if (paths.config / "config.json").exists() else None
            value = resolved(paths, settings)
        elif args.command in ('capture-path', 'record-screenshot'):
            from . import capture
            if args.command == 'capture-path':
                value = capture.directory(paths, args.source, args.timestamp)
            else:
                value = capture.screenshot(paths, args.image, args.timestamp)
        else:
            settings = config.load(paths)
            if args.command == "doctor":
                native = {name: spec.get("path") or str(paths.raw_logs)
                          for name, spec in settings["sources"].items() if spec.get("enabled", True)}
                value = {"paths": resolved(paths, settings), "python": sys.version.split()[0],
                         "analyzer": settings["analyzer"],
                         "sources": {name: {"path": path, "exists": Path(path).exists()}
                                     for name, path in native.items() if path is not None},
                         "warnings": [f"{name}: source path does not exist: {path}"
                                      for name, path in native.items() if not Path(path).exists()],
                         "note": "Path existence does not verify readable history, recorder installation, or an Analyzer. "
                                 "Run analyze and inspect its manifest. Exit 0 only validates configuration."}
                if not native:
                    value["warnings"].append("No input sources are enabled. Configure a readable source before scheduling.")
                for name in native:
                    spec = settings["sources"][name]
                    if "reader" in spec:
                        exists = Path(spec["reader"]).is_file()
                        value["sources"][name]["reader"] = {"path": spec["reader"], "exists": exists}
                        if not exists:
                            value["warnings"].append(f"{name}: reader file does not exist: {spec['reader']}")
                if "bash" in native and "reader" not in settings["sources"]["bash"]:
                    present = any(path.is_file() for path in Path(native["bash"]).glob("????-??-??/bash/*.jsonl"))
                    value["sources"]["bash"]["records_present"] = present
                    if not present:
                        value["warnings"].append("bash: no session JSONL files found. Root existence does not verify recording.")
                print(json.dumps(value, indent=2, ensure_ascii=False))
                return 0
            elif args.command == 'log-startup-error':
                directory = paths.layout.ensure_day(runner.latest_closed_date(settings['day_start_hour']))
                with (directory / 'scheduler.log').open('a', encoding='utf-8') as stream:
                    stream.write(datetime.now().astimezone().isoformat() + ' ' + args.message + '\n')
                value = {'status': 'recorded', 'path': str(directory / 'scheduler.log')}
            elif args.command in {"begin-automation", "complete-automation"}:
                from . import automation
                if args.command == "begin-automation":
                    value = automation.begin(paths, settings, args.launch_dir, dates=args.dates)
                else:
                    value = automation.complete(paths, settings, args.launch_dir)
            elif args.command == "prepare":
                review_date = args.date or runner.latest_closed_date(settings["day_start_hour"])
                with runner.lock(paths, review_date):
                    cutoff = datetime.fromisoformat(args.snapshot_end.replace("Z", "+00:00")) if args.snapshot_end else None
                    value = runner.prepare_run(paths, settings, review_date, snapshot_end=cutoff)
            elif args.command == "analyze":
                value = runner.analyze(paths, settings,
                                       args.date or runner.latest_closed_date(settings["day_start_hour"]),
                                       allow_empty=args.allow_empty,
                                       skip_completed=args.skip_completed,
                                       snapshot_end=datetime.fromisoformat(args.snapshot_end.replace("Z", "+00:00"))
                                       if args.snapshot_end else None)
            elif args.command == "plan-due":
                from . import automation
                value = {"dates": automation.invocation_dates(settings, None)}
            elif args.command == "finish":
                context = runner.read_object(Path(args.run_dir) / "context.json")
                with runner.lock(paths, context["date"]):
                    value = runner.finish_run(paths, settings, args.run_dir)
            else:
                value = runner.due(paths, settings)
        print(json.dumps(value, indent=2, ensure_ascii=False))
        if args.command in ("prepare", "analyze") and value.get("status") == "blocked":
            return 1
        if args.command == "due" and any(item.get("status") == "blocked" for item in value):
            return 1
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(f"my-big-brother: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("my-big-brother: review cancelled, diagnostics preserved", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
