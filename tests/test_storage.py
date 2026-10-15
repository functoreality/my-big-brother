"""Deletion is a supported lifecycle transition, not a cleanup command."""

import json
import os
import importlib.util
import io
from types import SimpleNamespace
from unittest.mock import patch
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

from my_big_brother import config, runner
from my_big_brother import capture
from my_big_brother.paths import Paths
from my_big_brother.storage import DiscardedDay, Layout, write_json


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.paths = Paths(self.root / 'config', self.root / 'data')
        self.settings = config.initialize(self.paths, sources=['bash'], day_start_hour=4)
        self.layout = self.paths.layout

    def discard(self, day):
        directory = self.layout.daily / day
        directory.rename(self.root / ('discarded-' + day))

    def test_logical_boundary_shared_with_collectors(self):
        before = datetime(2020, 1, 15, 3, 59).astimezone()
        self.assertEqual(self.layout.day(before), '2020-01-14')
        self.assertEqual(self.layout.day(before + timedelta(minutes=1)), '2020-01-15')

    def test_deleted_failed_day_stays_discarded_until_explicit_restore(self):
        first = runner.prepare_run(self.paths, self.settings, '2020-01-15')
        workspace = self.layout.record('2020-01-15')['workspace_id']
        self.discard('2020-01-15')
        self.assertEqual(runner.analyze(self.paths, self.settings, '2020-01-15')['status'], 'discarded')
        self.assertEqual(runner.prepare_run(self.paths, self.settings, '2020-01-15')['status'], 'discarded')
        self.assertFalse((self.layout.daily / '2020-01-15').exists())
        restored = runner.analyze(self.paths, self.settings, '2020-01-15', recreate_deleted=True)
        self.assertNotEqual(restored['run_dir'], first['run_dir'])
        self.assertNotEqual(self.layout.record('2020-01-15')['workspace_id'], workspace)
        self.assertEqual(self.layout.record('2020-01-15')['disposition'], 'retained')

    def test_completion_fact_survives_workspace_deletion(self):
        self.layout.ensure_day('2020-01-15')
        self.layout.update_review('2020-01-15', {'status': 'completed', 'closed_day': True})
        self.discard('2020-01-15')
        value = self.layout.record('2020-01-15')
        self.assertEqual(value['disposition'], 'discarded')
        self.assertEqual(value['review']['status'], 'completed')
        self.assertFalse((self.paths.state / 'completed.json').exists())

    def test_concurrent_first_writers_share_one_generation(self):
        def create(_):
            self.layout.ensure_day('2020-01-15')
            return self.layout.record('2020-01-15')['workspace_id']
        with ThreadPoolExecutor(max_workers=8) as pool:
            identifiers = list(pool.map(create, range(24)))
        self.assertEqual(len(set(identifiers)), 1)

    def test_corrupt_registry_and_missing_system_are_not_reset(self):
        self.layout.ensure_day('2020-01-15')
        record = self.paths.state / 'days/2020-01-15.json'
        record.write_text('{broken')
        with self.assertRaises(ValueError):
            self.layout.ensure_day('2020-01-15')
        self.assertEqual(record.read_text(), '{broken')
        (self.paths.state / 'days').rename(self.paths.state / 'days-backup')
        with self.assertRaises(ValueError):
            Layout.load(self.paths.config)

    def test_stale_run_rejected_after_explicit_restoration(self):
        ticket = runner.prepare_run(self.paths, self.settings, '2020-01-15')
        directory = Path(ticket['run_dir'])
        context = runner.read_object(directory / 'context.json')
        self.discard('2020-01-15')
        self.layout.ensure_day('2020-01-15', recreate=True)
        with self.assertRaises(DiscardedDay):
            self.layout.check_run(directory, context['workspace_id'])

    def test_calendar_cannot_change_silently(self):
        self.settings['day_start_hour'] = 3
        config.write_json(self.paths.config / 'config.json', self.settings)
        with self.assertRaisesRegex(ValueError, 'calendar'):
            config.load(self.paths)
        with self.assertRaises(ValueError):
            Layout.install(self.paths.config, self.paths.data, 3)

    def test_restore_rejects_invalid_date_before_creating_paths(self):
        with self.assertRaises(ValueError):
            self.layout.ensure_day('../escape', recreate=True)
        self.assertFalse((self.paths.data / 'escape').exists())

    def test_bash_writer_uses_shared_boundary_and_never_recreates_discarded_day(self):
        helper = Path(__file__).parents[1] / 'collectors/bash/recorder.py'
        spec = importlib.util.spec_from_file_location('test_v2_bash', helper)
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        clock = datetime(2020, 1, 15, 3).astimezone().isoformat()
        fields = ['a' * 32, clock, str(self.root), '0', 'synthetic command', '']
        payload = '\0'.join(fields).encode()
        with patch.object(recorder, 'locations', return_value=(self.paths.config, self.paths.data)), \
             patch.object(recorder, 'now', return_value=clock), \
             patch.object(recorder.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(payload))):
            recorder.record()
        log = next((self.layout.daily / '2020-01-14/bash').glob('*.jsonl'))
        self.assertEqual(json.loads(log.read_text())['command'], 'synthetic command')
        self.discard('2020-01-14')
        with patch.object(recorder, 'locations', return_value=(self.paths.config, self.paths.data)), \
             patch.object(recorder, 'now', return_value=clock), \
             patch.object(recorder.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(payload))):
            recorder.record()
        self.assertFalse((self.layout.daily / '2020-01-14').exists())

    def test_vendored_protocol_matches_canonical_source(self):
        root = Path(__file__).parents[1]
        self.assertEqual((root / 'my_big_brother/storage.py').read_bytes(),
                         (root / 'collectors/bash/storage.py').read_bytes())

    def test_existing_screenshot_is_registered_by_capture_time_and_discard_is_respected(self):
        source = self.root / 'synthetic.jpg'
        source.write_bytes(b'fixture bytes, no image decoding requested')
        instant = datetime(2020, 1, 15, 3).astimezone()
        result = capture.screenshot(self.paths, source, instant)
        self.assertEqual(result['date'], '2020-01-14')
        self.assertEqual(Path(result['image']).read_bytes(), source.read_bytes())
        metadata = json.loads((Path(result['directory']) / 'manifest.jsonl').read_text())
        self.assertEqual(metadata['captured_at'], instant.isoformat())
        self.discard('2020-01-14')
        self.assertEqual(capture.screenshot(self.paths, source, instant)['status'], 'discarded')
        self.assertFalse((self.layout.daily / '2020-01-14').exists())

    def test_log_fallback_does_not_resurrect_target_day(self):
        self.layout.ensure_day('2020-01-15')
        self.discard('2020-01-15')
        launch = self.layout.launch_directory('2020-01-15')
        self.assertEqual(launch.parent.parent.name, self.layout.day())
        self.assertFalse((self.layout.daily / '2020-01-15').exists())

    def test_failed_publication_leaves_large_temporary_copy_only_in_daily(self):
        self.settings['outputs'] = ['worklog']
        ticket = runner.prepare_run(self.paths, self.settings, '2020-01-15')
        run = Path(ticket['run_dir'])
        context = runner.read_object(run / 'context.json')
        Path(context['output_paths'][0]).write_text('# Synthetic result\n')
        config.write_json(run / 'completion.json', context['completion_example'])
        destination = Path(context['final_output_paths'][0])
        replace = runner.os.replace

        def interrupted(source, target):
            if Path(target) == destination:
                raise OSError('Synthetic interruption before replacing report')
            return replace(source, target)

        with patch.object(runner.os, 'replace', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'Synthetic interruption'):
                runner.finish_run(self.paths, self.settings, run)
        self.assertFalse(destination.exists())
        self.assertTrue(list((run / 'publication').glob('.mbb-*')))
        self.assertFalse(list(self.paths.memory.rglob('.mbb-*')))
        self.assertEqual(runner.finish_run(self.paths, self.settings, run)['status'], 'completed')

    def test_cross_filesystem_publication_stops_before_replacing_any_report(self):
        self.settings['outputs'] = ['worklog']
        ticket = runner.prepare_run(self.paths, self.settings, '2020-01-15')
        run = Path(ticket['run_dir'])
        context = runner.read_object(run / 'context.json')
        Path(context['output_paths'][0]).write_text('# Synthetic result\n')
        config.write_json(run / 'completion.json', context['completion_example'])
        target = Path(context['final_output_paths'][0])
        target.parent.mkdir(parents=True, exist_ok=True)
        original_stat = Path.stat

        def different_device(path, *args, **kwargs):
            result = original_stat(path, *args, **kwargs)
            if path == target.parent:
                values = list(result)
                values[2] += 1
                return os.stat_result(values)
            return result

        with patch.object(Path, 'stat', different_device):
            with self.assertRaisesRegex(ValueError, 'same filesystem'):
                runner.finish_run(self.paths, self.settings, run)
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
