"""Optional interactive startup remains inside the single-Agent boundary."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from my_big_brother import config, runner
from my_big_brother.analyzers import codex
from my_big_brother.paths import Paths


class CodexTmuxTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.run = self.root / "unique-launch"
        (self.run / "logs").mkdir(parents=True)
        (self.run / "prompt.md").write_text("Isolated task.\n", encoding="utf-8")

    def test_exec_remains_default_and_model_optional(self):
        self.assertEqual(codex.validate_settings({})["mode"], "exec")
        with patch.object(codex.shutil, "which", return_value="/tools/codex"):
            command = codex.command({}, self.run)
        self.assertIn("exec", command)
        self.assertEqual(command[-1], "-")
        self.assertNotIn("--model", command)

    def test_tui_uses_same_scope_and_model_without_exec_options(self):
        writes = self.root / "output"
        writes.mkdir()
        with patch.object(codex.shutil, "which", return_value="/tools/codex"):
            command = codex.command({"mode": "tmux", "model": "chosen-model"}, self.run,
                                    write_paths=[str(writes)])
        self.assertNotIn("exec", command)
        for flag in ("--ephemeral", "--skip-git-repo-check", "--output-last-message", "--color"):
            self.assertNotIn(flag, command)
        self.assertIn('approval_policy="never"', command)
        self.assertIn('projects.' + json.dumps(str(self.run)) + '.trust_level="trusted"', command)
        self.assertIn("--no-daemon", command)
        self.assertEqual(command[command.index("--sandbox") + 1], "workspace-write")
        self.assertEqual(command[command.index("--add-dir") + 1], str(writes))
        self.assertEqual(command[command.index("--model") + 1], "chosen-model")
        self.assertIn(str(self.run / "prompt.md"), command[-1])
        self.assertTrue(command[-1].startswith("<!-- my-big-brother:analysis -->"))
        self.assertNotIn("Isolated task.", command[-1])

    def test_invalid_mode_and_windows_do_not_fallback(self):
        for value in ("screen", None, [], {}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "mode"):
                codex.validate_settings({"mode": value})
        with patch.object(codex, "os", SimpleNamespace(name="nt")):
            with self.assertRaisesRegex(ValueError, "native Windows"):
                codex.command({"mode": "tmux"}, self.run)

    def test_missing_tmux_does_not_launch_codex(self):
        with patch.object(codex.shutil, "which", return_value=None), \
             patch.object(codex.subprocess, "run") as run:
            with self.assertRaisesRegex(ValueError, "tmux executable not found"):
                codex.launch_tmux(["/tools/codex"], self.run, {})
        run.assert_not_called()

    def test_env_secrets_only_cross_stdin_and_do_not_change_global_env(self):
        secret = "secret '$HOME; # \" \\ \n 确认"
        environment = {"PATH": "/fresh/tools", "HTTPS_PROXY": secret, "TMPDIR": "/fresh/tmp"}
        previous = subprocess.CompletedProcess([], 0, b"HTTPS_PROXY=stale\nOLD_PROXY=old\n", b"")
        created = subprocess.CompletedProcess([], 0, b"", b"")
        with patch.object(codex.shutil, "which", return_value="/tools/tmux"), \
             patch.object(codex.subprocess, "run", side_effect=[previous, created]) as run:
            result = codex.launch_tmux(["/tools/codex", "Task file"], self.run, environment)
        self.assertEqual(result["status"], "session-started")
        self.assertEqual(result["session_name"], "mbb-unique-launch")
        self.assertIn("attach-session", result["attach_command"])
        create = run.call_args_list[1]
        self.assertEqual(create.args[0], ["/tools/tmux", "start-server", ";", "source-file", "-"])
        self.assertEqual(create.kwargs["env"], environment)
        self.assertNotIn(secret, str(create.args))
        script = create.kwargs["input"].decode("utf-8")
        self.assertIn('set-environment -r -t "mbb-unique-launch" "OLD_PROXY"', script)
        self.assertIn('"-e" "PATH=/fresh/tools"', script)
        self.assertIn(codex._tmux_quote("HTTPS_PROXY=" + secret), script)
        self.assertNotIn("set-environment -g", script)
        self.assertLess(script.index("pipe-pane"), script.index("respawn-pane"))
        self.assertEqual(list((self.run / "logs").iterdir()), [self.run / "logs" / "terminal.log"])

    def test_tmux_failure_does_not_expose_secret_or_fallback(self):
        query = subprocess.CompletedProcess([], 1, b"", b"no server")
        failed = subprocess.CompletedProcess([], 1, b"", b"source line contained secret")
        cleanup = subprocess.CompletedProcess([], 0, b"", b"")
        with patch.object(codex.shutil, "which", return_value="/tools/tmux"), \
             patch.object(codex.subprocess, "run", side_effect=[query, failed, cleanup]) as run:
            with self.assertRaisesRegex(ValueError, "tmux session startup failed") as error:
                codex.launch_tmux(["/tools/codex"], self.run, {})
        self.assertNotIn("secret", str(error.exception))
        self.assertEqual(run.call_args_list[2].args[0],
                         ["/tools/tmux", "kill-session", "-t", "mbb-unique-launch"])
        self.assertEqual(run.call_count, 3)

    def test_tmux_launch_never_uses_popen_or_exec_timeout(self):
        expected = {"status": "session-started", "session_name": "mbb-test", "attach_command": "tmux attach"}
        with patch.object(codex.shutil, "which", return_value="/tools/codex"), \
             patch.object(codex, "launch_tmux", return_value=expected) as tmux, \
             patch.object(codex.subprocess, "Popen") as popen:
            result = codex.launch({"mode": "tmux", "timeout_seconds": 1}, self.run, "task", environment={})
        self.assertEqual(result, expected)
        popen.assert_not_called()
        tmux.assert_called_once()
        self.assertEqual(tmux.call_args.args[2], {})
        command = json.loads((self.run / "logs" / "command.json").read_text())
        self.assertNotIn("exec", command)

    def test_automation_returns_session_identity_without_completion_claim(self):
        paths = Paths(self.root / "config", self.root / "data")
        settings = config.initialize(paths, sources=["bash"])
        expected = {"status": "session-started", "session_name": "mbb-test", "attach_command": "tmux attach"}
        with patch.object(codex, "launch", return_value=expected) as launch:
            result = codex.automate(paths, settings, review_date="2020-01-15", mode="tmux")
        self.assertEqual(result["status"], "session-started")
        self.assertNotIn("results", result)
        self.assertEqual(launch.call_args.args[0]["mode"], "tmux")
        environment = launch.call_args.kwargs["environment"]
        launch_dir = Path(result["launch_dir"])
        self.assertEqual(environment["TMPDIR"], str(launch_dir / "tmp"))
        self.assertEqual(runner.read_object(launch_dir / "state.json")["status"], "session-started")
        self.assertFalse((launch_dir / "automation-result.json").exists())
        self.assertEqual(settings["codex"].get("mode", "exec"), "exec")

    def test_cli_passes_explicit_mode(self):
        with patch("my_big_brother.paths.discover"), patch.object(config, "load"), \
             patch.object(codex, "automate", return_value={"status": "session-started"}) as automate, \
             patch("builtins.print"):
            self.assertEqual(codex.main(["--mode", "tmux"]), 0)
        self.assertEqual(automate.call_args.kwargs["mode"], "tmux")


if __name__ == "__main__":
    unittest.main()
