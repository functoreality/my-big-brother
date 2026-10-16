"""The outer launcher starts one Agent, which drives every common phase."""

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from my_big_brother import automation, config, runner
from my_big_brother.analyzers import codex
from my_big_brother.paths import Paths


DAY = "2020-01-15"


class AutomationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.paths = Paths(self.root / "config", self.root / "data")
        self.settings = config.initialize(self.paths, sources=["bash"])
        self.settings["analyzer"] = "any-agent"
        self.settings["sources"]["bash"]["path"] = str(self.root / "inputs")
        self.inputs = Path(self.settings["sources"]["bash"]["path"])
        self.inputs.mkdir()
        self.task_calls = []
        self.evidence()

    def evidence(self):
        from datetime import datetime
        event = {"event": "command", "completed_at": datetime.fromisoformat(DAY + "T10:00:00").astimezone().isoformat(),
                 "command": "printf '%s' example"}
        directory = self.inputs / DAY / 'bash'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "example.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")

    def write_review(self, ticket):
        run_dir = Path(ticket["run_dir"])
        context = runner.read_object(run_dir / "context.json")
        for name, kind in context["output_kinds"].items():
            path = Path(name)
            if path.suffix == ".md":
                path.write_text("# Observed example\n", encoding="utf-8")
            else:
                config.write_json(path, {"date": context["date"],
                                         "samples" if kind == "time_estimates" else "segments": []})
        config.write_json(run_dir / "completion.json", context["completion_example"])
        return runner.finish_run(self.paths, self.settings, run_dir)

    def current_agent(self, settings, launch_dir, prompt, *, write_paths=(), environment=None):
        self.task_calls.append((settings, launch_dir, prompt, write_paths, environment))
        context = automation.begin(self.paths, self.settings, launch_dir)
        if context["date"]:
            from datetime import datetime
            cutoff = datetime.fromisoformat(context["snapshot_end"]) if context["snapshot_end"] else None
            tickets = [runner.analyze(self.paths, self.settings, context["date"],
                                      snapshot_end=cutoff, allow_empty=context["allow_empty"])]
        else:
            tickets = runner.due(self.paths, self.settings)
        config.write_json(Path(context["tickets_path"]), tickets)
        results = []
        for ticket in tickets:
            if ticket["status"] == "prepared":
                result = self.write_review(ticket)
                if result["status"] == "actions-pending":
                    actions = Path(result["action_dir"])
                    action_context = runner.read_object(actions / "context.json")
                    config.write_json(actions / "action_receipt.json", action_context["action_receipt_example"])
                    result = runner.finish_run(self.paths, self.settings, result["run_dir"])
            else:
                result = ticket
            results.append({key: result[key] for key in ("date", "status", "run_dir")})
        config.write_json(Path(context["receipt_path"]), {"invocation_id": context["invocation_id"],
                                                          "results": results})
        automation.complete(self.paths, self.settings, launch_dir)

    def automate(self, **kwargs):
        with patch.object(codex, "launch", side_effect=self.current_agent) as launch:
            result = codex.automate(self.paths, self.settings, **kwargs)
        self.assertEqual(launch.call_count, 1)
        self.assertEqual(result["status"], "agent-exited")
        return runner.read_object(Path(result["launch_dir"]) / "automation-result.json")

    def test_one_startup_agent_drives_review_and_post_phase(self):
        task = self.root / "post.md"
        task.write_text("Complete isolated operations.\n", encoding="utf-8")
        checker = self.root / "check.py"
        checker.write_text("from pathlib import Path\nPath('checked.txt').write_text('ok')\n", encoding="utf-8")
        profile = self.root / "profile.json"
        writes = self.root / "knowledge"
        config.write_json(profile, {"post_review": {"task": str(task), "write_paths": [str(writes)],
                                                    "validation_command": [sys.executable, str(checker)]}})
        self.settings["local_profile"] = str(profile)
        result = self.automate(review_date=DAY)
        self.assertEqual(result["results"][0]["status"], "completed")
        entry = runner.day_entry(self.paths, DAY)
        self.assertEqual(entry["status"], "completed")
        self.assertTrue((Path(entry["run_dir"]) / "actions/checked.txt").is_file())
        _, launch_dir, prompt, roots, environment = self.task_calls[0]
        self.assertTrue(prompt.startswith("<!-- my-big-brother:analysis -->"))
        self.assertIn("AUTOMATION.md", prompt)
        self.assertIn(str(writes), roots)
        self.assertNotIn(str(self.paths.config), roots)
        self.assertNotIn(str(runner.REPO), roots)
        self.assertEqual(environment["PYTHONPATH"], str(runner.REPO))
        self.assertEqual(environment["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(runner.read_object(launch_dir / "state.json")["status"], "agent-exited")

    def test_scheduled_invocation_only_analyzes_previous_closed_day(self):
        older = self.paths.layout.ensure_day("2020-01-13")
        with patch.object(runner, "latest_closed_date", return_value=DAY):
            result = self.automate()
        self.assertEqual([item["date"] for item in result["results"]], [DAY])
        self.assertEqual([item["status"] for item in result["results"]], ["completed"])
        self.assertEqual(list(older.iterdir()), [])
        self.assertFalse((self.paths.raw_logs / "2020-01-14").exists())

    def test_scheduled_empty_previous_day_is_verified_without_older_catchup(self):
        with patch.object(runner, "latest_closed_date", return_value="2020-01-16"):
            result = self.automate()
        self.assertEqual([item["date"] for item in result["results"]], ["2020-01-16"])
        self.assertEqual(result["results"][0]["status"], "empty")
        self.assertFalse(runner.day_entry(self.paths, DAY))

    def test_scheduled_invocation_confirms_dated_completion(self):
        self.automate(review_date=DAY)
        with patch.object(runner, "latest_closed_date", return_value=DAY):
            result = self.automate()
        self.assertEqual(result["results"][0]["status"], "already-completed")
        record = runner.read_object(self.paths.raw_logs / DAY / "review.json")
        self.assertEqual(record["review"]["status"], "completed")

    def test_snapshot_and_explicit_empty_are_completed_by_same_agent(self):
        cutoff = runner.window(DAY, 0)[0] + timedelta(hours=12)
        result = self.automate(review_date=DAY, snapshot_end=cutoff)
        self.assertEqual(result["results"][0]["status"], "completed")
        self.assertFalse(runner.day_entry(self.paths, DAY)["closed_day"])
        other = self.automate(review_date="2020-01-14", allow_empty=True)
        self.assertEqual(other["results"][0]["status"], "completed")

    def test_agent_owned_completion_rejects_blocked_required_input(self):
        self.settings["sources"]["bash"].update(required=True, path=str(self.root / "missing"))
        with patch.object(codex, "launch", side_effect=self.current_agent) as launch:
            with self.assertRaisesRegex(ValueError, "blocked"):
                codex.automate(self.paths, self.settings, review_date=DAY)
        launch.assert_called_once()
        states = list(self.paths.raw_logs.glob("*/_launches/*/state.json"))
        self.assertEqual(runner.read_object(states[0])["status"], "failed")

    def bad_agent(self, status, *, wrong_id=False, fake_empty=False, wrong_order=False):
        def agent(settings, launch_dir, prompt, **kwargs):
            context = automation.begin(self.paths, self.settings, launch_dir)
            ticket = runner.analyze(self.paths, self.settings, DAY)
            if fake_empty:
                ticket["status"] = "empty"
            config.write_json(launch_dir / "tickets.json", [ticket])
            result = {"date": "2020-01-14" if wrong_order else DAY,
                      "status": status, "run_dir": ticket["run_dir"]}
            config.write_json(launch_dir / "completion.json", {
                "invocation_id": "wrong" if wrong_id else context["invocation_id"], "results": [result]})
            automation.complete(self.paths, self.settings, launch_dir)
        return agent

    def test_false_completion_pending_and_unverified_skip_are_rejected(self):
        for status in ("completed", "already-completed", "actions-pending", "blocked"):
            with self.subTest(status=status), patch.object(codex, "launch", side_effect=self.bad_agent(status)):
                with self.assertRaises(ValueError):
                    codex.automate(self.paths, self.settings, review_date=DAY)

    def test_empty_claim_with_actual_evidence_is_rejected(self):
        with patch.object(codex, "launch", side_effect=self.bad_agent("empty", fake_empty=True)):
            with self.assertRaisesRegex(ValueError, "evidence"):
                codex.automate(self.paths, self.settings, review_date=DAY)

    def test_wrong_invocation_or_requested_date_is_rejected(self):
        for options in ({"wrong_id": True}, {"wrong_order": True}):
            with self.subTest(options=options), patch.object(codex, "launch", side_effect=self.bad_agent("completed", **options)):
                with self.assertRaises(ValueError):
                    codex.automate(self.paths, self.settings, review_date=DAY)

    def test_nonobject_extra_receipt_rows_are_rejected(self):
        def malformed_receipt(settings, launch_dir, prompt, **kwargs):
            self.current_agent(settings, launch_dir, prompt, **kwargs)
            receipt = runner.read_object(launch_dir / "completion.json")
            receipt['results'].append(None)
            config.write_json(launch_dir / "completion.json", receipt)
            automation.complete(self.paths, self.settings, launch_dir)

        with patch.object(codex, "launch", side_effect=malformed_receipt):
            with self.assertRaisesRegex(ValueError, "requested dates"):
                codex.automate(self.paths, self.settings, review_date=DAY)

    def test_dated_output_permissions_use_static_parent_without_planning(self):
        profile = self.root / "profile.json"
        destination = self.root / "bound-reports"
        config.write_json(profile, {"output_paths": {"worklog": str(destination / "{date}" / "worklog.md")}})
        self.settings["local_profile"] = str(profile)
        result = self.automate(review_date=DAY)
        self.assertEqual(result['results'][0]['status'], 'completed')
        roots = self.task_calls[0][3]
        self.assertIn(str(destination), roots)
        self.assertNotIn(str(destination / DAY), roots)
        self.assertNotIn(str(destination / '2000-01-01'), roots)
        self.assertTrue((destination / DAY / 'worklog.md').is_file())

    def test_completed_claim_must_match_published_outputs(self):
        def incomplete_record(settings, launch_dir, prompt, **kwargs):
            self.current_agent(settings, launch_dir, prompt, **kwargs)
            entry = runner.day_entry(self.paths, DAY)
            entry["outputs"] = []
            runner.update_completion(self.paths, DAY, entry)
            automation.complete(self.paths, self.settings, launch_dir)

        with patch.object(codex, "launch", side_effect=incomplete_record):
            with self.assertRaisesRegex(ValueError, "configuration"):
                codex.automate(self.paths, self.settings, review_date=DAY)

    def test_outer_cli_selects_date_and_reports_startup_errors(self):
        cutoff = runner.window(DAY, 0)[0] + timedelta(hours=12)
        with patch("my_big_brother.paths.discover", return_value=self.paths), \
             patch.object(config, "load", return_value=self.settings), \
             patch.object(codex, "automate", return_value={"status": "completed"}) as automate, \
             patch("builtins.print"):
            self.assertEqual(codex.main(["--date", DAY, "--snapshot-end", cutoff.isoformat(), "--allow-empty"]), 0)
        self.assertEqual(automate.call_args.kwargs["review_date"], DAY)
        self.assertEqual(automate.call_args.kwargs["snapshot_end"], cutoff)
        self.assertTrue(automate.call_args.kwargs["allow_empty"])
        with patch("my_big_brother.paths.discover", return_value=self.paths), \
             patch.object(config, "load", return_value=self.settings), \
             patch.object(codex, "automate", side_effect=ValueError("fixture startup failed")), \
             patch("builtins.print") as output:
            self.assertEqual(codex.main([]), 1)
        self.assertIn("fixture startup failed", output.call_args.args[0])

    def test_agent_exit_without_business_receipt_reports_only_process_exit(self):
        with patch.object(codex, "launch") as launch:
            result = codex.automate(self.paths, self.settings, review_date=DAY)
        launch.assert_called_once()
        self.assertEqual(result["status"], "agent-exited")
        self.assertNotIn("results", result)
        self.assertFalse((Path(result["launch_dir"]) / "automation-result.json").exists())
        with self.assertRaises(OSError):
            automation.complete(self.paths, self.settings, result["launch_dir"])

    def test_timeout_preserves_startup_diagnostics(self):
        with patch.object(codex, "launch", side_effect=subprocess.TimeoutExpired("fixture", 1)):
            with self.assertRaises(subprocess.TimeoutExpired):
                codex.automate(self.paths, self.settings, review_date=DAY)
        launch_dir = next(self.paths.raw_logs.glob("*/_launches/*"))
        self.assertTrue((launch_dir / "context.json").is_file())
        self.assertEqual(runner.read_object(launch_dir / "state.json")["status"], "failed")

    def test_backend_options_are_validated_only_at_outer_startup(self):
        for backend in ({"timeout_seconds": 0}, {"executable": ""}, {"model": False}, {"unknown": True}, None):
            self.settings["codex"] = backend
            with self.subTest(backend=backend), patch.object(codex, "launch") as launch:
                with self.assertRaises(ValueError):
                    codex.automate(self.paths, self.settings, review_date=DAY)
            launch.assert_not_called()

    def test_launch_snapshot_and_empty_flags_require_an_explicit_date(self):
        for kwargs in ({"allow_empty": True}, {"snapshot_end": runner.window(DAY, 0)[0]}):
            with self.subTest(kwargs=kwargs), patch.object(codex, "launch") as launch:
                with self.assertRaises(ValueError):
                    codex.automate(self.paths, self.settings, **kwargs)
            launch.assert_not_called()

    def test_writable_roots_cannot_include_configuration_checkout_or_source_histories(self):
        for root in (self.paths.config, self.paths.config / "subfolder", runner.REPO,
                     runner.REPO / "subfolder", self.paths.data, self.inputs):
            self.settings["results_root"] = str(root)
            with self.subTest(root=root), patch.object(codex, "launch") as launch:
                with self.assertRaisesRegex(ValueError, "protected"):
                    codex.automate(self.paths, self.settings, review_date=DAY)
            launch.assert_not_called()

    def test_startup_never_plans_prepares_finishes_or_checks_business_results(self):
        from contextlib import ExitStack
        with ExitStack() as stack:
            for module, names in ((automation, ("invocation_dates", "begin", "complete", "validate_receipt")),
                                  (runner, ("latest_closed_date", "snapshot_window", "prepare_run", "analyze", "due", "finish_run"))):
                for name in names:
                    stack.enter_context(patch.object(module, name, side_effect=AssertionError("Startup performed " + name)))
            launch = stack.enter_context(patch.object(codex, "launch"))
            for request in ({"review_date": DAY}, {}):
                value = codex.automate(self.paths, self.settings, **request)
                self.assertEqual(value["status"], "agent-exited")
                context = runner.read_object(Path(value["launch_dir"]) / "context.json")
                self.assertNotIn("dates", context)
                self.assertNotIn("tickets_path", context)
                self.assertFalse((Path(value["launch_dir"]) / "automation-context.json").exists())
            self.assertEqual(launch.call_count, 2)

    def test_agent_date_override_must_match_single_selected_day(self):
        for review_date in (None, "2020-01-13"):
            selected = review_date or DAY
            for dates in ([selected], [], ["2020-01-14", DAY], ["2020-01-12"]):
                def current(settings, launch_dir, prompt, **kwargs):
                    context = automation.begin(self.paths, self.settings, launch_dir, dates=dates)
                    self.assertEqual(context["dates"], [selected])
                with self.subTest(review_date=review_date, dates=dates), \
                     patch.object(runner, "latest_closed_date", return_value=DAY), \
                     patch.object(codex, "launch", side_effect=current) as launch:
                    if dates == [selected]:
                        value = codex.automate(self.paths, self.settings, review_date=review_date)
                        self.assertEqual(value["status"], "agent-exited")
                    else:
                        with self.assertRaises(ValueError):
                            codex.automate(self.paths, self.settings, review_date=review_date)
                launch.assert_called_once()

    def test_removed_catchup_option_is_rejected_before_launch(self):
        with patch.object(codex, "launch") as launch, patch("sys.stderr"):
            with self.assertRaises(SystemExit) as rejected:
                codex.main(["--max-days", "2"])
        self.assertEqual(rejected.exception.code, 2)
        launch.assert_not_called()

    def test_custom_task_and_explicit_import_permissions_are_passed_without_importing(self):
        task = self.root / "private-task.md"
        task.write_text("Import evidence within this Agent session.\n", encoding="utf-8")
        with patch.object(codex, "launch") as launch:
            value = codex.automate(self.paths, self.settings, task=str(task), write_dirs=[str(self.inputs)])
        launch.assert_called_once()
        self.assertIn(str(self.inputs), launch.call_args.kwargs["write_paths"])
        self.assertIn(str(task), launch.call_args.args[2])
        context = runner.read_object(Path(value["launch_dir"]) / "context.json")
        self.assertEqual(context["extra_write_paths"], [str(self.inputs)])
        self.assertEqual(list(self.inputs.rglob("*.jsonl")),
                         [self.inputs / DAY / "bash" / "example.jsonl"])
        for options in ({"task": "relative.md"}, {"task": str(self.root / "missing.md")},
                        {"write_dirs": ["relative"]}, {"write_dirs": [str(self.paths.config)]}):
            with self.subTest(options=options), patch.object(codex, "launch") as rejected:
                with self.assertRaises(ValueError):
                    codex.automate(self.paths, self.settings, **options)
            rejected.assert_not_called()

    def test_generic_automation_cli_has_no_agent_import(self):
        from my_big_brother import __main__ as cli
        with patch.object(cli, "discover", return_value=self.paths), \
             patch.object(config, "load", return_value=self.settings), \
             patch.object(codex, "launch") as launch, patch("builtins.print"):
            startup = codex.automate(self.paths, self.settings, review_date=DAY)
            launch.assert_called_once()
            launch.reset_mock()
            self.assertEqual(cli.main(["begin-automation", "--launch-dir", startup["launch_dir"],
                                       "--dates", DAY]), 0)
            directory = Path(startup["launch_dir"])
            context = runner.read_object(directory / "automation-context.json")
            ticket = runner.analyze(self.paths, self.settings, DAY)
            result = self.write_review(ticket)
            config.write_json(directory / "tickets.json", [ticket])
            config.write_json(directory / "completion.json", {
                "invocation_id": context["invocation_id"],
                "results": [{key: result[key] for key in ("date", "status", "run_dir")}],
            })
            self.assertEqual(cli.main(["complete-automation", "--launch-dir", startup["launch_dir"]]), 0)
            launch.assert_not_called()
        self.assertEqual(runner.read_object(directory / "automation-result.json")["status"], "completed")

    def test_source_collection_cannot_spawn_an_agent(self):
        with patch.object(codex, "launch", side_effect=AssertionError("nested launch")):
            ticket = runner.analyze(self.paths, self.settings, DAY)
            self.assertEqual(ticket["status"], "prepared")
            self.assertEqual(self.write_review(ticket)["status"], "completed")


if __name__ == "__main__":
    unittest.main()
