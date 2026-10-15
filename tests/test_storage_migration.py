import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime

from my_big_brother import config, migration, runner
from my_big_brother.paths import Paths


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.paths = Paths(self.root / 'config', self.root / 'data')
        self.paths.config.mkdir()
        settings = config.defaults(self.paths)
        settings.update(day_start_hour=4, results_root=str(self.paths.data / 'results'))
        settings['sources'] = {'bash': {'enabled': True}}
        config.write_json(self.paths.config / 'config.json', settings)
        raw = self.paths.data / 'raw-logs'
        config.write_json(raw / '2020-01-15/bash/unrelated.json', {})
        (raw / '2020-01-15/bash/session.jsonl').write_text(json.dumps({
            'event': 'command', 'command': 'example',
            'completed_at': datetime(2020, 1, 15, 3).astimezone().isoformat(),
        }) + '\n')

    def test_preview_preserves_configuration_and_apply_moves_logical_ownership(self):
        before = (self.paths.config / 'config.json').read_bytes()
        self.assertEqual(migration.migrate(self.paths)['status'], 'preview')
        self.assertFalse((self.paths.config / 'storage.json').exists())
        self.assertEqual((self.paths.config / 'config.json').read_bytes(), before)
        result = migration.migrate(self.paths, apply=True)
        self.assertEqual(result['status'], 'migrated')
        self.assertEqual(len(list((self.paths.daily / '2020-01-14/bash').glob('*.jsonl'))), 1)
        self.assertTrue((self.paths.data / 'raw-logs/2020-01-15/bash/session.jsonl').exists())
        self.assertEqual(config.load(self.paths)['results_root'], str(self.paths.memory))
        self.assertEqual(migration.migrate(self.paths)['status'], 'already-v2')

    def test_formal_results_without_ledger_or_captures_are_migrated(self):
        old = self.paths.data / 'results/records/worklog/2019-12-01.md'
        old.parent.mkdir(parents=True)
        old.write_text('# Historical report\n')
        migration.migrate(self.paths, apply=True)
        self.assertEqual((self.paths.memory / 'records/2019-12-01/worklog.md').read_bytes(), old.read_bytes())

    def test_pending_legacy_actions_block_migration_without_modifying_config(self):
        config.write_json(self.paths.data / 'state/completed.json', {
            'days': {'2020-01-15': {'status': 'actions-pending'}}})
        with self.assertRaisesRegex(ValueError, 'pending'):
            migration.migrate(self.paths, apply=True)
        self.assertFalse((self.paths.config / 'storage.json').exists())

    def test_deleted_migrated_day_is_not_reimported_by_repeat_migration(self):
        migration.migrate(self.paths, apply=True)
        (self.paths.daily / '2020-01-14').rename(self.root / 'deleted')
        self.assertEqual(runner.analyze(self.paths, config.load(self.paths), '2020-01-14')['status'], 'discarded')
        migration.migrate(self.paths, apply=True)
        self.assertFalse((self.paths.daily / '2020-01-14').exists())

    def test_screenshot_manifest_time_survives_migration(self):
        folder = self.paths.data / 'raw-logs/2020-01-15/screenshots'
        folder.mkdir(parents=True)
        (folder / 'frame.jpg').write_bytes(b'synthetic-image')
        (folder / 'manifest.jsonl').write_text(json.dumps({
            'path': 'frame.jpg', 'captured_at': datetime(2020, 1, 15, 3).astimezone().isoformat(),
        }) + '\n')
        migration.migrate(self.paths, apply=True)
        target = self.paths.daily / '2020-01-14/screenshots'
        self.assertTrue((target / 'frame.jpg').exists())
        self.assertEqual(json.loads((target / 'manifest.jsonl').read_text())['path'], 'frame.jpg')

    def test_migration_preserves_newer_formal_result(self):
        old = self.paths.data / 'results/records/worklog/2019-12-01.md'
        old.parent.mkdir(parents=True)
        old.write_text('# Older result\n')
        target = self.paths.data / 'memory/records/2019-12-01/worklog.md'
        target.parent.mkdir(parents=True)
        target.write_text('# Later human revision\n')
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            migration.migrate(self.paths, apply=True)
        self.assertEqual(target.read_text(), '# Later human revision\n')
        self.assertFalse((self.paths.config / 'storage.json').exists())


if __name__ == '__main__':
    unittest.main()
