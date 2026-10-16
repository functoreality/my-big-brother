"""Daily runtime material is disposable and needs no permanent registry."""

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
from my_big_brother.storage import write_json
from my_big_brother.sources import bash, vim, calendar_dates
from my_big_brother import __main__ as cli
from my_big_brother.sources import screenshots
from contextlib import redirect_stdout


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.paths = Paths(self.root / 'config', self.root / 'data')
        self.settings = config.initialize(self.paths, sources=['bash'], day_start_hour=4)
        self.layout = self.paths.layout

    def remove_day(self, day):
        directory = self.layout.raw_logs / day
        directory.rename(self.root / ('removed-' + day))

    def test_collectors_use_system_calendar_dates(self):
        before = datetime(2020, 1, 15, 3, 59).astimezone()
        self.assertEqual(self.layout.day(before), '2020-01-15')
        self.assertEqual(self.layout.day(before + timedelta(minutes=1)), '2020-01-15')
        self.assertEqual(self.layout.day(datetime(2020, 1, 16, 0).astimezone()), '2020-01-16')

    def test_default_collectors_need_no_application_configuration(self):
        paths = Paths(self.root / 'standalone-config', self.root / 'standalone-data')
        instant = datetime(2020, 1, 15, 3).astimezone()
        result = capture.directory(paths, 'bash', instant)
        self.assertEqual(Path(result['directory']), paths.data / 'raw-logs/2020-01-15/bash')
        self.assertFalse(paths.config.exists())
        self.assertEqual(list(paths.data.iterdir()), [paths.raw_logs])
        (paths.raw_logs / '2020-01-15').rename(self.root / 'removed-default-date')
        recreated = capture.directory(paths, 'bash', instant)
        self.assertEqual(recreated['status'], 'ready')
        self.assertTrue(Path(recreated['directory']).is_dir())
        self.assertFalse((paths.data / 'memory').exists())

    def test_concurrent_default_collectors_share_plain_date_paths(self):
        paths = Paths(self.root / 'fresh-config', self.root / 'fresh-data')
        instant = datetime(2020, 1, 15, 3).astimezone()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: capture.directory(paths, 'bash', instant), range(24)))
        self.assertEqual({row['directory'] for row in results},
                         {str(paths.raw_logs / '2020-01-15/bash')})
        self.assertFalse(paths.config.exists())
        self.assertEqual(list(paths.data.rglob('*')),
                         [paths.raw_logs, paths.raw_logs / '2020-01-15',
                          paths.raw_logs / '2020-01-15/bash'])

    def test_capture_cli_works_before_application_initialization(self):
        paths = Paths(self.root / 'capture-config', self.root / 'capture-data')
        with patch.object(cli, 'discover', return_value=paths), redirect_stdout(io.StringIO()) as output:
            status = cli.main(['capture-path', '--source', 'screenshots',
                               '--timestamp', datetime(2020, 1, 15, 3).astimezone().isoformat()])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())['date'], '2020-01-15')
        self.assertFalse(paths.config.exists())

    @unittest.skipIf(screenshots.Image is None, 'Optional Pillow is unavailable')
    def test_screenshots_are_selected_from_both_calendar_dates(self):
        start, end = runner.window('2020-01-14', 4)
        for instant in (datetime(2020, 1, 14, 5).astimezone(), datetime(2020, 1, 15, 2).astimezone(), end):
            image = self.root / ('frame-' + instant.strftime('%d-%H') + '.png')
            screenshots.Image.new('RGB', (16, 16), 'red').save(image)
            capture.screenshot(self.paths, image, instant)
        result = screenshots.collect(self.layout.raw_logs, start, end)
        self.assertEqual(len(result.rows), 2)
        self.assertEqual({Path(row['path']).parents[1].name for row in result.rows}, {'2020-01-14', '2020-01-15'})

    def test_analysis_joins_adjacent_calendar_dates_and_filters_actual_timestamps(self):
        start, end = runner.window('2020-01-14', 4)
        self.assertEqual(calendar_dates(start, end), ['2020-01-14', '2020-01-15'])
        self.assertEqual(calendar_dates(start, datetime(2020, 1, 15, 0).astimezone()), ['2020-01-14'])
        moments = [datetime(2020, 1, 14, 2).astimezone(), datetime(2020, 1, 14, 5).astimezone(),
                   datetime(2020, 1, 15, 2).astimezone(), datetime(2020, 1, 15, 4).astimezone()]
        for ordinal, instant in enumerate(moments):
            date_dir = self.layout.ensure_day(instant.strftime('%Y-%m-%d'))
            bash_dir = date_dir / 'bash'
            bash_dir.mkdir(exist_ok=True)
            (bash_dir / (str(ordinal) + '.jsonl')).write_text(json.dumps({
                'event': 'command', 'command': 'sample-' + str(ordinal),
                'completed_at': instant.isoformat(),
            }) + '\n')
            write_json(date_dir / 'vim' / str(ordinal) / 'record.json', {
                'schema_version': 1, 'source': 'vim', 'session_id': format(ordinal, '032x'),
                'vim_start': instant.isoformat(), 'vim_close': (instant + timedelta(minutes=1)).isoformat(),
                'opened_files': [], 'storage_version': 2, 'calendar_date': instant.strftime('%Y-%m-%d'),
                'segment_open': False,
            })
        rows = bash.collect(self.layout.raw_logs, start, end).rows
        self.assertEqual([row['command'] for row in rows], ['sample-1', 'sample-2'])
        sessions = vim.collect(self.layout.raw_logs, start, end).rows
        self.assertEqual(len(sessions), 2)
        self.assertEqual({Path(row['record_path']).parents[2].name for row in sessions}, {'2020-01-14', '2020-01-15'})

    def test_vim_session_started_days_before_window_is_discovered(self):
        start, end = runner.window('2020-01-14', 4)
        opened = start - timedelta(days=2)
        directory = self.layout.ensure_day(opened.strftime('%Y-%m-%d')) / 'vim' / 'long-session'
        payload = {
            'schema_version': 1, 'source': 'vim', 'session_id': 'a' * 32,
            'vim_start': opened.isoformat(),
            'vim_close': (start + timedelta(hours=1)).isoformat(),
            'opened_files': [],
        }
        write_json(directory / 'record.json', payload)
        result = vim.collect(self.layout.raw_logs, start, end)
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result.rows), 1)
        row = result.rows[0]
        self.assertEqual(row['record_path'], str(directory / 'record.json'))
        self.assertEqual(row['record_metadata'], payload)
        self.assertEqual(row['session_status'], 'closed')
        self.assertIn('Whole-session', row['diff_scope'])
        self.assertIn('clipped window', row['diff_scope'])
        self.assertFalse((self.layout.raw_logs / '2020-01-14').exists())

    def test_vim_day_segment_fields_do_not_change_whole_session_meaning(self):
        start, end = runner.window('2020-01-14', 4)
        directory = self.layout.ensure_day('2020-01-14') / 'vim' / 'historical-segment'
        write_json(directory / 'record.json', {
            'schema_version': 1, 'source': 'vim', 'session_id': 'b' * 32,
            'vim_start': start.isoformat(),
            'vim_close': (start + timedelta(hours=1)).isoformat(),
            'opened_files': [], 'storage_version': 2, 'segment_open': True,
        })
        row = vim.collect(self.layout.raw_logs, start, end).rows[0]
        self.assertEqual(row['session_status'], 'closed')
        self.assertIn('Whole-session', row['diff_scope'])

    def test_explicit_older_day_can_be_prepared_after_deletion(self):
        first = runner.prepare_run(self.paths, self.settings, '2020-01-15')
        self.remove_day('2020-01-15')
        self.assertIsNone(self.layout.record('2020-01-15'))
        rerun = runner.analyze(self.paths, self.settings, '2020-01-15', allow_empty=True)
        self.assertEqual(rerun['status'], 'prepared')
        self.assertNotEqual(rerun['run_dir'], first['run_dir'])
        self.assertTrue(Path(rerun['run_dir']).is_dir())

    def test_completion_fact_is_deleted_with_its_day(self):
        self.layout.ensure_day('2020-01-15')
        review = {'status': 'completed', 'closed_day': True}
        self.layout.update_review('2020-01-15', review)
        record = {'date': '2020-01-15', 'review': review}
        self.assertEqual(self.layout.record('2020-01-15'), record)
        self.assertEqual(json.loads((self.paths.raw_logs / '2020-01-15/review.json').read_text()), record)
        self.remove_day('2020-01-15')
        self.assertIsNone(self.layout.record('2020-01-15'))
        self.assertEqual(list(self.paths.memory.iterdir()), [])

    def test_concurrent_first_writers_create_one_plain_directory(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            directories = list(pool.map(lambda _: self.layout.ensure_day('2020-01-15'), range(24)))
        self.assertEqual(set(directories), {self.paths.raw_logs / '2020-01-15'})
        self.assertIsNone(self.layout.record('2020-01-15'))
        self.assertEqual(list(directories[0].iterdir()), [])

    def test_corrupt_daily_review_is_reported_without_replacement(self):
        directory = self.layout.ensure_day('2020-01-15')
        record = directory / 'review.json'
        record.write_text('{broken')
        with self.assertRaises(ValueError):
            self.layout.record('2020-01-15')
        self.assertEqual(record.read_text(), '{broken')
        self.assertEqual(list(self.paths.memory.iterdir()), [])
        self.assertEqual(list(self.paths.config.iterdir()), [self.paths.config / 'config.json'])

    def test_run_must_exist_inside_retained_daily_analysis(self):
        ticket = runner.prepare_run(self.paths, self.settings, '2020-01-15')
        directory = Path(ticket['run_dir'])
        self.layout.check_run(directory)
        self.remove_day('2020-01-15')
        self.layout.ensure_day('2020-01-15')
        with self.assertRaises(ValueError):
            self.layout.check_run(directory)
        outside = self.root / 'unmanaged-run'
        outside.mkdir()
        with self.assertRaises(ValueError):
            self.layout.check_run(outside)

    def test_analysis_boundary_does_not_change_capture_paths(self):
        original = self.paths.raw_logs
        self.settings['day_start_hour'] = 3
        config.write_json(self.paths.config / 'config.json', self.settings)
        self.assertEqual(config.load(self.paths)['day_start_hour'], 3)
        self.assertEqual(self.paths.raw_logs, original)
        instant = datetime(2020, 1, 15, 2).astimezone()
        self.assertEqual(capture.directory(self.paths, 'bash', instant)['date'], '2020-01-15')
        self.assertFalse((self.paths.config / 'storage.json').exists())
        self.assertFalse((self.paths.memory / '_system').exists())

    def test_invalid_date_is_rejected_before_creating_paths(self):
        for day in ('../escape', '2020-02-30', '20200115'):
            with self.assertRaises(ValueError):
                self.layout.ensure_day(day)
        self.assertEqual(list(self.paths.raw_logs.iterdir()), [])

    def test_bash_writer_keeps_start_date_and_does_not_recreate_removed_active_session(self):
        helper = Path(__file__).parents[1] / 'collectors/bash/recorder.py'
        spec = importlib.util.spec_from_file_location('test_v2_bash', helper)
        recorder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(recorder)
        clock = datetime(2020, 1, 15, 3).astimezone().isoformat()
        with patch.object(recorder._paths, 'platform_paths', return_value=(self.paths.config, self.paths.data)), \
             patch.object(recorder, 'now', return_value=datetime(2020, 1, 14, 23).astimezone().isoformat()):
            session = recorder.new_session('12345', str(self.root))
        fields = [session, 'command', str(self.root), 'synthetic command', '0',
                  str(int(datetime.fromisoformat(clock).timestamp())), '']
        payload = '\0'.join(fields).encode()
        with patch.object(recorder._paths, 'platform_paths', return_value=(self.paths.config, self.paths.data)), \
             patch.object(recorder, 'now', return_value=clock), \
             patch.object(recorder.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(payload))):
            recorder.record()
        log = next((self.layout.raw_logs / '2020-01-14/bash').glob('*.jsonl'))
        self.assertEqual(log.name, Path(session).name)
        self.assertEqual(json.loads(log.read_text().splitlines()[1])['command'], 'synthetic command')
        self.remove_day('2020-01-14')
        with patch.object(recorder._paths, 'platform_paths', return_value=(self.paths.config, self.paths.data)), \
             patch.object(recorder, 'now', return_value=clock), \
             patch.object(recorder.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(payload))):
            recorder.record()
        self.assertFalse((self.layout.raw_logs / '2020-01-14').exists())

        self.layout.ensure_day('2020-01-14')
        with patch.object(recorder, 'now', return_value=clock), \
             patch.object(recorder.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(payload))):
            recorder.record()
        self.assertFalse((self.layout.raw_logs / '2020-01-14/bash').exists())

    def test_vendored_locator_matches_canonical_source(self):
        root = Path(__file__).parents[1]
        self.assertEqual((root / 'my_big_brother/collector_paths.py').read_bytes(),
                         (root / 'collectors/bash/paths.py').read_bytes())

    def test_text_locator_is_shared_by_bash_capture_and_analysis(self):
        from my_big_brother.collector_paths import capture_root

        target = self.root / 'shared captures'
        (self.paths.config / 'raw-logs-path.txt').write_text(str(target) + '\n')
        self.assertEqual(self.paths.raw_logs, target)
        self.assertEqual(capture_root(self.paths.config, self.paths.data), target)
        instant = datetime(2020, 1, 15, 3).astimezone()
        selected = capture.directory(self.paths, 'screenshots', instant)
        self.assertEqual(Path(selected['directory']), target / '2020-01-15/screenshots')
        ticket = runner.prepare_run(self.paths, self.settings, '2020-01-15')
        self.assertEqual(Path(ticket['run_dir']).parents[2], target)
        self.assertEqual(self.paths.memory, self.paths.data / 'memory')
        self.assertFalse((self.paths.data / 'raw-logs/2020-01-15').exists())

    def test_initialization_publishes_or_preserves_the_text_locator(self):
        from my_big_brother.collector_paths import capture_root

        self.assertEqual(capture_root(self.paths.config, self.paths.data), self.paths.raw_logs)
        fresh = Paths(self.root / 'fresh-config', self.root / 'fresh-data')
        fresh.config.mkdir()
        target = self.root / 'selected-captures'
        (fresh.config / 'raw-logs-path.txt').write_bytes((str(target) + '\r\n').encode())
        config.initialize(fresh, sources=['bash'], data_root=self.root / 'selected-data')
        self.assertEqual(fresh.raw_logs, target)
        self.assertEqual((fresh.config / 'raw-logs-path.txt').read_bytes(), (str(target) + '\r\n').encode())
        self.assertEqual(fresh.memory, self.root / 'selected-data/memory')
        (fresh.config / 'raw-logs-path.txt').write_text(str(fresh.memory))
        with self.assertRaisesRegex(ValueError, 'outside disposable'):
            config.load(fresh)

    def test_first_install_root_shortcut_stores_only_locator_and_config(self):
        paths = Paths(self.root / 'custom-config', self.root / 'platform-data')
        selected = self.root / 'selected-data'
        settings = config.initialize(paths, sources=['bash'], data_root=selected)
        self.assertEqual(paths.raw_logs, selected / 'raw-logs')
        self.assertEqual(paths.memory, selected / 'memory')
        self.assertEqual(settings['results_root'], str(selected / 'memory'))
        self.assertNotIn('data_root', settings)
        self.assertEqual({path.name for path in paths.config.iterdir()},
                         {'raw-logs-path.txt', 'config.json'})
        self.assertEqual({path.name for path in selected.iterdir()}, {'raw-logs', 'memory'})
        self.assertEqual(list(paths.memory.iterdir()), [])
        self.assertFalse(paths.data.exists())

    def test_existing_screenshot_uses_capture_date_and_daily_manifest(self):
        source = self.root / 'synthetic.jpg'
        source.write_bytes(b'fixture bytes, no image decoding requested')
        instant = datetime(2020, 1, 15, 3).astimezone()
        result = capture.screenshot(self.paths, source, instant)
        self.assertEqual(result['date'], '2020-01-15')
        self.assertEqual(Path(result['image']).read_bytes(), source.read_bytes())
        metadata = json.loads((Path(result['directory']) / 'manifest.jsonl').read_text())
        self.assertEqual(metadata['captured_at'], instant.isoformat())
        self.assertTrue((Path(result['directory']) / '.manifest.lock').is_file())
        self.remove_day('2020-01-15')
        repeated = capture.screenshot(self.paths, source, instant)
        self.assertEqual(repeated['status'], 'ready')
        self.assertTrue(Path(repeated['image']).exists())
        self.assertEqual(list(self.paths.memory.iterdir()), [])

    def test_launch_logs_use_requested_day_without_permanent_registry(self):
        self.layout.ensure_day('2020-01-15')
        self.remove_day('2020-01-15')
        launch = self.layout.launch_directory('2020-01-15')
        self.assertEqual(launch.parent.parent, self.paths.raw_logs / '2020-01-15')
        self.assertTrue(launch.is_dir())
        self.assertEqual(list(self.paths.memory.iterdir()), [])

    def publication_fixture(self):
        self.settings['outputs'] = ['worklog']
        ticket = runner.prepare_run(self.paths, self.settings, '2020-01-15')
        run = Path(ticket['run_dir'])
        context = runner.read_object(run / 'context.json')
        staged = Path(context['output_paths'][0])
        staged.write_text('# Synthetic result\n')
        config.write_json(run / 'completion.json', context['completion_example'])
        return run, context, staged, Path(context['final_output_paths'][0])

    def test_partial_write_preserves_draft_and_requires_manual_recovery(self):
        run, context, staged, destination = self.publication_fixture()
        fdopen = os.fdopen

        def interrupted(fd, mode, *args, **kwargs):
            handle = fdopen(fd, mode, *args, **kwargs)
            if mode == 'wb':
                write = handle.write

                def partial_write(content):
                    write(content[:4])
                    raise OSError('Synthetic interrupted write')

                handle.write = partial_write
            return handle

        with patch.object(runner.os, 'fdopen', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'Synthetic interrupted write'):
                runner.finish_run(self.paths, self.settings, run)
        self.assertEqual(destination.read_bytes(), staged.read_bytes()[:4])
        self.assertEqual(staged.read_text(), '# Synthetic result\n')
        self.assertFalse(runner.completed(self.paths, self.settings, '2020-01-15'))
        journal = runner.read_object(Path(context['publication_journal']))
        self.assertEqual(journal['status'], 'publishing')
        self.assertEqual(journal['published'], [])
        self.assertFalse((run / 'publication').exists())
        self.assertFalse(list(self.paths.memory.rglob('.mbb-*')))
        with self.assertRaisesRegex(ValueError, 'Result changed after prepare'):
            runner.finish_run(self.paths, self.settings, run)
        # Simulate a human checking the target and restoring the intact draft.
        destination.write_bytes(staged.read_bytes())
        self.assertEqual(runner.finish_run(self.paths, self.settings, run)['status'], 'completed')

    def test_unreadable_draft_does_not_truncate_existing_report(self):
        self.settings['outputs'] = ['worklog']
        first, _, _, target = self.publication_fixture()
        runner.finish_run(self.paths, self.settings, first)
        original = target.read_bytes()
        run, _, staged, _ = self.publication_fixture()
        read_bytes = Path.read_bytes
        reads = 0

        def unreadable(path):
            nonlocal reads
            if path == staged:
                reads += 1
                if reads == 2:
                    raise OSError('Synthetic draft read failure')
            return read_bytes(path)

        with patch.object(Path, 'read_bytes', unreadable):
            with self.assertRaisesRegex(OSError, 'draft read failure'):
                runner.finish_run(self.paths, self.settings, run)
        self.assertEqual(reads, 2)
        self.assertEqual(target.read_bytes(), original)

    def test_cross_filesystem_publication_needs_no_final_rename(self):
        run, _, staged, target = self.publication_fixture()
        target.parent.mkdir(parents=True, exist_ok=True)
        original_stat = Path.stat
        replace = os.replace

        def different_device(path, *args, **kwargs):
            result = original_stat(path, *args, **kwargs)
            if path == target.parent:
                values = list(result)
                values[2] += 1
                return os.stat_result(values)
            return result

        def no_final_rename(source, destination):
            if Path(destination) == target:
                raise OSError('Synthetic cross-mount rename rejected')
            return replace(source, destination)

        with patch.object(Path, 'stat', different_device), patch.object(
                runner.os, 'replace', side_effect=no_final_rename):
            result = runner.finish_run(self.paths, self.settings, run)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(target.read_bytes(), staged.read_bytes())
        self.assertFalse((run / 'publication').exists())
        if os.name == 'posix':
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)


if __name__ == '__main__':
    unittest.main()
