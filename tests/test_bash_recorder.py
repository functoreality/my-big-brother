"""Exercise recorder hooks in isolated real interactive Bash subprocesses."""

import importlib.util
import json
import os
from pathlib import Path
import select
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "collectors" / "bash" / "session-recorder.sh"
HELPER = HOOK.with_name("recorder.py")
spec = importlib.util.spec_from_file_location("bash_recorder", HELPER)
recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recorder)


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "Requires a POSIX Bash environment")
class BashRecorderTests(unittest.TestCase):
    def shell(self, setup, commands, *, initialize=True):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        if initialize:
            recorder._storage.Layout.install(root / "config/my-big-brother", root / "data/my-big-brother")
        env = os.environ.copy()
        env.update(
            HOME=str(root), XDG_CONFIG_HOME=str(root / "config"),
            XDG_DATA_HOME=str(root / "data"), HISTFILE=str(root / "history"),
            MBB_PYTHON=sys.executable, PS1="", MBB_BASH_RECORDING="1",
        )
        env.pop("PROMPT_COMMAND", None)
        env.pop("BASH_ENV", None)
        script = "\n".join(setup + [f"source {shlex.quote(str(HOOK))}"] + commands + ["exit", ""])
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-i"], input=script,
            text=True, env=env, cwd=root, capture_output=True, timeout=15,
        )
        rows = []
        for path in root.rglob("*.jsonl"):
            rows.extend(json.loads(line) for line in path.read_text().splitlines())
            self.assertEqual(path.parent.name, "bash")
            self.assertEqual(path.parent.parent.name, rows[-1]["completed_at"][:10])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        return result, rows, root

    def test_independent_shell_records_without_application_configuration(self):
        result, rows, root = self.shell([], ['printf independent'], initialize=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual([row['command'] for row in rows], ['printf independent'])
        self.assertFalse((root / 'config/my-big-brother').exists())

    def test_history_controls_and_ignore(self):
        for control in ("", "ignoredups", "ignoreboth", "erasedups", "ignoreboth:erasedups"):
            with self.subTest(control=control):
                result, rows, root = self.shell(
                    [f"HISTCONTROL={shlex.quote(control)}", "HISTIGNORE='printf*'"],
                    ["printf repeated", "printf repeated", " printf spaced",
                     "printf '%s\\n' \"$HISTCONTROL|$HISTIGNORE\" > settings"],
                )
                self.assertEqual([r["command"] for r in rows[:3]],
                                 ["printf repeated", "printf repeated", "printf spaced"])
                self.assertEqual((root / "settings").read_text().strip(), f"{control}|printf*")
                self.assertEqual(result.returncode, 0)

    def test_history_disabled_status_and_cwd(self):
        result, rows, root = self.shell(["set +o history"], ["false", "mkdir child", "cd child", "printf done"])
        self.assertEqual(rows[0]["exit_status"], 1)
        self.assertEqual(rows[-1]["cwd"], str(root / "child"))
        self.assertEqual(result.returncode, 0)

    def test_existing_string_prompt_and_exit_trap_keep_status(self):
        result, rows, root = self.shell(
            ["PROMPT_COMMAND='printf \"%s\\n\" \"$?\" >> prompt-status'",
             "trap 'printf \"%s\\n\" \"$?\" > exit-status' EXIT", "umask 027"],
            ["false", "umask > umask-value", "exit 7"],
        )
        self.assertEqual(result.returncode, 7)
        self.assertEqual((root / "exit-status").read_text().strip(), "7")
        self.assertIn("1", (root / "prompt-status").read_text().splitlines())
        self.assertEqual((root / "umask-value").read_text().strip(), "0027")
        self.assertEqual(rows[0]["exit_status"], 1)
        self.assertFalse(any(r["command"].startswith("printf \"%s") for r in rows))

    def test_array_prompt(self):
        version = subprocess.check_output(["bash", "-c", "printf '%s.%s' \"${BASH_VERSINFO[0]}\" \"${BASH_VERSINFO[1]}\""], text=True)
        if tuple(int(part) for part in version.split(".")) < (5, 1):
            self.skipTest("Array PROMPT_COMMAND requires Bash 5.1+")
        result, rows, root = self.shell(
            ["PROMPT_COMMAND=('printf \"%s\\n\" \"$?\" >> status' 'printf second >> hook')"],
            ["false", "printf success"],
        )
        self.assertIn("1", (root / "status").read_text().splitlines())
        self.assertIn("second", (root / "hook").read_text())
        self.assertEqual([r["command"] for r in rows], ["false", "printf success"])

    def test_prompt_comments_and_function(self):
        result, rows, root = self.shell(
            ["user_prompt() { printf '%s\\n' \"$?\" >> status; }",
             "PROMPT_COMMAND='user_prompt # preserve this comment'"],
            ["false", "printf success"],
        )
        self.assertIn("1", (root / "status").read_text().splitlines())
        self.assertEqual([r["command"] for r in rows], ["false", "printf success"])

    def test_declines_existing_debug_without_overwriting(self):
        result, rows, root = self.shell(
            ["trap 'printf debug >> debug-marker' DEBUG",
             "trap 'printf exit > exit-marker' EXIT"],
            ["printf user", "trap -p DEBUG > debug-trap"],
        )
        self.assertIn("recorder not attached", result.stderr)
        self.assertEqual(rows, [])
        self.assertIn("printf debug", (root / "debug-trap").read_text())
        self.assertEqual((root / "exit-marker").read_text(), "exit")

    def test_declines_functrace_ps0_and_readonly_prompt(self):
        for setting in ("set -T", "PS0=precommand", "readonly PROMPT_COMMAND='printf prompt'"):
            with self.subTest(setting=setting):
                result, rows, root = self.shell([setting], ["printf user"])
                self.assertIn("recorder not attached", result.stderr)
                self.assertEqual(rows, [])

    def test_repeated_source_and_compound_scope(self):
        result, rows, root = self.shell([], [f"source {shlex.quote(str(HOOK))}", "printf first; printf second"])
        matches = [r for r in rows if r["command"] == "printf first"]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["capture_scope"], "first-simple-command")

    def test_redaction_and_disable(self):
        result, rows, root = self.shell([], ["TOKEN=secret", "MBB_BASH_RECORDING=0", "printf private",
                                            "MBB_BASH_RECORDING=1", "printf public"])
        self.assertTrue(rows[0]["redacted"])
        self.assertNotIn("secret", rows[0]["command"].replace("possible secret", ""))
        self.assertFalse(any("private" in r["command"] for r in rows))
        self.assertEqual(rows[-1]["command"], "printf public")

    def test_shared_storage_path_spaces_and_missing_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config" / "my-big-brother"
            target = root / "data space"
            with patch.object(recorder, "locations", return_value=(config, target)):
                self.assertEqual(recorder.daily_root(), target / 'daily')
                self.assertFalse((config / 'storage.json').exists())
                recorder._storage.Layout.install(config, target)
                self.assertEqual(recorder.daily_root(), target / 'daily')
                (config / 'storage.json').write_text('{broken')
                with self.assertRaises(ValueError):
                    recorder.daily_root()

    @unittest.skipIf(os.name == "nt", "PTY test requires POSIX")
    def test_real_terminal_repeated_commands(self):
        import pty

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            recorder._storage.Layout.install(base / "config/my-big-brother", base / "data/my-big-brother")
            env = os.environ.copy()
            env.update(HOME=temporary, XDG_CONFIG_HOME=temporary + "/config",
                       XDG_DATA_HOME=temporary + "/data", HISTFILE=temporary + "/history",
                       MBB_PYTHON=sys.executable, PS1="MBB_TEST_PROMPT> ", MBB_BASH_RECORDING="1")
            env.pop("PROMPT_COMMAND", None)
            master, slave = pty.openpty()
            process = subprocess.Popen(["bash", "--noprofile", "--norc", "-i"],
                                       stdin=slave, stdout=slave, stderr=slave, env=env)
            os.close(slave)
            try:
                os.write(master, (f"source {shlex.quote(str(HOOK))}\n"
                                  "HISTCONTROL=ignoredups\nprintf terminal\nprintf terminal\nexit\n").encode())
                deadline = time.monotonic() + 15
                while process.poll() is None and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.1)[0]:
                        try:
                            os.read(master, 65536)
                        except OSError:
                            break
                process.wait(timeout=2)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                os.close(master)
            rows = [json.loads(line) for p in Path(temporary).rglob("*.jsonl")
                    for line in p.read_text().splitlines()]
            self.assertEqual(sum(r["command"] == "printf terminal" for r in rows), 2)


if __name__ == "__main__":
    unittest.main()
