"""Zsh input selection, analysis windows and preparation with isolated evidence."""

import contextlib
from datetime import datetime, timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from my_big_brother import capture, config, runner
from my_big_brother import __main__ as cli
from my_big_brother.paths import Paths
from my_big_brother.sources import zsh


class ZshSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.paths = Paths(self.root / 'config', self.root / 'data')
        self.settings = config.initialize(self.paths, sources=['zsh'], day_start_hour=4)
        self.start = datetime(2020, 1, 15, 4).astimezone()
        self.end = self.start + timedelta(days=1)

    def events(self, relative, values):
        path = self.paths.raw_logs / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(json.dumps(value) + '\n' for value in values), encoding='utf-8')
        return path

    def command(self, text, instant):
        return {'event': 'command', 'command': text, 'cwd': '/synthetic/project',
                'started_at': instant.isoformat(), 'completed_at': instant.isoformat(), 'exit_status': 0}

    def test_old_start_date_context_and_half_open_window(self):
        old = self.start - timedelta(days=90)
        file = self.events('2019-10-17/zsh/long-lived.jsonl', [
            {'event': 'session_start', 'started_at': old.isoformat(), 'cwd': '/synthetic/initial'},
            self.command('old command', old + timedelta(hours=1)),
            self.command('first', self.start),
            self.command('last', self.end - timedelta(seconds=1)),
            self.command('outside', self.end)])
        original = file.read_bytes()
        result = zsh.collect(self.paths.raw_logs, self.start, self.end)
        self.assertEqual(result.status, 'ok')
        self.assertEqual([row['content'] for row in result.rows], ['first', 'last'])
        for row in result.rows:
            self.assertEqual(row['session_context_status'], 'outside_window')
            self.assertEqual(row['session_context']['cwd'], '/synthetic/initial')
            self.assertTrue(row['session_context']['outside_window'])
            self.assertEqual(row['timestamp_semantics'], 'completed_at')
        self.assertEqual(file.read_bytes(), original)

    def test_explicit_root_reads_only_date_zsh_layout(self):
        for name in ('loose.jsonl', 'zsh/flat.jsonl', '2020-01-15/bash/other.jsonl',
                     '2020-01-15/zsh/nested/extra.jsonl'):
            self.events(name, [self.command('excluded', self.start)])
        self.events('2020-01-15/zsh/expected.jsonl', [self.command('included', self.start)])
        rows = zsh.collect(self.paths.raw_logs, self.start, self.end).rows
        self.assertEqual([row['content'] for row in rows], ['included'])
        self.assertEqual(rows[0]['session_context_status'], 'not_recorded')

    def test_malformed_or_partial_records_report_gaps_with_source_name(self):
        path = self.events('2020-01-15/zsh/partial.jsonl', [
            [], {'event': 'command', 'completed_at': 'bad'}, self.command('valid', self.start)])
        with path.open('a') as handle:
            handle.write('{"event":')
        result = zsh.collect(self.paths.raw_logs, self.start, self.end)
        self.assertEqual(result.status, 'partial')
        self.assertEqual([row['content'] for row in result.rows], ['valid'])
        self.assertEqual(len(result.gaps), 3)
        self.assertTrue(all('Zsh' in gap for gap in result.gaps))

    def test_missing_source_never_creates_files(self):
        path = self.root / 'missing'
        self.assertEqual(zsh.collect(path, self.start, self.end).status, 'unavailable')
        self.assertFalse(path.exists())

    def test_zsh_is_opt_in_and_upgrade_preserves_restricted_sources(self):
        self.assertFalse(config.defaults(self.paths)['sources']['zsh']['enabled'])
        self.assertEqual(set(config.load(self.paths)['sources']), {'zsh'})
        self.settings['sources'] = {'codex': {'enabled': False}}
        config.write_json(self.paths.config / 'config.json', self.settings)
        self.assertEqual(set(config.load(self.paths)['sources']), {'codex'})

    def test_capture_path_accepts_zsh_without_changing_logical_day(self):
        instant = datetime(2020, 1, 15, 2).astimezone()
        value = capture.directory(self.paths, 'zsh', instant)
        self.assertEqual(value['date'], '2020-01-15')
        self.assertEqual(Path(value['directory']).parts[-2:], ('2020-01-15', 'zsh'))

    def test_doctor_requires_actual_zsh_record_files(self):
        for present in (False, True):
            if present:
                self.events('2020-01-15/zsh/session.jsonl', [self.command('sample', self.start)])
            with patch.object(cli, 'discover', return_value=self.paths), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(cli.main(['doctor']), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result['sources']['zsh']['records_present'], present)
            self.assertEqual(bool(result['warnings']), not present)

    def test_prepare_indexes_zsh_without_launching_agent(self):
        self.events('2020-01-15/zsh/sample.jsonl', [self.command('printf synthetic', self.start)])
        result = runner.prepare_run(self.paths, self.settings, '2020-01-15')
        run = Path(result['run_dir'])
        manifest = runner.read_object(run / 'manifest.json')
        self.assertEqual(manifest['sources']['zsh']['entries'], 1)
        self.assertEqual(manifest['sources']['zsh']['status'], 'ok')
        index = Path(manifest['sources']['zsh']['index'])
        row = json.loads(index.read_text().strip())
        self.assertEqual(Path(row['excerpt']).read_text(), 'printf synthetic')
        self.assertTrue(row['evidence_id'])


if __name__ == '__main__':
    unittest.main()
