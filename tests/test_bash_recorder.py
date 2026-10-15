"""Exercise recorder hooks in isolated real interactive Bash subprocesses."""

import importlib.util
import io
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
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "collectors" / "bash" / "session-recorder.sh"
HELPER = HOOK.with_name("recorder.py")
spec = importlib.util.spec_from_file_location("bash_recorder", HELPER)
recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recorder)


class BashSessionNamingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.config = self.root / 'config'
        self.data = self.root / 'data'
        locations = patch.object(recorder, 'locations', return_value=(self.config, self.data))
        locations.start()
        self.addCleanup(locations.stop)

    def session(self, pid='12345', cwd=None):
        with patch.object(recorder, 'now', return_value='2026-10-15T09:30:12.123456+08:00'):
            return recorder.new_session(pid, str(cwd or self.root / 'project'))

    def test_same_second_sessions_are_distinguished_by_bash_pid(self):
        first = self.session('12345')
        second = self.session('12346')
        self.assertEqual(first['filename'], '09-30-12_project_12345.jsonl')
        self.assertEqual(second['filename'], '09-30-12_project_12346.jsonl')
        self.assertNotEqual(first['session_id'], second['session_id'])

    def test_existing_filename_is_not_overwritten_or_shared(self):
        first = self.session()
        logfile = self.data / 'daily/2026-10-15/bash' / first['filename']
        logfile.write_text('existing session content')
        second = self.session()
        self.assertNotEqual(first['filename'], second['filename'])
        self.assertNotEqual(first['session_id'], second['session_id'])
        self.assertEqual(logfile.read_text(), 'existing session content')

    def test_directory_hint_is_bounded_and_keeps_unicode_head_and_tail(self):
        name = '首' * 30 + '中' * 30 + '尾' * 30
        session = self.session(cwd=self.root / name)
        label = session['filename'][9:-len('_12345.jsonl')]
        self.assertLessEqual(len(label.encode('utf-8')), 64)
        self.assertTrue(label.startswith('首'))
        self.assertTrue(label.endswith('尾'))
        self.assertEqual(session['session_cwd'], str(self.root / name))
        self.assertEqual(recorder.directory_label(self.root / 'a:b?c*'), 'a_b_c_')
        self.assertEqual(recorder.directory_label(Path('/')), '')

    def test_one_file_survives_midnight_months_and_config_changes(self):
        from my_big_brother.sources import bash

        session = self.session()
        for completed in ('2026-10-16T03:00:00+08:00', '2027-01-15T06:00:00+08:00'):
            fields = [json.dumps(session), completed, str(self.root / 'another-project'),
                      '0', 'printf synthetic', '']
            payload = '\0'.join(fields).encode()
            with patch.object(recorder, 'now', return_value=completed), \
                 patch.object(recorder, 'locations', side_effect=AssertionError('must keep startup storage')), \
                 patch.object(recorder.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(payload))):
                recorder.record()
        logs = list((self.data / 'daily').rglob('*.jsonl'))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].parent.parent.name, '2026-10-15')
        rows = [json.loads(line) for line in logs[0].read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row['session_cwd'] == session['session_cwd'] for row in rows))
        self.assertTrue(all(row['cwd'] == str(self.root / 'another-project') for row in rows))
        start = recorder.dt.datetime.fromisoformat('2027-01-15T04:00:00+08:00')
        end = recorder.dt.datetime.fromisoformat('2027-01-16T04:00:00+08:00')
        result = bash.collect(self.data / 'daily', start, end)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]['completed_at'], rows[-1]['completed_at'])
        self.assertEqual(Path(result.rows[0]['session_path']), logs[0])


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
            events = [json.loads(line) for line in path.read_text().splitlines()]
            rows.extend(events)
            self.assertEqual(path.parent.name, "bash")
            for row in events:
                self.assertEqual(path.parent.parent.name, row["session_started_at"][:10])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        return result, rows, root

    def test_independent_shell_records_without_application_configuration(self):
        result, rows, root = self.shell([], ['printf independent'], initialize=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual([row['command'] for row in rows], ['printf independent'])
        self.assertFalse((root / 'config/my-big-brother').exists())

    def test_session_filename_contains_enable_time_and_actual_shell_pid(self):
        result, rows, root = self.shell([], [
            "printf '%s\\n' \"${BASHPID:-$$}\" > shell-pid", "printf second",
        ])
        self.assertEqual(result.returncode, 0)
        logs = list(root.rglob('*.jsonl'))
        self.assertEqual(len(logs), 1)
        pid = (root / 'shell-pid').read_text().strip()
        enabled = recorder.dt.datetime.fromisoformat(rows[0]['session_started_at'])
        expected = enabled.strftime('%H-%M-%S') + '_' + recorder.directory_label(root) + '_' + pid
        self.assertEqual(logs[0].stem, expected)
        self.assertTrue(all(row['session_id'] == rows[0]['session_id'] for row in rows))
        self.assertTrue(all(row['session_cwd'] == str(root) for row in rows))
        self.assertLessEqual(enabled, recorder.dt.datetime.fromisoformat(rows[0]['started_at']))

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
