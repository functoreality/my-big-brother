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

    def test_existing_filename_is_not_overwritten_or_shared(self):
        first = self.session()
        logfile = self.data / 'daily/2026-10-15/bash' / first['filename']
        logfile.write_text('existing session content')
        second = self.session()
        self.assertNotEqual(first['filename'], second['filename'])
        self.assertEqual(logfile.read_text(), 'existing session content')

    def test_directory_hint_is_bounded_and_keeps_unicode_head_and_tail(self):
        name = '首' * 30 + '中' * 30 + '尾' * 30
        session = self.session(cwd=self.root / name)
        label = session['filename'][9:-len('_12345.jsonl')]
        self.assertLessEqual(len(label.encode('utf-8')), 64)
        self.assertTrue(label.startswith('首'))
        self.assertTrue(label.endswith('尾'))
        event = json.loads((self.data / 'daily/2026-10-15/bash' / session['filename']).read_text())
        self.assertEqual(event['cwd'], str(self.root / name))
        self.assertEqual(recorder.directory_label(self.root / 'a:b?c*'), 'a_b_c_')
        self.assertEqual(recorder.directory_label(Path('/')), '')

    def test_one_file_survives_midnight_months_and_config_changes(self):
        from my_big_brother.sources import bash

        session = self.session()
        for completed in ('2026-10-16T03:00:00+08:00', '2027-01-15T06:00:00+08:00'):
            fields = [json.dumps(session), 'command', str(self.root / 'another-project'),
                      'printf synthetic', '0', str(int(recorder.dt.datetime.fromisoformat(completed).timestamp())), '']
            payload = '\0'.join(fields).encode()
            with patch.object(recorder, 'now', return_value=completed), \
                 patch.object(recorder, 'locations', side_effect=AssertionError('must keep startup storage')), \
                 patch.object(recorder.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(payload))):
                recorder.record()
        logs = list((self.data / 'daily').rglob('*.jsonl'))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].parent.parent.name, '2026-10-15')
        rows = [json.loads(line) for line in logs[0].read_text().splitlines()]
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['event'], 'session_start')
        self.assertEqual(rows[0]['cwd'], str(self.root / 'project'))
        self.assertTrue(all(row['cwd'] == str(self.root / 'another-project') for row in rows[1:]))
        start = recorder.dt.datetime.fromisoformat('2027-01-15T04:00:00+08:00')
        end = recorder.dt.datetime.fromisoformat('2027-01-16T04:00:00+08:00')
        result = bash.collect(self.data / 'daily', start, end)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0]['completed_at'], rows[-1]['completed_at'])
        self.assertEqual(Path(result.rows[0]['session_path']), logs[0])


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "Requires a POSIX Bash environment")
class BashRecorderTests(unittest.TestCase):
    def shell(self, setup, commands, *, initialize=True, recording=True, exit_command=True):
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
        attach = [f"source {shlex.quote(str(HOOK))}"] if recording else []
        script = "\n".join(setup + attach + commands + (["exit", ""] if exit_command else [""]))
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
                self.assertEqual(path.parent.parent.name, events[0]['started_at'][:10])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        return result, [row for row in rows if row["event"] == "command"], root

    def test_independent_shell_records_without_application_configuration(self):
        result, rows, root = self.shell([], ['printf independent'], initialize=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual([row['command'] for row in rows], ['printf independent', 'exit'])
        self.assertFalse((root / 'config/my-big-brother').exists())

    def test_session_filename_contains_enable_time_and_actual_shell_pid(self):
        result, rows, root = self.shell([], [
            "printf '%s\\n' \"${BASHPID:-$$}\" > shell-pid", "printf second",
        ])
        self.assertEqual(result.returncode, 0)
        logs = list(root.rglob('*.jsonl'))
        self.assertEqual(len(logs), 1)
        pid = (root / 'shell-pid').read_text().strip()
        events = [json.loads(line) for line in logs[0].read_text().splitlines()]
        enabled = recorder.dt.datetime.fromisoformat(events[0]['started_at'])
        expected = enabled.strftime('%H-%M-%S') + '_' + recorder.directory_label(root) + '_' + pid
        self.assertEqual(logs[0].stem, expected)
        self.assertEqual(events[0]['event'], 'session_start')
        self.assertEqual(events[0]['cwd'], str(root))
        self.assertEqual(events[-1]['event'], 'session_end')
        self.assertTrue(all('session_id' not in row for row in events))
        self.assertLessEqual(enabled, recorder.dt.datetime.fromisoformat(rows[0]['started_at']))

    def test_history_controls_and_ignore(self):
        for control in ("", "ignoredups", "ignoreboth", "erasedups", "ignoreboth:erasedups"):
            with self.subTest(control=control):
                result, rows, root = self.shell(
                    [f"HISTCONTROL={shlex.quote(control)}", "HISTIGNORE='*excluded-pattern*'"],
                    ["printf repeated", "printf repeated", " printf spaced", "printf excluded-pattern",
                     "printf '%s\\n' \"$HISTCONTROL|$HISTIGNORE\" > settings"],
                )
                expected = ['printf repeated', 'printf repeated']
                expected.extend(['printf spaced', 'printf excluded-pattern'])
                self.assertEqual([r['command'] for r in rows[:len(expected)]], expected)
                self.assertIn('printf excluded-pattern', [r['command'] for r in rows])
                self.assertEqual((root / "settings").read_text().strip(), f"{control}|*excluded-pattern*")
                self.assertEqual(result.returncode, 0)

    def test_status_and_completion_cwd(self):
        result, rows, root = self.shell([], ["false", "mkdir child", "cd child", "printf done"])
        self.assertEqual(rows[0]["exit_status"], 1)
        self.assertEqual(rows[-1]["cwd"], str(root / "child"))
        self.assertEqual(result.returncode, 0)

    def test_native_history_contents_and_settings_are_preserved(self):
        import re

        policies = [('', ''), ('ignoredups', ''), ('erasedups', ''),
                    ('ignoreboth:erasedups', ''), ('', '&'), ('erasedups', '*private*:&'),
                    ('ignorespace', '*'), ('', '*private*')]
        for control, ignore in policies:
            for size in (2, 20):
                with self.subTest(control=control, ignore=ignore, size=size):
                    setup = [f'HISTCONTROL={shlex.quote(control)}',
                             f'HISTIGNORE={shlex.quote(ignore)}', f'HISTSIZE={size}']
                    commands = ['history -c', 'printf alpha', 'printf alpha', 'printf beta',
                                'printf alpha', ' printf spaced', 'printf private',
                                "printf '%s|%s|%s' \"$HISTCONTROL\" \"$HISTIGNORE\" \"$HISTSIZE\" > settings",
                                'builtin history > observed-history']
                    _, _, baseline = self.shell(setup, commands, recording=False)
                    result, rows, root = self.shell(setup, commands)
                    native = (baseline / 'observed-history').read_text()
                    observed = (root / 'observed-history').read_text()
                    strip_numbers = lambda value: re.sub(r'^\s*\d+\s{2}', '', value, flags=re.MULTILINE)
                    self.assertEqual(strip_numbers(observed), strip_numbers(native))
                    self.assertEqual((root / 'settings').read_text(), (baseline / 'settings').read_text())
                    self.assertEqual(sum(row['command'] == 'printf alpha' for row in rows), 3)
                    self.assertEqual(result.returncode, 0)

    def test_disk_history_disabled_or_zero_size_still_records_without_changing_native_history(self):
        import re

        for setting in ('HISTSIZE=0', 'unset HISTFILE', 'HISTFILE=', 'HISTFILESIZE=0'):
            with self.subTest(setting=setting):
                setup = ['HISTCONTROL=ignoredups', "HISTIGNORE='source *'", 'history -c',
                         'history -s previous-entry', setting]
                commands = ['printf repeated', 'printf repeated',
                            "[[ -o history ]]; printf '%s|%s|%s' \"$?\" \"$HISTSIZE\" \"${HISTFILE-unset}\" > settings",
                            'history > observed-history']
                _, _, baseline = self.shell(setup, commands, recording=False)
                result, rows, root = self.shell(setup, commands)
                normalize = lambda value, directory: re.sub(
                    r'^\s*\d+\s{2}', '', value.replace(str(directory), '<HOME>'), flags=re.MULTILINE)
                self.assertEqual(normalize((root / 'observed-history').read_text(), root),
                                 normalize((baseline / 'observed-history').read_text(), baseline))
                self.assertEqual(normalize((root / 'settings').read_text(), root),
                                 normalize((baseline / 'settings').read_text(), baseline))
                saved = lambda directory: (directory / 'history').read_text() if (directory / 'history').exists() else ''
                self.assertEqual(normalize(saved(root), root), normalize(saved(baseline), baseline))
                self.assertEqual(sum(row['command'] == 'printf repeated' for row in rows), 2)
                self.assertEqual(result.returncode, 0)

    def test_history_can_be_disabled_and_enabled_during_a_recorded_session(self):
        result, rows, root = self.shell([], ['set +o history', 'printf disabled',
            'HISTSIZE=0', 'printf zero', 'HISTSIZE=20', 'set -o history',
            'printf enabled', 'history > observed-history'])
        recorded = [row['command'] for row in rows]
        self.assertNotIn('printf disabled', recorded)
        self.assertNotIn('printf zero', recorded)
        self.assertIn('printf enabled', recorded)
        self.assertNotIn('printf disabled', (root / 'observed-history').read_text())
        self.assertNotIn('printf zero', (root / 'observed-history').read_text())
        self.assertEqual(result.returncode, 0)

    def test_history_disabled_is_an_explicit_capture_gap(self):
        result, rows, root = self.shell(['set +o history'], ['printf disabled'])
        self.assertEqual(rows, [])
        events = [json.loads(line) for path in root.rglob('*.jsonl')
                  for line in path.read_text().splitlines()]
        self.assertEqual([event['event'] for event in events], ['session_start', 'session_end'])
        self.assertEqual(result.returncode, 0)

    def test_original_exit_hook_observes_original_settings_on_eof(self):
        setup = ["HISTCONTROL=ignoreboth", "HISTIGNORE='*excluded*'", 'HISTSIZE=2',
                 "trap 'printf \"%s|%s|%s\" \"$HISTCONTROL\" \"$HISTIGNORE\" \"$HISTSIZE\" > exit-settings' EXIT"]
        # A final comment reaches EOF without running a command or its preexec hook.
        result, rows, root = self.shell(setup, ['# EOF observation'], exit_command=False)
        self.assertEqual((root / 'exit-settings').read_text(), 'ignoreboth|*excluded*|2')
        self.assertEqual(result.returncode, 0)

    def test_event_fields_match_legacy_without_repeated_session_metadata(self):
        result, rows, root = self.shell([], ['false', 'exit 7'])
        events = [json.loads(line) for path in root.rglob('*.jsonl')
                  for line in path.read_text().splitlines()]
        self.assertEqual(set(events[0]), {'event', 'started_at', 'cwd'})
        self.assertEqual(set(events[-1]), {'event', 'ended_at', 'cwd'})
        self.assertEqual(events[0]['event'], 'session_start')
        self.assertEqual(events[-1]['event'], 'session_end')
        for row in rows:
            self.assertEqual(set(row), {'event', 'started_at', 'completed_at', 'cwd',
                                        'command', 'exit_status'})
        self.assertEqual(rows[-1]['command'], 'exit 7')
        self.assertEqual(rows[-1]['exit_status'], 7)
        self.assertEqual(result.returncode, 7)

    def test_multiline_and_compound_inputs_are_complete(self):
        for lithist in (False, True):
            with self.subTest(lithist=lithist):
                setup = ['shopt -s cmdhist', 'shopt ' + ('-s' if lithist else '-u') + ' lithist']
                result, rows, root = self.shell(setup, ['printf first; printf second',
                    'for item in alpha beta', 'do', '  printf "%s\\n" "$item"', 'done'])
                self.assertEqual(rows[0]['command'], 'printf first; printf second')
                loop = rows[1]['command']
                self.assertIn('for item in alpha beta', loop)
                self.assertIn('printf', loop)
                self.assertIn('done', loop)
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
        self.assertEqual([r["command"] for r in rows], ["false", "printf success", "exit"])

    def test_prompt_comments_and_function(self):
        result, rows, root = self.shell(
            ["user_prompt() { printf '%s\\n' \"$?\" >> status; }",
             "PROMPT_COMMAND='user_prompt # preserve this comment'"],
            ["false", "printf success"],
        )
        self.assertIn("1", (root / "status").read_text().splitlines())
        self.assertEqual([r["command"] for r in rows], ["false", "printf success", "exit"])

    def test_preserves_existing_debug_and_exit_hooks(self):
        result, rows, root = self.shell(
            ["trap 'printf debug >> debug-marker' DEBUG",
             "trap 'printf exit > exit-marker' EXIT"],
            ["printf user", "trap -p DEBUG > debug-trap"],
        )
        self.assertNotIn("recorder not attached", result.stderr)
        self.assertIn("printf user", [row["command"] for row in rows])
        self.assertIn("printf debug", (root / "debug-trap").read_text())
        self.assertEqual((root / "exit-marker").read_text(), "exit")

    def test_functrace_and_ps0_remain_usable(self):
        for setting in ('set -T', 'PS0=precommand'):
            with self.subTest(setting=setting):
                result, rows, root = self.shell([setting], ['printf user'])
                self.assertEqual([row['command'] for row in rows], ['printf user', 'exit'])
                self.assertEqual(result.returncode, 0)

    def test_declines_readonly_prompt(self):
        result, rows, root = self.shell(["readonly PROMPT_COMMAND='printf prompt'"], ['printf user'])
        self.assertIn('recorder not attached', result.stderr)
        self.assertEqual(rows, [])

    def test_repeated_source_and_compound_scope(self):
        result, rows, root = self.shell([], [f"source {shlex.quote(str(HOOK))}", "printf first; printf second"])
        matches = [r for r in rows if r["command"] == "printf first; printf second"]
        self.assertEqual(len(matches), 1)
        self.assertNotIn("capture_scope", matches[0])

    def test_redaction_and_disable(self):
        result, rows, root = self.shell([], ["TOKEN=secret", "MBB_BASH_RECORDING=0", "printf private",
                                            "MBB_BASH_RECORDING=1", "printf public"])
        self.assertEqual(rows[0]["command"], "<redacted:possible-secret>")
        self.assertFalse(any("private" in r["command"] for r in rows))
        self.assertIn("printf public", [row["command"] for row in rows])

    def test_shared_storage_path_spaces_and_missing_configuration(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "config" / "my-big-brother"
            target = root / "data space"
            with patch.object(recorder, "locations", return_value=(config, target)):
                session = recorder.new_session('12345', str(root))
                self.assertTrue((target / 'daily' / session['date'] / 'bash' / session['filename']).is_file())
                self.assertFalse((config / 'storage.json').exists())
                recorder._storage.Layout.install(config, target)
                self.assertEqual(recorder.new_session('12346', str(root))['storage_settings']['data_root'], str(target))
                (config / 'storage.json').write_text('{broken')
                with self.assertRaises(ValueError):
                    recorder.new_session('12347', str(root))

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
                release = base / 'release'
                os.write(master, (f"source {shlex.quote(str(HOOK))}\n"
                                  f"while [[ ! -f {shlex.quote(str(release))} ]]; do sleep 0.01; done\n").encode())
                deadline = time.monotonic() + 5
                logs = []
                while not logs and time.monotonic() < deadline:
                    logs = list(base.rglob('*.jsonl'))
                    time.sleep(0.01)
                self.assertTrue(logs)
                events = [json.loads(line) for line in logs[0].read_text().splitlines()]
                self.assertEqual([row['event'] for row in events], ['session_start'])
                self.assertIsNone(process.poll())
                release.touch()
                os.write(master, b"HISTCONTROL=ignoredups\nprintf terminal\nprintf terminal\nexit\n")
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
            self.assertEqual(sum(r.get("command") == "printf terminal" for r in rows), 2)


if __name__ == "__main__":
    unittest.main()
