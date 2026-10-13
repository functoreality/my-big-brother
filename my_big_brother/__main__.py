"""Command-line entry, shared by users, installing Agents and schedulers."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import config, runner
from .paths import discover, raw_logs_root


def parser():
    result = argparse.ArgumentParser(prog="python -m my_big_brother")
    result.add_argument("--version", action="version", version=__version__)
    commands = result.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Create missing configuration, preserving existing settings")
    init.add_argument("--sources", help="Comma-separated inputs: codex,opencode,bash")
    init.add_argument("--results-root")
    init.add_argument("--raw-logs-root")
    commands.add_parser("paths", help="Show resolved paths without changing them")
    commands.add_parser("doctor", help="Check configuration and installed inputs/analyzer")
    for name in ("prepare", "analyze"):
        command = commands.add_parser(name)
        command.add_argument("--date", help="Review date YYYY-MM-DD, default last closed logical day")
        if name == "analyze":
            command.add_argument("--allow-empty", action="store_true", help="Explicitly analyze a day with no evidence")
    finish = commands.add_parser("finish", help="Validate and publish a review from the current Agent")
    finish.add_argument("--run-dir", required=True)
    due = commands.add_parser("due", help="Analyze missing completed days with evidence")
    due.add_argument("--max-days", type=int, default=7)
    return result


def resolved(paths, settings=None):
    settings = settings or config.defaults(paths)
    return {"config": str(paths.config / "config.json"),
            "raw_logs_path_file": str(paths.config / "raw-logs-path.txt"),
            "raw_logs": str(raw_logs_root(paths)), "results": settings["results_root"],
            "state": str(paths.state), "checkout": str(runner.REPO)}


def main(argv=None):
    args = parser().parse_args(argv)
    paths = discover()
    try:
        if args.command == "init":
            names = args.sources.split(",") if args.sources else None
            if names is not None and (not names or set(names) - set(config.SOURCES)):
                raise ValueError("sources must be a comma-separated subset of codex,opencode,bash")
            settings = config.initialize(paths, sources=names, results_root=args.results_root,
                                         raw_root=args.raw_logs_root)
            value = resolved(paths, settings)
        elif args.command == "paths":
            settings = config.load(paths) if (paths.config / "config.json").exists() else None
            value = resolved(paths, settings)
        else:
            settings = config.load(paths)
            if args.command == "doctor":
                native = {name: spec["path"] for name, spec in settings["sources"].items()
                          if name != "bash" and spec.get("enabled", True)}
                bash_enabled = "bash" in settings["sources"] and settings["sources"]["bash"].get("enabled", True)
                native["bash"] = str(raw_logs_root(paths)) if bash_enabled else None
                executable = shutil.which(settings["codex"]["executable"])
                value = {"paths": resolved(paths, settings), "python": sys.version.split()[0],
                         "analyzer_executable": executable,
                         "sources": {name: {"path": path, "exists": Path(path).exists()}
                                     for name, path in native.items() if path is not None},
                         "note": "Source presence does not verify supported contents or Codex login. Run prepare, then analyze."}
                print(json.dumps(value, indent=2, ensure_ascii=False))
                return 0 if executable else 1
            elif args.command == "prepare":
                review_date = args.date or runner.latest_closed_date(settings["day_start_hour"])
                with runner.lock(paths, review_date):
                    value = runner.prepare_run(paths, settings, review_date)
            elif args.command == "analyze":
                value = runner.analyze(paths, settings,
                                       args.date or runner.latest_closed_date(settings["day_start_hour"]),
                                       allow_empty=args.allow_empty)
            elif args.command == "finish":
                context = runner.read_object(Path(args.run_dir) / "context.json")
                with runner.lock(paths, context["date"]):
                    value = runner.finish_run(paths, settings, args.run_dir)
            else:
                value = runner.due(paths, settings, args.max_days)
        print(json.dumps(value, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(f"my-big-brother: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("my-big-brother: review cancelled, diagnostics preserved", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
