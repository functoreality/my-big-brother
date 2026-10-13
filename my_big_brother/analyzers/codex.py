"""Launch the installed Codex CLI without changing its authentication."""

import json
import os
import signal
import shutil
import subprocess
from pathlib import Path


def command(settings, run_dir):
    executable = shutil.which(settings["executable"])
    if executable is None:
        raise ValueError("Codex executable not found. Install it and log in, then run doctor.")
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
    args.append("-")
    return args


def launch(settings, run_dir, prompt):
    args = command(settings, run_dir)
    (run_dir / "logs" / "command.json").write_text(
        json.dumps(args, indent=2) + "\n", encoding="utf-8")
    with (run_dir / "logs" / "stdout.log").open("w", encoding="utf-8") as out:
        with (run_dir / "logs" / "stderr.log").open("w", encoding="utf-8") as err:
            process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=out, stderr=err,
                                       start_new_session=os.name != "nt")
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
