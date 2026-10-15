import json
import contextlib
import io
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from my_big_brother import config, runner
from my_big_brother import __main__ as cli
from my_big_brother.paths import Paths, discover
from my_big_brother.analyzers import codex


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.paths = Paths(self.root / "config", self.root / "data")
        self.settings = config.initialize(self.paths, sources=["codex"])
        self.sessions = self.root / "sessions"
        self.sessions.mkdir()
        self.settings["sources"]["codex"]["path"] = str(self.sessions)

    def evidence(self, day="2020-01-15", content="Review the import parser"):
        events = [{"type": "session_meta", "payload": {"thread_source": "user"}},
                  {"type": "event_msg", "timestamp": datetime.fromisoformat(day + "T10:00:00").astimezone().isoformat(),
                   "payload": {"type": "user_message", "message": content}}]
        (self.sessions / (day + ".jsonl")).write_text(
            "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")

    def staged_review(self, day="2020-01-15"):
        prepared = runner.prepare_run(self.paths, self.settings, day)
        run = Path(prepared["run_dir"])
        context = runner.read_object(run / "context.json")
        for name in context["output_paths"]:
            path = Path(name)
            if path.suffix == ".md":
                path.write_text(f"# {day}\n\nObserved parser review.\n", encoding="utf-8")
            else:
                key = "samples" if path.name == "time-estimates.json" else "segments"
                config.write_json(path, {"date": day, key: []})
        config.write_json(run / "completion.json", context["completion_example"])
        return run, context

    def test_platform_discovery_and_relative_xdg_fallback(self):
        home = self.root / "home"
        linux = discover(system="linux", home=home, environ={"XDG_CONFIG_HOME": "relative"})
        self.assertEqual(linux.config, home / ".config" / "my-big-brother")
        mac = discover(system="darwin", home=home, environ={})
        self.assertEqual(mac.config, home / "Library/Application Support/my-big-brother/configs")
        win = discover(system="win32", home=home, environ={"LOCALAPPDATA": str(self.root / "local")})
        self.assertEqual(win.data, self.root / "local/my-big-brother/data")

    def test_required_source_blocks_unattended_cli_with_failure_exit(self):
        blocked = {'status': 'blocked', 'blocked_sources': ['vim']}
        with patch.object(cli, 'discover', return_value=self.paths), \
             patch.object(cli.config, 'load', return_value=self.settings), \
             patch.object(cli.runner, 'analyze', return_value=blocked), \
             patch.object(cli.runner, 'due', return_value=[{'date': '2020-01-15', **blocked}]), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['analyze', '--date', '2020-01-15']), 1)
            self.assertEqual(cli.main(['due']), 1)

    def test_shared_storage_supports_spaces_and_rejects_missing_configuration(self):
        self.assertEqual(self.paths.daily, self.paths.layout.daily)
        (self.paths.config / "storage.json").rename(self.paths.config / "saved-storage.json")
        with self.assertRaisesRegex(ValueError, 'not initialized'):
            self.paths.daily

    def test_init_preserves_existing_settings_and_storage(self):
        self.settings["language"] = "zh"
        config.write_json(self.paths.config / "config.json", self.settings)
        storage = (self.paths.config / "storage.json").read_bytes()
        initialized = config.initialize(self.paths)
        self.assertEqual(initialized["language"], "zh")
        self.assertEqual((self.paths.config / "storage.json").read_bytes(), storage)
        with self.assertRaises(ValueError):
            config.initialize(self.paths, results_root=str(self.root / "other"))

    def test_invalid_config_is_reported(self):
        for field, value in (("day_start_hour", True), ("day_start_hour", 24),
                             ("results_root", "relative"), ("outputs", ["typo"]),
                             ("analyzer", " "), ("unexpected", True)):
            settings = dict(self.settings)
            settings[field] = value
            config.write_json(self.paths.config / "config.json", settings)
            with self.assertRaises(ValueError):
                config.load(self.paths)

    def test_prepare_materializes_excerpts_without_publishing(self):
        self.evidence()
        prepared = runner.prepare_run(self.paths, self.settings, "2020-01-15")
        self.assertEqual(prepared["status"], "prepared")
        manifest = runner.read_object(Path(prepared["run_dir"]) / "manifest.json")
        source = manifest["sources"]["codex"]
        self.assertEqual(source["entries"], 1)
        row = json.loads(Path(source["index"]).read_text())
        self.assertEqual(Path(row["excerpt"]).read_text(), "Review the import parser")
        self.assertNotIn("content", row)
        self.assertEqual(list(Path(self.settings["results_root"]).rglob("*.md")), [])

    def test_missing_coverage_or_output_does_not_publish(self):
        self.evidence()
        run, context = self.staged_review()
        receipt = context["completion_example"]
        receipt["sources"]["codex"]["covered"] = False
        config.write_json(run / "completion.json", receipt)
        with self.assertRaisesRegex(ValueError, "coverage"):
            runner.finish_run(self.paths, self.settings, run)
        self.assertFalse(Path(context["final_output_paths"][0]).exists())

    def test_finish_publishes_and_records_completed_day(self):
        self.evidence()
        run, context = self.staged_review()
        finished = runner.finish_run(self.paths, self.settings, run)
        self.assertEqual(finished["status"], "completed")
        self.assertTrue(all(Path(x).is_file() for x in context["final_output_paths"]))
        self.assertTrue(runner.day_entry(self.paths, "2020-01-15")["closed_day"])

    def test_user_edit_after_prepare_prevents_overwrite(self):
        self.evidence()
        run, context = self.staged_review()
        final = Path(context["final_output_paths"][0])
        final.parent.mkdir(parents=True, exist_ok=True)
        final.write_text("User correction\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "changed after prepare"):
            runner.finish_run(self.paths, self.settings, run)
        self.assertEqual(final.read_text(), "User correction\n")
        self.assertFalse(Path(context["final_output_paths"][-1]).exists())

    def test_existing_outputs_are_staged_for_preserving_user_notes(self):
        self.evidence()
        run, context = self.staged_review()
        runner.finish_run(self.paths, self.settings, run)
        final = Path(context["final_output_paths"][0])
        final.write_text("Keep my manual note\n", encoding="utf-8")
        new = runner.prepare_run(self.paths, self.settings, "2020-01-15")
        new_context = runner.read_object(Path(new["run_dir"]) / "context.json")
        self.assertEqual(Path(new_context["output_paths"][0]).read_text(), "Keep my manual note\n")

    def test_point_timeline_allowed_but_reverse_or_naive_rejected(self):
        path = self.root / "time-use/data/2020-01-15.json"
        row = {"start": "2020-01-15T10:00:00+00:00", "end": "2020-01-15T10:00:00+00:00",
               "activity": "Message submission", "confidence": "high", "human_attention": "unknown"}
        config.write_json(path, {"date": "2020-01-15", "segments": [row]})
        runner.validate_output(path, "2020-01-15")
        for value in ("2020-01-15T09:59:59+00:00", "2020-01-15T10:00:00"):
            row["end"] = value
            config.write_json(path, {"date": "2020-01-15", "segments": [row]})
            with self.assertRaises(ValueError):
                runner.validate_output(path, "2020-01-15")

    def test_empty_day_does_not_launch_analyzer(self):
        with patch("my_big_brother.analyzers.codex.launch") as launch:
            result = runner.analyze(self.paths, self.settings, "2020-01-15")
        self.assertEqual(result["status"], "empty")
        launch.assert_not_called()

    def test_prepare_ticket_keeps_stable_results_until_agent_completes(self):
        self.evidence()
        final = Path(self.settings["results_root"]) / "records/2020-01-15/worklog.md"
        final.parent.mkdir(parents=True, exist_ok=True)
        final.write_text("Existing report\n", encoding="utf-8")
        with patch("my_big_brother.analyzers.codex.launch") as launch:
            result = runner.analyze(self.paths, self.settings, "2020-01-15")
        launch.assert_not_called()
        self.assertEqual(final.read_text(), "Existing report\n")
        self.assertEqual(result["status"], "prepared")
        run = Path(result["run_dir"])
        self.assertEqual(runner.read_object(run / "state.json")["status"], "prepared")
        self.assertTrue(Path(result["prompt_path"]).is_file())
        self.assertFalse((run / "completion.json").exists())

    def test_custom_agent_configuration_and_doctor_need_no_codex(self):
        self.settings["analyzer"] = "a-user-selected-agent"
        self.settings["codex"] = {"unused_other_launcher_option": True}
        config.write_json(self.paths.config / "config.json", self.settings)
        loaded = config.load(self.paths)
        self.assertEqual(loaded["analyzer"], "a-user-selected-agent")
        with patch.object(cli, "discover", return_value=self.paths), \
             patch("shutil.which", return_value=None), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["doctor"]), 0)
        self.evidence()
        result = runner.analyze(self.paths, loaded, "2020-01-15")
        self.assertEqual(result["status"], "prepared")

    def test_due_returns_bounded_tickets_oldest_first_without_launch(self):
        self.evidence("2020-01-14")
        self.evidence("2020-01-15")
        with patch.object(runner, "latest_closed_date", return_value="2020-01-15"), \
             patch("my_big_brother.analyzers.codex.launch") as launch:
            tickets = runner.due(self.paths, self.settings, 3)
        self.assertEqual([item["date"] for item in tickets], ["2020-01-13", "2020-01-14", "2020-01-15"])
        self.assertEqual([item["status"] for item in tickets], ["empty", "prepared", "prepared"])
        launch.assert_not_called()
        for limit in (0, 32):
            with self.assertRaises(ValueError):
                runner.due(self.paths, self.settings, limit)

    def test_explicit_empty_review_produces_a_task_ticket(self):
        ticket = runner.analyze(self.paths, self.settings, "2020-01-15", allow_empty=True)
        self.assertEqual(ticket["status"], "prepared")
        self.assertTrue(ticket["allow_empty"])
        self.assertEqual(ticket["entries"], 0)

    def test_successful_due_is_skipped_without_account_usage(self):
        self.evidence()
        run, _ = self.staged_review()
        runner.finish_run(self.paths, self.settings, run)
        with patch.object(runner, "latest_closed_date", return_value="2020-01-15"):
            with patch("my_big_brother.analyzers.codex.launch") as launch:
                results = runner.due(self.paths, self.settings, 1)
        self.assertEqual(results[0]["status"], "already-completed")
        launch.assert_not_called()

    def test_due_rechecks_completion_after_date_lock(self):
        with patch.object(runner, "latest_closed_date", return_value="2020-01-15"):
            with patch.object(runner, "completed", side_effect=[False, True]) as check:
                with patch("my_big_brother.analyzers.codex.launch") as launch:
                    results = runner.due(self.paths, self.settings, 1)
        self.assertEqual(results[0]["status"], "already-completed")
        self.assertEqual(check.call_count, 2)
        launch.assert_not_called()

    @unittest.skipIf(os.name == "nt", "POSIX lock concurrency is executed on Linux")
    def test_two_dates_finish_without_losing_shared_ledger(self):
        self.evidence("2020-01-15")
        self.evidence("2020-01-16")
        first, _ = self.staged_review("2020-01-15")
        second, _ = self.staged_review("2020-01-16")
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda run: runner.finish_run(self.paths, self.settings, run), [first, second]))
        self.assertTrue(all(result["status"] == "completed" for result in results))
        self.assertTrue(runner.day_entry(self.paths, "2020-01-15")["closed_day"])
        self.assertTrue(runner.day_entry(self.paths, "2020-01-16")["closed_day"])

    def test_analyzer_command_keeps_model_optional_and_prompt_off_argv(self):
        with patch("shutil.which", return_value="/tools/codex"):
            args = codex.command(self.settings["codex"], self.root)
        self.assertNotIn("--model", args)
        self.assertEqual(args[-1], "-")
        self.assertIn("--ephemeral", args)
        self.assertIn("workspace-write", args)

    def test_windows_npm_wrapper_uses_node_without_a_shell(self):
        shim = self.root / "npm with spaces" / "codex.cmd"
        script = shim.parent / "node_modules/@openai/codex/bin/codex.js"
        script.parent.mkdir(parents=True)
        script.write_text("// fixture\n", encoding="utf-8")
        node = str(self.root / "node.exe")
        with patch.object(codex, "os", SimpleNamespace(name="nt")):
            with patch("shutil.which", side_effect=[str(shim), node]):
                args = codex.command(self.settings["codex"], self.root)
        self.assertEqual(args[:2], [node, str(script)])
        self.assertNotIn("cmd.exe", args)

    def test_unknown_windows_wrapper_fails_with_native_binary_hint(self):
        with patch.object(codex, "os", SimpleNamespace(name="nt")):
            with patch("shutil.which", side_effect=[str(self.root / "codex.cmd"), "/node.exe"]):
                with self.assertRaisesRegex(ValueError, "native codex.exe"):
                    codex.command(self.settings["codex"], self.root)


if __name__ == "__main__":
    unittest.main()
