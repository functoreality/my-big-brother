import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from my_big_brother import config, notifications, runner
from my_big_brother.analyzers import codex
from my_big_brother.paths import Paths


DAY = "2020-01-15"


class NotificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.paths = Paths(self.root / "config", self.root / "data")
        self.settings = config.initialize(self.paths, sources=["codex"])
        self.history = self.root / "sessions"
        self.history.mkdir()
        event = {"type": "event_msg", "timestamp": DAY + "T10:00:00+00:00",
                 "payload": {"type": "user_message", "message": "Synthetic note edit"}}
        (self.history / "session.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
        self.settings["sources"]["codex"]["path"] = str(self.history)
        self.save()

    def save(self):
        config.write_json(self.paths.config / "config.json", self.settings)
        self.settings = config.load(self.paths)

    def staged(self):
        result = runner.prepare_run(self.paths, self.settings, DAY)
        run = Path(result["run_dir"])
        context = runner.read_object(run / "context.json")
        for name, kind in context["output_kinds"].items():
            target = Path(name)
            if target.suffix == ".md":
                target.write_text("# Synthetic note correction\n", encoding="utf-8")
            else:
                key = "samples" if kind == "time_estimates" else "segments"
                config.write_json(target, {"date": DAY, key: []})
        config.write_json(run / "completion.json", context["completion_example"])
        return run

    def plan(self, action, entries=None):
        action = Path(action)
        context = runner.read_object(action / "context.json")
        (action / "reminder.md").write_text(
            "# Check the note\nEvidence: synthetic counterexample.\n"
            "Benefit: avoid learning an error. Confidence: high for this example.\n"
            "Next step: add the missing condition.\n", encoding="utf-8")
        if entries is None:
            entries = [{"id": "note-missing-condition", "content_file": "reminder.md"}]
        config.write_json(action / "messages.json", {
            "run_id": context["run_id"], "date": DAY, "messages": entries})
        return context

    def receipt(self, action):
        action = Path(action)
        context = runner.read_object(action / "context.json")
        config.write_json(action / "action_receipt.json", context["action_receipt_example"])

    def test_new_install_enables_reminders_without_profile(self):
        self.assertEqual(self.settings["notifications"], {"enabled": True, "inbox": None})
        self.assertIsNone(config.load_profile(self.settings))
        run = self.staged()
        result = runner.finish_run(self.paths, self.settings, run)
        self.assertEqual(result["status"], "actions-pending")
        self.assertEqual(Path(result["action_dir"]), run / "notifications")
        context = self.plan(result["action_dir"])
        self.assertEqual(context["task"], str(notifications.TASK))
        self.assertEqual(context["inbox"], str(Path(self.settings["results_root"]) / "inbox"))
        applied = subprocess.run(context["delivery_command"], check=True, capture_output=True, text=True)
        delivered = json.loads(applied.stdout)["messages"]
        self.receipt(result["action_dir"])
        self.assertEqual(runner.finish_run(self.paths, self.settings, run)["status"], "completed")
        self.assertEqual(len(delivered), 1)
        self.assertTrue(runner.completed(self.paths, self.settings, DAY))

    def test_existing_config_without_field_stays_disabled(self):
        del self.settings["notifications"]
        self.save()
        self.assertFalse(self.settings["notifications"]["enabled"])
        run = self.staged()
        self.assertEqual(runner.finish_run(self.paths, self.settings, run)["status"], "completed")
        self.assertFalse((run / "notifications").exists())

    def test_disabled_reminders_have_no_action_phase(self):
        self.settings["notifications"]["enabled"] = False
        self.save()
        run = self.staged()
        self.assertEqual(runner.finish_run(self.paths, self.settings, run)["status"], "completed")

    def test_disabled_legacy_config_ignores_unused_inbox(self):
        del self.settings["notifications"]
        inbox = Path(self.settings["results_root"]) / "inbox"
        inbox.write_text("Existing unrelated file\n", encoding="utf-8")
        self.save()
        self.assertFalse(self.settings["notifications"]["enabled"])
        self.assertEqual(inbox.read_text(), "Existing unrelated file\n")

    def test_empty_plan_completes_without_messages(self):
        run = self.staged()
        action = Path(runner.finish_run(self.paths, self.settings, run)["action_dir"])
        self.plan(action, [])
        self.assertEqual(notifications.deliver(action, apply=True), [])
        self.receipt(action)
        self.assertEqual(runner.finish_run(self.paths, self.settings, run)["status"], "completed")
        self.assertEqual(list(Path(notifications.settings(self.settings)["inbox"]).iterdir()), [])

    def test_retry_and_same_day_rerun_do_not_duplicate(self):
        for _ in range(2):
            run = self.staged()
            result = runner.finish_run(self.paths, self.settings, run)
            action = Path(result["action_dir"])
            self.plan(action)
            delivered = notifications.deliver(action, apply=True)
            before = Path(delivered[0]).stat().st_mtime_ns
            notifications.deliver(action, apply=True)
            self.assertEqual(Path(delivered[0]).stat().st_mtime_ns, before)
            pending = runner.analyze(self.paths, self.settings, DAY)
            self.assertEqual(pending["run_dir"], str(run))
            self.assertEqual(pending["status"], "actions-pending")
            self.receipt(action)
            runner.finish_run(self.paths, self.settings, run)
        self.assertEqual(len(list(Path(notifications.settings(self.settings)["inbox"]).glob("*.md"))), 1)

    def test_changed_existing_message_is_preserved(self):
        run = self.staged()
        action = Path(runner.finish_run(self.paths, self.settings, run)["action_dir"])
        self.plan(action)
        target = Path(notifications.deliver(action, apply=True)[0])
        target.write_text("Human correction\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Preserve"):
            notifications.deliver(action, apply=True)
        self.assertEqual(target.read_text(), "Human correction\n")
        self.receipt(action)
        with self.assertRaises(ValueError):
            runner.finish_run(self.paths, self.settings, run)
        self.assertEqual(runner.day_entry(self.paths, DAY)["status"], "actions-pending")

    def test_receipt_cannot_claim_undelivered_message(self):
        run = self.staged()
        action = Path(runner.finish_run(self.paths, self.settings, run)["action_dir"])
        self.plan(action)
        self.receipt(action)
        with self.assertRaises(ValueError):
            runner.finish_run(self.paths, self.settings, run)

    def test_custom_inbox_is_granted_without_its_parent(self):
        inbox = self.root / "custom" / "inbox"
        self.settings["notifications"]["inbox"] = str(inbox)
        self.save()
        roots = codex.writable_roots(self.paths, self.settings)
        self.assertIn(str(inbox), roots)
        self.assertNotIn(str(inbox.parent), roots)
        run = self.staged()
        action = Path(runner.finish_run(self.paths, self.settings, run)["action_dir"])
        self.plan(action)
        self.assertEqual(Path(notifications.deliver(action, apply=True)[0]).parent, inbox)

    def test_private_post_review_runs_after_notifications(self):
        task = self.root / "private.md"
        task.write_text("Maintain synthetic knowledge only.\n")
        checker = self.root / "check.py"
        checker.write_text("import sys\nsys.exit(0)\n")
        profile = self.root / "profile.json"
        config.write_json(profile, {"post_review": {
            "task": str(task), "write_paths": [str(self.root / "knowledge")],
            "validation_command": [sys.executable, str(checker)]}})
        self.settings["local_profile"] = str(profile)
        self.save()
        run = self.staged()
        first = runner.finish_run(self.paths, self.settings, run)
        self.assertEqual(Path(first["action_dir"]).name, "notifications")
        self.plan(first["action_dir"], [])
        self.receipt(first["action_dir"])
        second = runner.finish_run(self.paths, self.settings, run)
        self.assertEqual(Path(second["action_dir"]).name, "actions")
        self.assertEqual(runner.analyze(self.paths, self.settings, DAY)["action_dir"], second["action_dir"])
        self.receipt(second["action_dir"])
        self.assertEqual(runner.finish_run(self.paths, self.settings, run)["status"], "completed")

    def test_notification_policy_change_blocks_stale_publication(self):
        run = self.staged()
        self.settings["notifications"]["inbox"] = str(self.root / "new-inbox")
        with self.assertRaisesRegex(ValueError, "configuration changed"):
            runner.finish_run(self.paths, self.settings, run)
        self.settings["notifications"]["inbox"] = None
        task = self.root / "changed-task.md"
        task.write_text("Changed notification policy\n")
        with patch.object(notifications, "TASK", task):
            with self.assertRaisesRegex(ValueError, "configuration changed"):
                runner.finish_run(self.paths, self.settings, run)

    def test_reject_invalid_or_disposable_destinations(self):
        for value in (None, {}, {"enabled": 1}, {"enabled": True, "extra": 1},
                      {"enabled": True, "inbox": "relative"},
                      {"enabled": True, "inbox": str(self.paths.raw_logs / "inbox")}):
            with self.subTest(value=value):
                self.settings["notifications"] = value
                config.write_json(self.paths.config / "config.json", self.settings)
                with self.assertRaises(ValueError):
                    config.load(self.paths)

    def test_plan_rejects_paths_duplicates_empty_and_wrong_identity(self):
        run = self.staged()
        action = Path(runner.finish_run(self.paths, self.settings, run)["action_dir"])
        outside = self.root / "outside.md"
        outside.write_text("Outside\n")
        for entries in ([{"id": "../escape", "content_file": "reminder.md"}],
                        [{"id": "valid", "content_file": str(outside)}],
                        [{"id": "valid", "content_file": "../outside.md"}],
                        [{"id": "valid", "content_file": "reminder.md"}] * 2):
            with self.subTest(entries=entries):
                self.plan(action, entries)
                with self.assertRaises(ValueError):
                    notifications.deliver(action, apply=True)
        self.plan(action)
        (action / "reminder.md").write_text("\n")
        with self.assertRaises(ValueError):
            notifications.deliver(action, apply=True)
        self.plan(action)
        plan = runner.read_object(action / "messages.json")
        plan["run_id"] = "another-run"
        config.write_json(action / "messages.json", plan)
        with self.assertRaisesRegex(ValueError, "does not match"):
            notifications.deliver(action, apply=True)

    @unittest.skipUnless(os.name == "posix", "symlink behavior")
    def test_disabled_legacy_config_does_not_resolve_unused_inbox(self):
        del self.settings["notifications"]
        inbox = Path(self.settings["results_root"]) / "inbox"
        inbox.symlink_to(inbox)
        self.save()
        run = self.staged()
        self.assertEqual(runner.finish_run(self.paths, self.settings, run)["status"], "completed")

    @unittest.skipUnless(os.name == "posix", "symlink behavior")
    def test_replaced_inbox_or_parent_cannot_redirect_delivery(self):
        for replace_parent in (False, True):
            with self.subTest(replace_parent=replace_parent):
                parent = self.root / ("parent" if replace_parent else "direct")
                inbox = parent / "inbox"
                self.settings["notifications"]["inbox"] = str(inbox)
                self.save()
                run = self.staged()
                action = Path(runner.finish_run(self.paths, self.settings, run)["action_dir"])
                self.plan(action)
                original = parent if replace_parent else inbox
                original.rename(self.root / ("saved-parent" if replace_parent else "saved-inbox"))
                outside = self.root / ("outside-parent" if replace_parent else "outside-inbox")
                outside.mkdir()
                original.symlink_to(outside, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, "Inbox path changed"):
                    notifications.deliver(action, apply=True)
                self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(os.name == "posix", "symlink behavior")
    def test_symlink_draft_or_target_cannot_escape(self):
        run = self.staged()
        action = Path(runner.finish_run(self.paths, self.settings, run)["action_dir"])
        context = self.plan(action)
        outside = self.root / "outside.md"
        outside.write_text("Outside\n")
        (action / "linked.md").symlink_to(outside)
        self.plan(action, [{"id": "valid", "content_file": "linked.md"}])
        with self.assertRaises(ValueError):
            notifications.deliver(action, apply=True)
        self.plan(action)
        target = Path(context["inbox"]) / (DAY + "--note-missing-condition.md")
        target.symlink_to(outside)
        with self.assertRaises(ValueError):
            notifications.deliver(action, apply=True)
        self.assertEqual(outside.read_text(), "Outside\n")


if __name__ == "__main__":
    unittest.main()
