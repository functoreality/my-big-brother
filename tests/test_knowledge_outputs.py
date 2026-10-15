"""Portable cumulative outputs use normal staging and checked publication."""

import os
import contextlib
import io
import json
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from my_big_brother import automation, config, runner
from my_big_brother import __main__ as cli
from my_big_brother.paths import Paths
from my_big_brother.sources import SourceResult


DAY = "2020-01-15"
NEXT_DAY = "2020-01-16"


class KnowledgeOutputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.paths = Paths(self.root / "config", self.root / "data")
        self.settings = config.initialize(self.paths, sources=["bash"])
        self.settings["analyzer"] = "any-agent"
        self.settings["outputs"] += ["user-model", "machine-context"]

    def invoke_cli(self, arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(cli, "discover", return_value=self.paths), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = cli.main(arguments)
        return status, json.loads(stdout.getvalue()) if stdout.getvalue() else stderr.getvalue()

    def prepare(self, day=DAY, *, empty=False):
        rows = [] if empty else [{"content": "The user stated a project constraint.",
                                 "timestamp": day + "T10:00:00+00:00"}]
        with patch("my_big_brother.sources.bash.collect", return_value=SourceResult(rows=rows)):
            ticket = runner.prepare_run(self.paths, self.settings, day)
        directory = Path(ticket["run_dir"])
        return directory, runner.read_object(directory / "context.json")

    def drafts(self, directory, context, *, addition=""):
        for name, kind in context["output_kinds"].items():
            target = Path(name)
            if kind in config.KNOWLEDGE_KEYS:
                previous = target.read_text(encoding="utf-8") if target.exists() else "# Knowledge\n"
                target.write_text(previous + addition, encoding="utf-8")
            elif target.suffix == ".md":
                target.write_text("# Isolated review\n", encoding="utf-8")
            else:
                field = "samples" if kind == "time_estimates" else "segments"
                config.write_json(target, {"date": context["date"], field: []})
        config.write_json(directory / "completion.json", context["completion_example"])

    def knowledge_items(self, context):
        return [item for item in context["output_mapping"] if item["kind"] in config.KNOWLEDGE_KEYS]

    def profile(self, value):
        path = self.root / "profile.json"
        config.write_json(path, value)
        self.settings["local_profile"] = str(path)
        config.write_json(self.paths.config / "config.json", self.settings)
        return config.load(self.paths)

    def test_opt_in_preserves_default_outputs_and_resolves_stable_paths(self):
        defaults = config.defaults(self.paths)
        self.assertEqual(defaults["outputs"], ["worklog", "time-use", "insights", "time-estimates"])
        self.assertEqual(len(runner.output_layout(defaults, DAY, self.paths.state, None)), 5)
        config.write_json(self.paths.config / "config.json", self.settings)
        self.assertEqual(config.load(self.paths)["outputs"], list(config.OUTPUTS))
        first = runner.output_layout(self.settings, DAY, self.paths.state, None)
        second = runner.output_layout(self.settings, NEXT_DAY, self.paths.state, None)
        self.assertEqual(len(first), 7)
        expected = {"user_model": "USER-MODEL.md", "machine_context": "MACHINE-CONTEXT.md"}
        for item in first[-2:]:
            relative = expected[item["kind"]]
            self.assertEqual(item["final"], str(Path(self.settings["results_root"]) / relative))
            self.assertEqual(item["staged"], str(self.paths.state / "drafts" / relative))
        self.assertEqual([item["final"] for item in first[-2:]],
                         [item["final"] for item in second[-2:]])

    def test_knowledge_overrides_accept_stable_paths_without_custom_tasks(self):
        overrides = {"user_model": str(self.root / "existing notes" / "USER-MODEL.md"),
                     "machine_context": str(self.root / "existing notes" / "SOURCES.md")}
        self.profile({"output_paths": overrides})
        directory, context = self.prepare()
        self.assertEqual({item["kind"]: item["final"] for item in self.knowledge_items(context)}, overrides)
        self.assertIsNone(context["profile"]["post_review"])
        self.drafts(directory, context)
        runner.finish_run(self.paths, self.settings, directory)
        self.assertTrue(all(Path(name).is_file() for name in overrides.values()))

    def test_dated_overrides_still_require_date_and_reject_unknown_placeholders(self):
        for key, template in (("worklog", "stable.md"), ("user_model", "{machine}.md")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.profile({"output_paths": {key: str(self.root / template)}})

    def test_knowledge_only_review_and_unchanged_manual_history_are_valid(self):
        self.settings["outputs"] = ["user-model", "machine-context"]
        directory, context = self.prepare()
        original = "# Existing knowledge\n\nManual correction.\nEarlier dated observation.\n"
        for item in self.knowledge_items(context):
            final = Path(item["final"])
            final.parent.mkdir(parents=True, exist_ok=True)
            final.write_text(original, encoding="utf-8")
        directory, context = self.prepare(empty=True)
        self.assertEqual(len(context["output_paths"]), 2)
        for item in self.knowledge_items(context):
            self.assertEqual(Path(item["staged"]).read_text(), original)
        self.drafts(directory, context)
        runner.finish_run(self.paths, self.settings, directory)
        self.assertTrue(runner.completed(self.paths, self.settings, DAY))
        for item in self.knowledge_items(context):
            self.assertEqual(Path(item["final"]).read_text(), original)

    def test_rerun_preserves_manual_additions_and_does_not_duplicate_history(self):
        directory, context = self.prepare()
        self.drafts(directory, context, addition="Earlier supported statement.\n")
        runner.finish_run(self.paths, self.settings, directory)
        original = "# Knowledge\nEarlier supported statement.\nManual user correction.\n"
        for item in self.knowledge_items(context):
            Path(item["final"]).write_text(original, encoding="utf-8")
        rerun, newer = self.prepare()
        self.drafts(rerun, newer)
        runner.finish_run(self.paths, self.settings, rerun)
        for item in self.knowledge_items(newer):
            self.assertEqual(Path(item["final"]).read_text(), original)
        # Retrying the already published older run must not replace later edits.
        runner.finish_run(self.paths, self.settings, directory)
        for item in self.knowledge_items(newer):
            self.assertEqual(Path(item["final"]).read_text(), original)

    def test_manual_edit_after_prepare_blocks_all_publication(self):
        directory, context = self.prepare()
        self.drafts(directory, context, addition="Stale new observation.\n")
        item = self.knowledge_items(context)[0]
        final = Path(item["final"])
        final.parent.mkdir(parents=True, exist_ok=True)
        final.write_text("Human correction after preparation.\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Result changed after prepare"):
            runner.finish_run(self.paths, self.settings, directory)
        self.assertEqual(final.read_text(), "Human correction after preparation.\n")
        self.assertFalse(Path(context["publication_journal"]).exists())
        self.assertFalse(Path(context["final_output_paths"][0]).exists())

    def test_later_updates_keep_prior_day_and_automation_completion_valid(self):
        first, older = self.prepare()
        self.drafts(first, older, addition="Earlier observation.\n")
        runner.finish_run(self.paths, self.settings, first)
        second, newer = self.prepare(NEXT_DAY)
        self.drafts(second, newer, addition="Later observation.\n")
        runner.finish_run(self.paths, self.settings, second)
        self.assertTrue(runner.completed(self.paths, self.settings, DAY))
        self.assertTrue(runner.completed(self.paths, self.settings, NEXT_DAY))
        for item in self.knowledge_items(newer):
            self.assertIn("Earlier observation.\nLater observation.", Path(item["final"]).read_text())
        launch = self.root / "launch"
        launch.mkdir()
        invocation = {"invocation_id": "isolated", "dates": [DAY, NEXT_DAY],
                      "date": None, "snapshot_end": None, "allow_empty": False}
        tickets = [{"date": day, "status": "prepared", "run_dir": str(run)}
                   for day, run in ((DAY, first), (NEXT_DAY, second))]
        config.write_json(launch / "tickets.json", tickets)
        config.write_json(launch / "completion.json", {
            "invocation_id": "isolated",
            "results": [{**ticket, "status": "completed"} for ticket in tickets],
        })
        results = automation.validate_receipt(self.paths, self.settings, launch, invocation)
        self.assertEqual([item["date"] for item in results], [DAY, NEXT_DAY])

    @unittest.skipIf(os.name == "nt", "POSIX lock concurrency is executed on Linux")
    def test_concurrent_dates_cannot_overwrite_each_others_cumulative_updates(self):
        first, older = self.prepare()
        second, newer = self.prepare(NEXT_DAY)
        self.drafts(first, older, addition="First date statement.\n")
        self.drafts(second, newer, addition="Second date statement.\n")
        original_publish = runner.publish_outputs
        active = 0
        maximum_active = 0
        counter_lock = threading.Lock()

        def checked_publish(*args, **kwargs):
            nonlocal active, maximum_active
            with counter_lock:
                active += 1
                maximum_active = max(maximum_active, active)
            try:
                time.sleep(0.05)
                return original_publish(*args, **kwargs)
            finally:
                with counter_lock:
                    active -= 1

        def finish(directory):
            try:
                return runner.finish_run(self.paths, self.settings, directory)["status"]
            except ValueError as error:
                return str(error)

        with patch.object(runner, "publish_outputs", side_effect=checked_publish):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(finish, [first, second]))
        self.assertEqual(maximum_active, 1)
        self.assertEqual(results.count("completed"), 1)
        self.assertEqual(sum("Result changed after prepare" in result for result in results), 1)
        winner = older if results[0] == "completed" else newer
        for item in self.knowledge_items(winner):
            self.assertEqual(Path(item["final"]).read_text(), Path(item["staged"]).read_text())

    def test_custom_dated_schema_still_validates_with_standard_knowledge(self):
        checker = self.root / "validator.py"
        checker.write_text(
            "import json, pathlib\n"
            "context = json.loads(pathlib.Path('context.json').read_text())\n"
            "kinds = context['output_kinds']\n"
            "assert set(kinds.values()) >= {'user_model', 'machine_context', 'time_use_json'}\n"
            "pathlib.Path('validator-ran.txt').write_text('checked')\n",
            encoding="utf-8",
        )
        self.profile({"output_schema": "isolated-legacy",
                      "validation_command": [sys.executable, str(checker)]})
        directory, context = self.prepare()
        self.drafts(directory, context)
        for name, kind in context["output_kinds"].items():
            if kind == "time_use_json":
                config.write_json(Path(name), {"date": DAY, "legacy_entries": []})
        runner.finish_run(self.paths, self.settings, directory)
        self.assertEqual((directory / "validator-ran.txt").read_text(), "checked")

    def test_duplicate_targets_and_non_markdown_knowledge_are_rejected(self):
        target = str(self.root / "shared.md")
        self.profile({"output_paths": {"user_model": target, "machine_context": target}})
        with self.assertRaisesRegex(ValueError, "destinations must be distinct"):
            self.prepare()
        path = self.root / "knowledge.json"
        config.write_json(path, {"date": DAY})
        with self.assertRaisesRegex(ValueError, "Knowledge output must be Markdown"):
            runner.validate_output(path, DAY, "user_model", custom=True)

    def test_preparation_and_finish_never_launch_an_agent(self):
        with patch("my_big_brother.analyzers.codex.launch") as launch:
            directory, context = self.prepare()
            self.drafts(directory, context)
            runner.finish_run(self.paths, self.settings, directory)
        launch.assert_not_called()

    def test_plan_due_lists_dates_without_preparation_or_mutations(self):
        config.write_json(self.paths.config / "config.json", self.settings)
        original = {path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}
        with patch.object(runner, "latest_closed_date", return_value=NEXT_DAY), \
             patch.object(runner, "prepare_run") as prepare, \
             patch.object(runner, "analyze") as analyze, \
             patch("my_big_brother.sources.bash.collect") as collect, \
             patch("my_big_brother.analyzers.codex.launch") as launch:
            status, value = self.invoke_cli(["plan-due", "--max-days", "2"])
        self.assertEqual(status, 0)
        self.assertEqual(value, {"dates": [DAY, NEXT_DAY]})
        for action in (prepare, analyze, collect, launch):
            action.assert_not_called()
        self.assertEqual({path: path.read_bytes() for path in self.root.rglob("*") if path.is_file()}, original)
        for limit in ("0", "32"):
            status, message = self.invoke_cli(["plan-due", "--max-days", limit])
            self.assertEqual(status, 1)
            self.assertIn("max_days must be from 1 to 31", message)

    def test_cli_sequential_catchup_merges_both_dates_without_another_agent(self):
        config.write_json(self.paths.config / "config.json", self.settings)
        with patch.object(runner, "latest_closed_date", return_value=NEXT_DAY), \
             patch("my_big_brother.analyzers.codex.launch") as launch:
            status, plan = self.invoke_cli(["plan-due", "--max-days", "2"])
            self.assertEqual(status, 0)
            for day in plan["dates"]:
                rows = [{"content": "Dated user statement.", "timestamp": day + "T10:00:00+00:00"}]
                with patch("my_big_brother.sources.bash.collect", return_value=SourceResult(rows=rows)):
                    status, ticket = self.invoke_cli(["analyze", "--date", day, "--skip-completed"])
                self.assertEqual(status, 0)
                self.assertEqual(ticket["status"], "prepared")
                directory = Path(ticket["run_dir"])
                context = runner.read_object(directory / "context.json")
                self.drafts(directory, context, addition=day + " supported statement.\n")
                status, completed = self.invoke_cli(["finish", "--run-dir", str(directory)])
                self.assertEqual(status, 0)
                self.assertEqual(completed["status"], "completed")
            launch.assert_not_called()
        self.assertTrue(runner.completed(self.paths, self.settings, DAY))
        self.assertTrue(runner.completed(self.paths, self.settings, NEXT_DAY))
        for item in self.knowledge_items(context):
            text = Path(item["final"]).read_text()
            self.assertEqual(text.count(DAY + " supported statement."), 1)
            self.assertEqual(text.count(NEXT_DAY + " supported statement."), 1)

    def test_cli_skips_completed_only_when_requested_and_preserves_explicit_rerun(self):
        config.write_json(self.paths.config / "config.json", self.settings)
        directory, context = self.prepare()
        self.drafts(directory, context)
        runner.finish_run(self.paths, self.settings, directory)
        with patch("my_big_brother.sources.bash.collect") as collect:
            status, skipped = self.invoke_cli(["analyze", "--date", DAY, "--skip-completed"])
        self.assertEqual(status, 0)
        self.assertEqual(skipped["status"], "already-completed")
        self.assertEqual(skipped["run_dir"], str(directory))
        collect.assert_not_called()
        with patch("my_big_brother.sources.bash.collect", return_value=SourceResult(rows=[{"content": "Evidence"}])):
            status, rerun = self.invoke_cli(["analyze", "--date", DAY])
        self.assertEqual(status, 0)
        self.assertEqual(rerun["status"], "prepared")
        self.assertNotEqual(rerun["run_dir"], str(directory))


if __name__ == "__main__":
    unittest.main()
