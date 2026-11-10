"""Exercise Zsh hooks using isolated interactive shells and a real terminal."""

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
HOOK = ROOT / 'collectors/zsh/session-recorder.zsh'
HELPER = HOOK.with_name('recorder.py')
spec = importlib.util.spec_from_file_location('zsh_recorder', HELPER)
recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recorder)


class ZshWriterTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.config = self.root / 'config'
        self.data = self.root / 'data'
        locations = patch.object(recorder._paths, 'platform_paths', return_value=(self.config, self.data))
        locations.start()
        self.addCleanup(locations.stop)

    def session(self, pid='12345'):
        with patch.object(recorder, 'now', return_value='2026-10-15T09:30:12+08:00'):
            return Path(recorder.new_session(pid, str(self.root / 'project')))

    def append(self, filename, command='printf synthetic', completed='2027-01-15T06:00:00+08:00'):
        fields = [str(filename), 'command', str(self.root / 'another directory'),
                  command, '3', '1799999999', '']
        with patch.object(recorder, 'now', return_value=completed), \
                patch.object(recorder._paths, 'platform_paths', side_effect=AssertionError('startup storage frozen')), \
                patch.object(recorder.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO('\0'.join(fields).encode()))):
            recorder.record()

    def test_fixed_natural_date_path_collision_and_private_file(self):
        first = self.session()
        second = self.session()
        self.assertEqual(first.relative_to(self.data).as_posix(),
                         'raw-logs/2026-10-15/zsh/09-30-12_project_12345.jsonl')
        self.assertNotEqual(first, second)
        self.append(first)
        events = [json.loads(line) for line in first.read_text().splitlines()]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1]['completed_at'], '2027-01-15T06:00:00+08:00')
        self.assertEqual(events[1]['exit_status'], 3)
        self.assertEqual(first.stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.config.exists())

    def test_missing_file_is_not_recreated(self):
        first = self.session()
        first.rename(first.with_suffix('.archived'))
        self.append(first)
        self.assertFalse(first.exists())

    def test_locator_preserves_spaces_and_rejects_malformed_values(self):
        self.config.mkdir()
        locator = self.config / 'raw-logs-path.txt'
        target = self.root / 'logs with spaces'
        locator.write_bytes((str(target) + '\r\n').encode())
        self.assertEqual(self.session().parents[2], target)
        for invalid in ('', 'relative', str(target) + '\nextra', '"' + str(target) + '"'):
            with self.subTest(invalid=invalid):
                locator.write_text(invalid)
                with self.assertRaises(ValueError):
                    self.session()

    def test_directory_hint_is_bounded_and_keeps_unicode_head_and_tail(self):
        label = recorder.directory_label(self.root / ('首' * 30 + '中' * 30 + '尾' * 30))
        self.assertLessEqual(len(label.encode('utf-8')), 64)
        self.assertTrue(label.startswith('首'))
        self.assertTrue(label.endswith('尾'))
        self.assertEqual(recorder.directory_label(self.root / 'dir:a?b*'), 'dir_a_b_')

    def test_command_is_json_escaped_and_redaction_matches_bash_policy(self):
        filename = self.session()
        self.append(filename, ' printf "中文\\n"\n# tail')
        self.append(filename, 'API_KEY=synthetic')
        events = [json.loads(line) for line in filename.read_text().splitlines()]
        self.assertEqual(events[1]['command'], ' printf "中文\\n"\n# tail')
        self.assertEqual(events[2]['command'], '<redacted:possible-secret>')
        self.assertEqual((HOOK.with_name('paths.py')).read_bytes(),
                         (ROOT / 'my_big_brother/collector_paths.py').read_bytes())


@unittest.skipUnless(os.name == 'posix' and shutil.which('zsh'), 'Requires POSIX Zsh')
class ZshRecorderTests(unittest.TestCase):
    def shell(self, commands, setup=(), recording=True, exit_command=True):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name).resolve()
        env = os.environ.copy()
        env.update(HOME=str(root), ZDOTDIR=str(root), XDG_CONFIG_HOME=str(root / 'config'),
                   XDG_DATA_HOME=str(root / 'data'), MBB_PYTHON=sys.executable,
                   MBB_ZSH_RECORDING='1', HISTFILE=str(root / 'history'),
                   TERM='dumb')
        attach = ['source ' + shlex.quote(str(HOOK))] if recording else []
        script = '\n'.join(['PS1= PS2= RPS1=', 'unsetopt promptcr promptsp', *setup,
                            *attach, *commands, *(['exit'] if exit_command else []), ''])
        result = subprocess.run(['zsh', '-dfi'], input=script, text=True, env=env,
                                cwd=root, capture_output=True, timeout=20)
        events = []
        for path in root.rglob('*.jsonl'):
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(path.parent.name, 'zsh')
            self.assertEqual(path.parent.parent.name, rows[0]['started_at'][:10])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            events.extend(rows)
        return result, events, root

    def commands(self, events):
        return [row for row in events if row['event'] == 'command']

    def test_independent_recording_and_session_boundaries(self):
        result, events, root = self.shell(['printf independent'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([event['event'] for event in events],
                         ['session_start', 'command', 'command', 'session_end'])
        self.assertEqual([row['command'] for row in self.commands(events)], ['printf independent', 'exit'])
        self.assertFalse(any(root.rglob('config.json')))
        self.assertEqual(set(events[0]), {'event', 'started_at', 'cwd'})
        self.assertEqual(set(events[-1]), {'event', 'ended_at', 'cwd'})
        self.assertEqual(set(events[1]), {'event', 'started_at', 'completed_at', 'cwd', 'command', 'exit_status'})
        for event in events:
            timestamp = event.get('completed_at', event.get('started_at', event.get('ended_at')))
            self.assertIsNotNone(recorder.dt.datetime.fromisoformat(timestamp).utcoffset())

    def test_filename_uses_recorded_clock_directory_and_actual_shell_pid(self):
        result, events, root = self.shell(['print -r -- "$$" > shell-pid'])
        logs = list(root.rglob('*.jsonl'))
        self.assertEqual(len(logs), 1)
        started = recorder.dt.datetime.fromisoformat(events[0]['started_at'])
        expected = (started.strftime('%H-%M-%S') + '_' + recorder.directory_label(root)
                    + '_' + (root / 'shell-pid').read_text().strip())
        self.assertEqual(logs[0].stem, expected)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_before_execution_cwd_and_exit_status(self):
        result, events, root = self.shell(['false', 'mkdir child', 'cd child',
            'pwd > observed', 'cd missing', 'cd ..; printf compound', 'cd child; exit 7'])
        rows = {row['command']: row for row in self.commands(events)}
        self.assertEqual(rows['false']['exit_status'], 1)
        self.assertEqual(rows['cd child']['cwd'], str(root))
        self.assertEqual(rows['pwd > observed']['cwd'], str(root / 'child'))
        self.assertEqual(rows['cd missing']['cwd'], str(root / 'child'))
        self.assertNotEqual(rows['cd missing']['exit_status'], 0)
        self.assertEqual(rows['cd ..; printf compound']['cwd'], str(root / 'child'))
        self.assertEqual(rows['cd child; exit 7']['cwd'], str(root))
        self.assertEqual(rows['cd child; exit 7']['exit_status'], 7)
        self.assertEqual(events[-1]['cwd'], str(root / 'child'))
        self.assertEqual(result.returncode, 7)

    def test_multiline_compound_alias_and_heredoc_inputs(self):
        result, events, root = self.shell(['printf first; printf second',
            'for item in alpha beta', 'do', '  printf "%s\\n" "$item"', 'done',
            'cat > heredoc <<\'END\'', 'synthetic text', 'END', 'll'],
            setup=["alias ll='printf expanded'"])
        rows = self.commands(events)
        self.assertEqual(rows[0]['command'], 'printf first; printf second')
        self.assertIn('for item in alpha beta\ndo\n', rows[1]['command'])
        self.assertIn('done', rows[1]['command'])
        self.assertIn('synthetic text', rows[2]['command'])
        self.assertEqual(rows[3]['command'], 'll')
        self.assertEqual((root / 'heredoc').read_text(), 'synthetic text\n')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_history_filters_zero_size_and_no_file_do_not_hide_inputs(self):
        for setup in (['setopt hist_ignore_dups hist_ignore_space'], ['HISTSIZE=0'],
                      ['unset HISTFILE'], ['SAVEHIST=0'],
                      ['zshaddhistory() { return 1; }']):
            with self.subTest(setup=setup):
                result, events, root = self.shell(['printf repeated', 'printf repeated', ' printf spaced'], setup=setup)
                rows = [row['command'] for row in self.commands(events)]
                self.assertEqual(rows.count('printf repeated'), 2)
                self.assertIn(' printf spaced', rows)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_history_and_options_match_without_recorder(self):
        for policy in ('hist_ignore_dups hist_ignore_space', 'hist_ignore_all_dups', 'hist_no_store'):
            with self.subTest(policy=policy):
                setup = ['HISTSIZE=20 SAVEHIST=20', 'setopt ' + policy,
                         "zshaddhistory() { [[ $1 == source* ]] && return 1; return 0; }"]
                commands = ['printf repeated', 'printf repeated', ' printf spaced',
                            'printf other', 'fc -ln 1 > observed-history', 'setopt > observed-options']
                baseline, _, base = self.shell(commands, setup=setup, recording=False)
                result, events, root = self.shell(commands, setup=setup)
                self.assertEqual((root / 'observed-history').read_text(), (base / 'observed-history').read_text())
                self.assertEqual((root / 'observed-options').read_text(), (base / 'observed-options').read_text())
                self.assertEqual(result.returncode, baseline.returncode)

    def test_already_loaded_add_zsh_hook_does_not_block_attachment(self):
        result, events, root = self.shell(['printf recorded'], setup=[
            'autoload -Uz add-zsh-hook',
            'existing_prompt() { print -r -- "existing" >> prompt-marker; }',
            'add-zsh-hook precmd existing_prompt'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('Zsh recorder not attached', result.stderr)
        self.assertEqual([row['command'] for row in self.commands(events)],
                         ['printf recorded', 'exit'])
        self.assertIn('existing', (root / 'prompt-marker').read_text())

    def test_missing_hook_loader_does_not_claim_attachment_and_can_retry(self):
        result, events, root = self.shell([
            'print -r -- "${__mbbz_attached:-0}" > attachment-before',
            'fpath=($saved_fpath)', 'source ' + shlex.quote(str(HOOK)),
            'printf recovered'], setup=['saved_fpath=($fpath)', 'fpath=()'])
        self.assertEqual((root / 'attachment-before').read_text().strip(), '0')
        self.assertIn('Zsh recorder not attached', result.stderr)
        self.assertEqual([row['command'] for row in self.commands(events)], ['printf recovered', 'exit'])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_existing_named_and_array_hooks_keep_status_and_order(self):
        setup = [
            "precmd() { print -r -- \"named:$?\" >> prompt-status; }",
            "existing_prompt() { print -r -- \"array:$?\" >> prompt-status; }",
            "preexec() { print -r -- \"named:$1\" >> command-hooks; }",
            "existing_preexec() { print -r -- \"array:$1\" >> command-hooks; }",
            "zshexit() { print -r -- \"named:$?\" >> exit-status; }",
            "existing_exit() { print -r -- \"array:$?\" >> exit-status; }",
            'precmd_functions=(existing_prompt)', 'preexec_functions=(existing_preexec)',
            'zshexit_functions=(existing_exit)', 'umask 027',
        ]
        result, events, root = self.shell(['false', 'umask > umask-value', 'exit 7'], setup=setup)
        self.assertEqual(result.returncode, 7)
        self.assertIn('named:1\narray:1', (root / 'prompt-status').read_text())
        self.assertEqual((root / 'exit-status').read_text(), 'named:7\narray:7\n')
        self.assertIn('named:false\narray:false', (root / 'command-hooks').read_text())
        self.assertEqual((root / 'umask-value').read_text().strip(), '027')
        self.assertEqual(self.commands(events)[0]['exit_status'], 1)
        self.assertFalse(any(row['command'].startswith('print -r') for row in self.commands(events)))

    def test_prompt_changes_directory_before_next_command(self):
        result, events, root = self.shell(['cd ..', 'printf after-prompt'], setup=[
            'mkdir prompt-directory', 'precmd() { cd "$HOME/prompt-directory"; }'])
        rows = self.commands(events)
        self.assertEqual(rows[0]['cwd'], str(root / 'prompt-directory'))
        self.assertEqual(rows[1]['cwd'], str(root / 'prompt-directory'))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pause_resume_redaction_and_repeated_source(self):
        result, events, root = self.shell(['TOKEN=synthetic', 'MBB_ZSH_RECORDING=0',
            'printf private', 'MBB_ZSH_RECORDING=1', 'printf public',
            'source ' + shlex.quote(str(HOOK)), 'printf once'])
        rows = [row['command'] for row in self.commands(events)]
        self.assertEqual(rows[0], '<redacted:possible-secret>')
        self.assertNotIn('printf private', rows)
        self.assertIn('printf public', rows)
        self.assertEqual(rows.count('printf once'), 1)
        self.assertEqual(sum(row['event'] == 'session_start' for row in events), 1)
        self.assertEqual(sum(row['event'] == 'session_end' for row in events), 1)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_disabled_at_attach_and_noninteractive_shell_do_not_record(self):
        result, events, root = self.shell(['printf unrecorded'], setup=['MBB_ZSH_RECORDING=0'])
        self.assertEqual(events, [])
        noninteractive = subprocess.run(['zsh', '-dfc', 'source ' + shlex.quote(str(HOOK))],
                                        capture_output=True, text=True, timeout=10)
        self.assertEqual(noninteractive.returncode, 0, noninteractive.stderr)
        self.assertEqual(result.returncode, 0)

    def test_readonly_hook_array_declines_without_partial_attachment(self):
        result, events, root = self.shell(['printf usable'], setup=[
            'typeset -ar precmd_functions=()'])
        self.assertEqual(events, [])
        self.assertIn('Zsh recorder not attached', result.stderr)
        self.assertEqual(result.returncode, 0)

    def test_eof_records_boundary_and_exec_does_not_fabricate_completion(self):
        result, events, root = self.shell(['false'], exit_command=False)
        self.assertEqual([row['event'] for row in events], ['session_start', 'command', 'session_end'])
        self.assertEqual(self.commands(events)[0]['exit_status'], 1)
        replaced, replaced_events, _ = self.shell(['exec /bin/sh -c \'exit 7\''], exit_command=False)
        self.assertEqual(replaced.returncode, 7)
        self.assertEqual([row['event'] for row in replaced_events], ['session_start'])

    def test_real_terminal_records_repeated_and_filtered_commands(self):
        import pty

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            env = os.environ.copy()
            env.update(HOME=str(root), ZDOTDIR=str(root), XDG_CONFIG_HOME=str(root / 'config'),
                       XDG_DATA_HOME=str(root / 'data'), MBB_PYTHON=sys.executable,
                       MBB_ZSH_RECORDING='1', TERM='dumb')
            master, slave = pty.openpty()
            process = subprocess.Popen(['zsh', '-dfi'], stdin=slave, stdout=slave, stderr=slave,
                                       cwd=root, env=env)
            os.close(slave)
            try:
                script = ('PS1= PS2= RPS1=\nsource ' + shlex.quote(str(HOOK)) + '\n'
                          'setopt hist_ignore_dups hist_ignore_space\nprintf terminal\n'
                          'printf terminal\n printf spaced\nexit\n')
                os.write(master, script.encode())
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
            rows = [json.loads(line) for path in root.rglob('*.jsonl') for line in path.read_text().splitlines()]
            self.assertEqual(sum(row.get('command') == 'printf terminal' for row in rows), 2)
            self.assertTrue(any(row.get('command') == ' printf spaced' for row in rows))
            self.assertEqual(rows[-1]['event'], 'session_end')


if __name__ == '__main__':
    unittest.main()
