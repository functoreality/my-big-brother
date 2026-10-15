"""Create isolated synthetic inputs and optionally exercise the real analyzer.

Run from the checkout: python tests/smoke.py [--run-analyzer].
The explicit analyzer option can consume the installed Codex account quota.
All configuration, evidence, and results stay in a separate temporary directory.
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DAY = "2020-01-15"


def timestamp(clock):
    return datetime.fromisoformat(DAY + "T" + clock).astimezone().isoformat()


def run(command, environment):
    result = subprocess.run([sys.executable, "-m", "my_big_brother", *command],
                            cwd=REPO, env=environment, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-analyzer", action="store_true")
    parser.add_argument("--with-post-review", action="store_true")
    parser.add_argument("--with-knowledge", action="store_true")
    args = parser.parse_args()
    if args.with_post_review and not args.run_analyzer:
        parser.error("--with-post-review requires --run-analyzer")
    if not sys.platform.startswith("linux"):
        raise SystemExit("This CLI isolation smoke harness currently requires Linux/XDG. Unit fixtures are portable.")
    root = Path(tempfile.mkdtemp(prefix="mbb-smoke-"))
    environment = dict(os.environ)
    environment["XDG_CONFIG_HOME"] = str(root / "config")
    environment["XDG_DATA_HOME"] = str(root / "data")
    paths = run(["init", "--sources", "codex,opencode,bash"], environment)
    sessions = root / "codex sessions"
    sessions.mkdir()
    events = [{"type": "session_meta", "payload": {"thread_source": "user", "source": "cli"}}]
    for clock, role, content in [
        ("10:00:00", "user", "Fix the order CSV importer: blank final lines cause an error. Use fixtures with empty, normal and trailing-blank input."),
        ("10:08:00", "assistant", "Updated import_orders.py to ignore blank trailing rows. The empty, normal and trailing-blank fixtures all pass."),
        ("10:20:00", "user", "Update the installation guide to explain required Python and how to select an input source."),
        ("10:32:00", "assistant", "Updated INSTALLATION.md with Python requirements and explicit source-selection examples. Reviewed the command snippets."),
    ]:
        payload = {"type": "message", "role": role, "id": clock,
                   "content": [{"type": "input_text" if role == "user" else "output_text", "text": content}]}
        if role == "assistant":
            payload["phase"] = "final_answer"
        events.append({"type": "response_item", "timestamp": timestamp(clock), "payload": payload})
    (sessions / "synthetic.jsonl").write_text("".join(json.dumps(x) + "\n" for x in events), encoding="utf-8")
    database = root / "opencode # fixture.db"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            CREATE TABLE session(id TEXT, parent_id TEXT);
            CREATE TABLE message(id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
            CREATE TABLE part(id TEXT, message_id TEXT, time_created INTEGER, data TEXT);
            INSERT INTO session VALUES ('release', NULL);
        """)
        for number, (role, text, clock) in enumerate([
            ("user", "Draft a release checklist for the CSV importer and documentation change.", "13:00:00"),
            ("assistant", "Created RELEASE.md with fixture validation, clean-install checks and release notes. Publishing remains pending.", "13:10:00"),
        ]):
            milliseconds = int(datetime.fromisoformat(timestamp(clock)).timestamp() * 1000)
            data = {"role": role, "finish": "stop" if role == "assistant" else None}
            connection.execute("INSERT INTO message VALUES (?, 'release', ?, ?)", (str(number), milliseconds, json.dumps(data)))
            connection.execute("INSERT INTO part VALUES (?, ?, ?, ?)",
                               ("part" + str(number), str(number), milliseconds, json.dumps({"type": "text", "text": text})))
    settings = json.loads(Path(paths["config"]).read_text(encoding="utf-8"))
    if args.with_knowledge:
        settings["outputs"].extend(["user-model", "machine-context"])
    settings["sources"]["codex"]["path"] = str(sessions)
    settings["sources"]["opencode"]["path"] = str(database)
    Path(paths["config"]).write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    bash_directory = Path(paths["daily"]) / DAY / "bash"
    bash_directory.mkdir(parents=True)
    bash = {"event": "command", "session_id": "synthetic-shell", "command": "python -m unittest",
            "command_scope": "first-simple-command", "cwd": "/synthetic/orders-project",
            "started_at": timestamp("10:07:00"), "completed_at": timestamp("10:08:00"), "exit_status": 0}
    (bash_directory / "synthetic.jsonl").write_text(json.dumps(bash) + "\n", encoding="utf-8")
    if args.with_post_review:
        rules = root / "rules"
        rules.mkdir()
        knowledge = root / "knowledge"
        knowledge.mkdir()
        marker = knowledge / "review-count.json"
        task = rules / "post-review.md"
        task.write_text("Maintain only the isolated fixture marker " + str(marker) + ".\n"
                        "If absent, write JSON {\"count\": 1}. If already present, retain it unchanged.\n"
                        "This records one completed fixture review, not a measured work duration.\n"
                        "Write the exact action receipt after the marker is correct.\n")
        validator = rules / "validate.py"
        validator.write_text("import json, pathlib, sys\n"
                             "assert json.loads(pathlib.Path(" + repr(str(marker)) + ").read_text()) == {'count': 1}\n")
        profile = rules / "profile.json"
        profile.write_text(json.dumps({"schema_version": 1, "post_review": {
            "task": str(task), "read_paths": [], "write_paths": [str(knowledge)],
            "validation_command": [sys.executable, str(validator), "{run_dir}"]}}))
        settings["local_profile"] = str(profile)
        settings["codex"]["model"] = "gpt-6.1-sol"
        Path(paths["config"]).write_text(json.dumps(settings, indent=2) + "\n")
    prepared = run(["prepare", "--date", DAY], environment)
    summary = {"fixture_root": str(root), "date": DAY, "prepare": prepared}
    if args.run_analyzer:
        print(f"Running installed Codex against synthetic evidence only. Artifacts: {root}", flush=True)
        result = subprocess.run([sys.executable, "-m", "my_big_brother.analyzers.codex",
                                 "--date", DAY], cwd=REPO, env=environment, check=True,
                                capture_output=True, text=True)
        summary["analysis"] = json.loads(result.stdout)
        summary["doctor"] = run(["doctor"], environment)
        assert summary["analysis"]["status"] == "agent-exited"
        automation = json.loads((Path(summary["analysis"]["launch_dir"]) / "automation-result.json").read_text())
        assert automation["status"] == "completed", automation
        summary["automation"] = automation
        review = automation["results"][0]
        assert review["status"] == "completed", review
        run_dir = Path(review["run_dir"])
        context = json.loads((run_dir / "context.json").read_text())
        assert len(context["final_output_paths"]) == (7 if args.with_knowledge else 5)
        for output in context["final_output_paths"]:
            assert Path(output).is_file(), output
        worklog = Path(paths["results"]) / "records" / DAY / "worklog.md"
        text = worklog.read_text(encoding="utf-8").lower()
        assert "csv" in text and "installation" in text, "Reports must describe fixture work"
        if args.with_post_review:
            assert json.loads(marker.read_text()) == {"count": 1}
            assert (run_dir / "actions/action_receipt.json").is_file()
            assert not (run_dir / "actions/logs/command.json").exists(), "Post-review must not start another Agent"
            assert len(list(Path(paths["state"]).glob("launches/*/logs/command.json"))) == 1
            summary["same_agent_post_review"] = True
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
