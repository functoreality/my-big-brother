import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from my_big_brother import config, runner
from my_big_brother.analyzers import codex
from my_big_brother.paths import Paths
from my_big_brother.sources import SourceResult


DAY = "2020-01-15"
SHANGHAI = timezone(timedelta(hours=8))


class ProfileTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.paths = Paths(self.root / "configuration", self.root / "data")
        self.settings = config.initialize(self.paths, sources=["codex"])
        sessions = self.root / "sessions"
        sessions.mkdir()
        self.settings["sources"]["codex"]["path"] = str(sessions)
        event = {"type": "event_msg", "timestamp": datetime.fromisoformat(DAY + "T10:00:00").astimezone().isoformat(),
                 "payload": {"type": "user_message", "message": "Review an isolated parser fixture"}}
        (sessions / "fixture.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
        self.rules = self.root / "review rules.md"
        self.rules.write_text("Compare relevant method nodes, without changing originals.\n", encoding="utf-8")
        self.methods = self.root / "method notes.md"
        self.methods.write_text("Private fixture method contents should not be copied.\n", encoding="utf-8")
        self.checker = self.root / "validate profile.py"
        self.checker.write_text(
            "import json, pathlib, sys\n"
            "context = json.loads(pathlib.Path('context.json').read_text())\n"
            "assert context['date'] == sys.argv[1]\n"
            "if 'reject' in sys.argv: raise SystemExit(9)\n"
            "pathlib.Path('validator-ran.txt').write_text(sys.argv[-1])\n",
            encoding="utf-8",
        )
        self.profile_path = self.root / "personal profile.json"
        self.profile = {"schema_version": 1, "instructions": [str(self.rules)],
                        "context_files": [str(self.methods)], "output_paths": {}}

    def select_profile(self, *, post=False, custom=False):
        if custom:
            self.profile.update(output_schema="fixture-v4",
                                validation_command=[sys.executable, str(self.checker), "{date}", "{run_dir}"])
        if post:
            task = self.root / "post task.md"
            task.write_text("Maintain isolated fixture knowledge. Deduplicate operations on retry.\n", encoding="utf-8")
            self.write_root = self.root / "knowledge"
            self.profile["post_review"] = {
                "task": str(task), "read_paths": [str(self.methods)], "write_paths": [str(self.write_root)],
                "validation_command": [sys.executable, str(self.checker), "{date}", "{run_dir}"],
            }
        config.write_json(self.profile_path, self.profile)
        self.settings["local_profile"] = str(self.profile_path)
        config.write_json(self.paths.config / "config.json", self.settings)
        return config.load(self.paths)

    def prepare(self, *, snapshot_end=None):
        prepared = runner.prepare_run(self.paths, self.settings, DAY, snapshot_end=snapshot_end)
        run_dir = Path(prepared["run_dir"])
        return run_dir, runner.read_object(run_dir / "context.json")

    def staged(self, *, custom=False, snapshot_end=None):
        run_dir, context = self.prepare(snapshot_end=snapshot_end)
        self.write_drafts(run_dir, context, custom=custom)
        return run_dir, context

    def write_drafts(self, run_dir, context, *, custom=False):
        for name, kind in context["output_kinds"].items():
            path = Path(name)
            if path.suffix == ".md":
                path.write_text("# Isolated parser review\n", encoding="utf-8")
            else:
                key = "samples" if kind == "time_estimates" else "segments"
                payload = {"date": context["date"], key: []}
                if custom:
                    payload["schema_version"] = 4
                    if kind == "time_use_json":
                        payload["segments"] = [{"human_attention": {"status": "unknown", "candidates": []}}]
                config.write_json(path, payload)
        config.write_json(run_dir / "completion.json", context["completion_example"])

    def complete_actions(self, settings, action_dir, prompt, *, write_paths=()):
        action_dir = Path(action_dir)
        action_context = runner.read_object(action_dir / "context.json")
        self.assertTrue(all(Path(name).is_file() for name in action_context["outputs"]))
        self.assertEqual(list(write_paths), [str(self.write_root)])
        config.write_json(action_dir / "action_receipt.json", action_context["action_receipt_example"])

    def test_profile_is_opt_in_and_optional_sources_are_disabled(self):
        defaults = config.defaults(self.paths)
        self.assertIsNone(defaults["local_profile"])
        self.assertFalse(defaults["sources"]["vim"]["enabled"])
        self.assertFalse(defaults["sources"]["screenshots"]["enabled"])
        run_dir, context = self.prepare()
        self.assertIsNone(context["profile"])
        self.assertNotIn(str(self.methods), runner.prompt_for(run_dir))

    def test_loads_explicit_policy_but_does_not_copy_context(self):
        self.select_profile()
        run_dir, context = self.prepare()
        self.assertEqual(context["profile"]["instructions"], [str(self.rules)])
        self.assertEqual(context["profile"]["context_files"], [str(self.methods)])
        prepared_text = "".join(path.read_text() for path in run_dir.rglob("*")
                                if path.is_file() and path.suffix in {".json", ".jsonl", ".txt"})
        self.assertNotIn(self.methods.read_text(), prepared_text)
        prompt = runner.prompt_for(run_dir)
        self.assertIn("extend the review's methods", prompt)
        self.assertIn("Post-review operations are a separate phase", prompt)

    def test_configuration_rejects_missing_scope_or_unvalidated_custom_schema(self):
        for changes in ({"context_files": [str(self.root / "missing")]},
                        {"output_schema": "custom"}, {"instructions": "all notes"},
                        {"output_paths": {"worklog": str(self.root / "no-date.md")}},
                        {"validation_command": [sys.executable, "{unknown}"]}):
            with self.subTest(changes=changes):
                self.profile = {"schema_version": 1, **changes}
                config.write_json(self.profile_path, self.profile)
                self.settings["local_profile"] = str(self.profile_path)
                with self.assertRaises((ValueError, OSError)):
                    config.load_profile(self.settings)

    def test_custom_destinations_preserve_output_kind_and_existing_notes(self):
        self.profile["output_paths"] = {key: str(self.root / "existing layout" / (key + "-{date}" +
                                    (".json" if key in {"time_use_json", "time_estimates"} else ".md")))
                                    for key in config.OUTPUT_KEYS}
        self.select_profile()
        final = Path(self.profile["output_paths"]["worklog"].format(date=DAY))
        final.parent.mkdir()
        final.write_text("Manual fixture note\n", encoding="utf-8")
        run_dir, context = self.prepare()
        self.assertEqual(Path(context["output_paths"][0]).read_text(), "Manual fixture note\n")
        self.write_drafts(run_dir, context)
        runner.finish_run(self.paths, self.settings, run_dir)
        self.assertEqual(set(context["final_output_paths"]),
                         {value.format(date=DAY) for value in self.profile["output_paths"].values()})

    def test_custom_validator_accepts_rich_json_and_uses_argv(self):
        self.select_profile(custom=True)
        run_dir, _ = self.staged(custom=True)
        runner.finish_run(self.paths, self.settings, run_dir)
        self.assertEqual((run_dir / "validator-ran.txt").read_text(), str(run_dir))

    def test_custom_validation_failure_never_publishes(self):
        self.select_profile(custom=True)
        self.profile["validation_command"].append("reject")
        config.write_json(self.profile_path, self.profile)
        run_dir, context = self.staged(custom=True)
        with self.assertRaisesRegex(ValueError, "review-validation failed"):
            runner.finish_run(self.paths, self.settings, run_dir)
        self.assertFalse(any(Path(name).exists() for name in context["final_output_paths"]))
        self.assertTrue((run_dir / "logs/review-validation.stderr.log").exists())

    def test_custom_validator_cannot_bypass_identity_coverage_or_user_conflict(self):
        self.select_profile(custom=True)
        for failure in ("identity", "coverage", "conflict"):
            with self.subTest(failure=failure):
                run_dir, context = self.staged(custom=True)
                receipt = context["completion_example"]
                if failure == "identity":
                    receipt["run_id"] = "another-run"
                elif failure == "coverage":
                    receipt["sources"]["codex"]["entries"] += 1
                else:
                    final = Path(context["final_output_paths"][0])
                    final.parent.mkdir(parents=True, exist_ok=True)
                    final.write_text("New human correction\n", encoding="utf-8")
                config.write_json(run_dir / "completion.json", receipt)
                with self.assertRaises(ValueError):
                    runner.finish_run(self.paths, self.settings, run_dir)
                self.assertFalse((run_dir / "publication.json").exists())

    def test_profile_and_policy_edits_block_stale_publication(self):
        self.select_profile()
        run_dir, context = self.staged()
        self.rules.write_text("Changed interpretation policy\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "local_profile changed"):
            runner.finish_run(self.paths, self.settings, run_dir)
        self.assertFalse(any(Path(name).exists() for name in context["final_output_paths"]))

    def test_profile_edit_invalidates_completed_day_but_data_edit_does_not(self):
        self.select_profile()
        run_dir, _ = self.staged()
        runner.finish_run(self.paths, self.settings, run_dir)
        self.assertTrue(runner.completed(self.paths, self.settings, DAY))
        self.methods.write_text("New data, unchanged policy\n", encoding="utf-8")
        self.assertTrue(runner.completed(self.paths, self.settings, DAY))
        self.rules.write_text("New policy\n", encoding="utf-8")
        self.assertFalse(runner.completed(self.paths, self.settings, DAY))

    def test_output_mapping_tampering_is_rejected(self):
        self.select_profile()
        run_dir, context = self.staged()
        context["output_mapping"][0]["final"] = str(self.root / "unexpected.md")
        config.write_json(run_dir / "context.json", context)
        with self.assertRaisesRegex(ValueError, "expected layout"):
            runner.finish_run(self.paths, self.settings, run_dir)

    def test_source_configuration_change_blocks_stale_review(self):
        run_dir, _ = self.staged()
        self.settings["sources"]["codex"]["required"] = True
        with self.assertRaisesRegex(ValueError, "configuration changed"):
            runner.finish_run(self.paths, self.settings, run_dir)

    def test_required_policy_cannot_be_removed_from_manifest(self):
        self.settings["sources"]["codex"].update(required=True, path=str(self.root / "missing"))
        run_dir, context = self.staged()
        manifest = runner.read_object(run_dir / "manifest.json")
        manifest["sources"]["codex"].pop("required")
        config.write_json(run_dir / "manifest.json", manifest)
        with self.assertRaisesRegex(ValueError, "Required source unavailable"):
            runner.finish_run(self.paths, self.settings, run_dir)

    def test_asset_hook_receives_evidence_ids_and_registers_asset_root(self):
        with patch("my_big_brother.sources.codex.prepare_assets", create=True,
                   return_value={"status": "ok", "coverage": {"mapped_frames": 1}}) as assets:
            run_dir, _ = self.prepare()
        rows, target = assets.call_args.args
        self.assertEqual(rows[0]["evidence_id"], "codex-000001")
        self.assertEqual(target, run_dir / "codex")
        manifest = runner.read_object(run_dir / "manifest.json")
        self.assertEqual(manifest["sources"]["codex"]["assets"]["root"], str(target))

    def test_required_unavailable_blocks_analysis_but_partial_keeps_evidence(self):
        self.settings["sources"]["codex"]["required"] = True
        session = Path(self.settings["sources"]["codex"]["path"]) / "fixture.jsonl"
        session.write_text(session.read_text() + "bad truncated json\n", encoding="utf-8")
        run_dir, context = self.prepare()
        self.assertEqual(runner.read_object(run_dir / "manifest.json")["sources"]["codex"]["status"], "partial")
        self.assertEqual(runner.read_object(run_dir / "state.json")["status"], "prepared")
        self.settings["sources"]["codex"]["path"] = str(self.root / "unavailable")
        with patch("my_big_brother.analyzers.codex.launch") as launch:
            result = runner.analyze(self.paths, self.settings, DAY)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blocked_sources"], ["codex"])
        launch.assert_not_called()

    def test_optional_adapter_exception_retains_diagnostic_and_other_sources(self):
        self.settings["sources"]["bash"] = {"enabled": True}
        available = SourceResult(rows=[{"timestamp": DAY + "T10:00:00+00:00", "event": "command"}])
        with patch("my_big_brother.sources.codex.collect", side_effect=RuntimeError("fixture parse defect")):
            with patch("my_big_brother.sources.bash.collect", return_value=available):
                run_dir, _ = self.prepare()
        manifest = runner.read_object(run_dir / "manifest.json")
        self.assertEqual(manifest["sources"]["codex"]["status"], "unavailable")
        self.assertEqual(manifest["sources"]["bash"]["entries"], 1)
        state = runner.read_object(run_dir / "state.json")
        self.assertEqual(state["status"], "prepared")
        diagnostic = runner.read_object(Path(state["source_diagnostics"]["codex"]))
        self.assertIn("fixture parse defect", diagnostic["error"])
        self.assertEqual(diagnostic["phase"], "collection")
        self.assertIn("RuntimeError", diagnostic["traceback"])
        self.assertIn("fixture parse defect", manifest["sources"]["codex"]["gaps"][0])

    def test_required_adapter_exception_blocks_without_losing_diagnostic(self):
        self.settings["sources"]["codex"]["required"] = True
        with patch("my_big_brother.sources.codex.collect", side_effect=RuntimeError("fixture parse defect")):
            with patch("my_big_brother.analyzers.codex.launch") as launch:
                result = runner.analyze(self.paths, self.settings, DAY)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["blocked_sources"], ["codex"])
        self.assertTrue((Path(result["run_dir"]) / "logs/codex-error.json").is_file())
        launch.assert_not_called()

    def test_optional_asset_exception_preserves_rows_and_other_sources(self):
        self.settings["sources"]["bash"] = {"enabled": True}
        available = SourceResult(rows=[{"timestamp": DAY + "T10:00:00+00:00", "event": "command"}])
        with patch("my_big_brother.sources.codex.prepare_assets", create=True,
                   side_effect=OSError("fixture storyboard failure")):
            with patch("my_big_brother.sources.bash.collect", return_value=available):
                run_dir, _ = self.prepare()
        manifest = runner.read_object(run_dir / "manifest.json")
        source = manifest["sources"]["codex"]
        self.assertEqual(source["status"], "unavailable")
        self.assertEqual(source["entries"], 1)
        self.assertEqual(source["assets"]["status"], "unavailable")
        self.assertEqual(manifest["sources"]["bash"]["entries"], 1)
        self.assertIn("asset preparation", runner.read_object(Path(source["diagnostic"]))["phase"])

    def test_required_asset_exception_blocks_analysis(self):
        self.settings["sources"]["codex"]["required"] = True
        with patch("my_big_brother.sources.codex.prepare_assets", create=True,
                   side_effect=OSError("fixture storyboard failure")):
            with patch("my_big_brother.analyzers.codex.launch") as launch:
                result = runner.analyze(self.paths, self.settings, DAY)
        self.assertEqual(result["status"], "blocked")
        launch.assert_not_called()

    def test_fixed_snapshot_is_offset_aware_and_half_open(self):
        self.settings["day_start_hour"] = 4
        start, full_end = runner.window(DAY, 4)
        cutoff = (start + timedelta(hours=6)).astimezone(SHANGHAI)
        with patch.object(runner, "now", return_value=full_end + timedelta(days=1)):
            run_dir, context = self.prepare(snapshot_end=cutoff)
        self.assertEqual(datetime.fromisoformat(context["window"]["end"]), cutoff)
        self.assertFalse(context["window"]["closed_day"])
        source = runner.read_object(run_dir / "manifest.json")["sources"]["codex"]
        self.assertEqual(source["entries"], 0)
        with patch.object(runner, "now", return_value=full_end + timedelta(days=1)):
            later_run, _ = self.prepare(snapshot_end=cutoff + timedelta(seconds=1))
        self.assertEqual(runner.read_object(later_run / "manifest.json")["sources"]["codex"]["entries"], 1)

    def test_snapshot_is_clamped_to_now_and_logical_day_end(self):
        start, full_end = runner.window(DAY, self.settings["day_start_hour"])
        current = start + timedelta(hours=12)
        with patch.object(runner, "now", return_value=current):
            _, context = self.prepare(snapshot_end=start + timedelta(hours=20))
        self.assertEqual(datetime.fromisoformat(context["window"]["end"]), current)
        with patch.object(runner, "now", return_value=full_end + timedelta(hours=2)):
            _, context = self.prepare(snapshot_end=full_end + timedelta(hours=1))
        self.assertEqual(datetime.fromisoformat(context["window"]["end"]), full_end)
        self.assertTrue(context["window"]["closed_day"])

    def test_snapshot_rejects_naive_and_out_of_window_cutoffs(self):
        start, _ = runner.window(DAY, self.settings["day_start_hour"])
        for cutoff in (start.replace(tzinfo=None), start, start - timedelta(seconds=1), "2020-01-15"):
            with self.subTest(cutoff=cutoff):
                with self.assertRaises(ValueError):
                    self.prepare(snapshot_end=cutoff)

    def test_analyze_forwards_fixed_snapshot_to_prepare_and_completion(self):
        start, _ = runner.window(DAY, self.settings["day_start_hour"])
        cutoff = start + timedelta(hours=12)

        def complete_review(settings, run_dir, prompt):
            self.write_drafts(Path(run_dir), runner.read_object(Path(run_dir) / "context.json"))

        with patch("my_big_brother.analyzers.codex.launch", side_effect=complete_review):
            result = runner.analyze(self.paths, self.settings, DAY, snapshot_end=cutoff)
        self.assertEqual(datetime.fromisoformat(runner.day_entry(self.paths, DAY)["window"]["end"]), cutoff)
        self.assertFalse(runner.completed(self.paths, self.settings, DAY))
        self.assertEqual(runner.read_object(Path(result["run_dir"]) / "state.json")["status"], "completed")

    def test_post_actions_run_after_publication_with_explicit_writable_roots(self):
        self.select_profile(post=True)
        run_dir, context = self.staged()
        with patch("my_big_brother.analyzers.codex.launch", side_effect=self.complete_actions) as launch:
            result = runner.finish_run(self.paths, self.settings, run_dir)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(launch.call_count, 1)
        self.assertTrue(runner.completed(self.paths, self.settings, DAY))
        self.assertEqual(runner.read_object(run_dir / "actions/state.json")["status"], "completed")

    def test_failed_actions_resume_same_run_without_rewriting_reports(self):
        self.select_profile(post=True)
        run_dir, context = self.staged()
        with patch("my_big_brother.analyzers.codex.launch", side_effect=ValueError("interrupted operations")):
            with self.assertRaisesRegex(ValueError, "interrupted operations"):
                runner.finish_run(self.paths, self.settings, run_dir)
        self.assertFalse(runner.completed(self.paths, self.settings, DAY))
        self.assertEqual(runner.day_entry(self.paths, DAY)["status"], "actions-pending")
        final = Path(context["final_output_paths"][0])
        final.write_text("Human addition after review publication\n", encoding="utf-8")
        with patch.object(runner, "latest_closed_date", return_value=DAY):
            with patch("my_big_brother.analyzers.codex.launch", side_effect=self.complete_actions) as launch:
                results = runner.due(self.paths, self.settings, 1)
        self.assertEqual(launch.call_count, 1)
        self.assertEqual(Path(launch.call_args.args[1]), run_dir / "actions")
        self.assertEqual(results[0]["run_dir"], str(run_dir))
        self.assertEqual(final.read_text(), "Human addition after review publication\n")
        self.assertEqual(runner.read_object(run_dir / "actions/state.json")["attempt"], 2)
        self.assertEqual(runner.read_object(run_dir / "actions/attempt-1.json")["status"], "failed")

    def test_same_fixed_snapshot_resumes_pending_actions_across_offsets(self):
        self.select_profile(post=True)
        start, _ = runner.window(DAY, self.settings["day_start_hour"])
        cutoff = start + timedelta(hours=12)
        run_dir, _ = self.staged(snapshot_end=cutoff)
        with patch("my_big_brother.analyzers.codex.launch", side_effect=ValueError("interrupted operations")):
            with self.assertRaises(ValueError):
                runner.finish_run(self.paths, self.settings, run_dir)
        with patch.object(runner, "prepare_run") as prepare:
            with patch("my_big_brother.analyzers.codex.launch", side_effect=self.complete_actions) as launch:
                result = runner.analyze(self.paths, self.settings, DAY,
                                        snapshot_end=cutoff.astimezone(SHANGHAI))
        prepare.assert_not_called()
        self.assertEqual(launch.call_count, 1)
        self.assertEqual(result["run_dir"], str(run_dir))

    def test_changed_fixed_snapshot_creates_review_instead_of_resuming_old_actions(self):
        self.select_profile(post=True)
        start, _ = runner.window(DAY, self.settings["day_start_hour"])
        cutoff = start + timedelta(hours=12)
        old_run, _ = self.staged(snapshot_end=cutoff)
        with patch("my_big_brother.analyzers.codex.launch", side_effect=ValueError("interrupted operations")):
            with self.assertRaises(ValueError):
                runner.finish_run(self.paths, self.settings, old_run)

        def complete_both(settings, target, prompt, **keywords):
            if Path(target).name == "actions":
                self.complete_actions(settings, target, prompt, **keywords)
            else:
                self.write_drafts(Path(target), runner.read_object(Path(target) / "context.json"))

        with patch("my_big_brother.analyzers.codex.launch", side_effect=complete_both) as launch:
            result = runner.analyze(self.paths, self.settings, DAY, snapshot_end=cutoff + timedelta(hours=1))
        self.assertEqual(launch.call_count, 2)
        self.assertNotEqual(result["run_dir"], str(old_run))
        self.assertEqual(datetime.fromisoformat(runner.day_entry(self.paths, DAY)["window"]["end"]),
                         cutoff + timedelta(hours=1))
        self.assertEqual(runner.read_object(old_run / "actions/state.json")["status"], "failed")

    def test_successful_action_receipt_is_validated_without_repeating_actions(self):
        self.select_profile(post=True)
        run_dir, _ = self.staged()
        with patch("my_big_brother.analyzers.codex.launch", side_effect=self.complete_actions):
            runner.finish_run(self.paths, self.settings, run_dir)
        with patch("my_big_brother.analyzers.codex.launch") as launch:
            runner.finish_run(self.paths, self.settings, run_dir)
        launch.assert_not_called()

    def test_wrong_action_receipt_cannot_complete_day(self):
        self.select_profile(post=True)
        run_dir, _ = self.staged()

        def wrong_receipt(settings, action_dir, prompt, *, write_paths):
            config.write_json(Path(action_dir) / "action_receipt.json",
                              {"run_id": "wrong", "date": DAY, "status": "completed"})

        with patch("my_big_brother.analyzers.codex.launch", side_effect=wrong_receipt):
            with self.assertRaisesRegex(ValueError, "action receipt"):
                runner.finish_run(self.paths, self.settings, run_dir)
        self.assertFalse(runner.completed(self.paths, self.settings, DAY))

    def test_post_validator_failure_keeps_day_pending(self):
        self.select_profile(post=True)
        self.profile["post_review"]["validation_command"].append("reject")
        config.write_json(self.profile_path, self.profile)
        run_dir, _ = self.staged()
        with patch("my_big_brother.analyzers.codex.launch", side_effect=self.complete_actions):
            with self.assertRaisesRegex(ValueError, "action-validation failed"):
                runner.finish_run(self.paths, self.settings, run_dir)
        self.assertFalse(runner.completed(self.paths, self.settings, DAY))

    def test_publication_retry_recovers_own_partial_file_replacements(self):
        run_dir, context = self.staged()
        real_replace = os.replace
        finals = set(context["final_output_paths"])
        replacements = 0

        def fail_second_file(source, target):
            nonlocal replacements
            if str(target) in finals:
                replacements += 1
                if replacements == 2:
                    raise OSError("fixture interrupted publication")
            return real_replace(source, target)

        with patch.object(runner.os, "replace", side_effect=fail_second_file):
            with self.assertRaisesRegex(OSError, "interrupted publication"):
                runner.finish_run(self.paths, self.settings, run_dir)
        self.assertEqual(runner.read_object(run_dir / "publication.json")["status"], "publishing")
        result = runner.finish_run(self.paths, self.settings, run_dir)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(all(Path(name).is_file() for name in context["final_output_paths"]))

    def test_launcher_adds_only_requested_directories(self):
        self.write_root = self.root / "write root"
        self.write_root.mkdir()
        with patch("shutil.which", return_value="/tools/codex"):
            review = codex.command(self.settings["codex"], self.root)
            actions = codex.command(self.settings["codex"], self.root, write_paths=[str(self.write_root)])
        self.assertNotIn("--add-dir", review)
        self.assertEqual(actions[actions.index("--add-dir") + 1], str(self.write_root))
        with patch("shutil.which", return_value="/tools/codex"):
            with self.assertRaisesRegex(ValueError, "absolute directory"):
                codex.command(self.settings["codex"], self.root, write_paths=[str(self.rules)])


if __name__ == "__main__":
    unittest.main()
