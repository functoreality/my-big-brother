"""WorkBuddy format fixtures, including regressions found in installation feedback."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from my_big_brother import config, runner
from my_big_brother.paths import Paths
from my_big_brother.sources import ANALYSIS_MARKER, workbuddy


class WorkBuddyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.projects = self.root / 'projects'
        self.projects.mkdir()
        self.start = datetime.fromisoformat('2026-03-05T00:00:00+08:00')
        self.end = self.start + timedelta(days=1)

    def message(self, role, text, minutes=0, **extra):
        return dict(type='message', role=role, content=[dict(type='text', text=text)],
                    timestamp=int((self.start + timedelta(minutes=minutes)).timestamp() * 1000), **extra)

    def session(self, events, *, encoding='utf-8'):
        path = self.projects / 'demo' / 'session.jsonl'
        path.parent.mkdir(exist_ok=True)
        path.write_text(''.join(json.dumps(event, ensure_ascii=False) + '\n' for event in events), encoding=encoding)
        return path

    def collect(self):
        return workbuddy.collect(self.projects, self.start, self.end)

    def test_bom_and_host_wrappers_keep_only_the_human_request(self):
        self.session([self.message('user', '<system-reminder>host setup</system-reminder>'
                                  '<user_query>整理发布清单</user_query>')], encoding='utf-8-sig')
        result = self.collect()
        self.assertEqual(result.status, 'ok')
        self.assertEqual([row['content'] for row in result.rows], ['整理发布清单'])

    def test_usage_does_not_promote_narration_to_a_final_answer(self):
        self.session([self.message('assistant', 'Still investigating'),
                      self.message('assistant', 'A response with usage', 1, message={'usage': {}})])
        self.assertEqual([row['role'] for row in self.collect().rows], ['assistant', 'assistant'])

    def test_tool_arguments_results_and_reasoning_never_become_message_evidence(self):
        self.session([self.message('user', 'Inspect a fixture'),
                      dict(type='function_call', name='Write', arguments='{"file_path":"private.txt"}'),
                      dict(type='function_call_result', output='secret payload'),
                      dict(type='reasoning', content='private thought'),
                      self.message('assistant', 'Could not write the file', 1)])
        rows = self.collect().rows
        self.assertEqual([row['content'] for row in rows], ['Inspect a fixture', 'Could not write the file'])

    def test_late_out_of_window_marker_excludes_already_collected_rows(self):
        self.session([self.message('user', 'Earlier ordinary text'),
                      self.message('assistant', 'Earlier answer', 1),
                      self.message('user', '<user_query>' + ANALYSIS_MARKER + '</user_query>', 1440)])
        self.assertEqual(self.collect().rows, [])

    def test_half_open_window_and_missing_source(self):
        self.session([self.message('user', 'Before', -1), self.message('user', 'Start'),
                      self.message('user', 'End', 1440)])
        self.assertEqual([row['content'] for row in self.collect().rows], ['Start'])
        self.assertEqual(workbuddy.collect(self.root / 'missing', self.start, self.end).status, 'unavailable')

    def test_corrupt_line_preserves_actual_line_numbers_and_reports_a_gap(self):
        path = self.session([self.message('user', 'One'), self.message('user', 'Two', 1)])
        lines = path.read_text(encoding='utf-8').splitlines()
        path.write_text(lines[0] + '\n{bad json}\n' + lines[1] + '\n', encoding='utf-8')
        result = self.collect()
        self.assertEqual(result.status, 'partial')
        self.assertEqual([row['event_ordinal'] for row in result.rows], [1, 3])
        self.assertTrue(any(':2' in gap for gap in result.gaps))

    def test_incomplete_wrappers_do_not_leak_host_context(self):
        self.session([self.message('user', '<system-reminder>unclosed host setup'),
                      self.message('user', '<user_query>incomplete request', 1),
                      self.message('user', '<system-reminder><user_query>host query</user_query>', 2)])
        result = self.collect()
        self.assertEqual(result.rows, [])
        self.assertEqual(result.status, 'partial')
        self.assertEqual(len(result.gaps), 3)

    def test_each_message_keeps_its_own_directory(self):
        self.session([self.message('user', 'First', cwd='first-project'),
                      self.message('user', 'Second', 1, cwd='second-project')])
        self.assertEqual([row['cwd'] for row in self.collect().rows], ['first-project', 'second-project'])

    def test_rollback_and_nested_subagent_files_are_not_read(self):
        path = self.session([self.message('user', 'Parent')])
        path.with_suffix('.file-rollback.ndjson').write_text('invalid rollback')
        child = path.parent / 'subagents'
        child.mkdir()
        (child / 'child.jsonl').write_text(json.dumps(self.message('user', 'Child')), encoding='utf-8')
        self.assertEqual([row['content'] for row in self.collect().rows], ['Parent'])

    def test_nonfinite_timestamps_are_gaps_not_crashes(self):
        self.session([dict(self.message('user', 'Bad'), timestamp=float('inf')),
                      dict(self.message('user', 'Bad too'), timestamp=True)])
        self.assertEqual(self.collect().status, 'partial')
        self.assertEqual(self.collect().rows, [])

    def test_explicit_workbuddy_setup_can_prepare_and_publish(self):
        paths = Paths(self.root / 'config', self.root / 'data')
        self.assertFalse(config.defaults(paths)['sources']['workbuddy']['enabled'])
        settings = config.initialize(paths, sources=['workbuddy'])
        self.assertTrue(settings['sources']['workbuddy']['enabled'])
        settings['sources']['workbuddy']['path'] = str(self.projects)
        config.write_json(paths.config / 'config.json', settings)
        self.session([self.message('user', 'Isolated integration fixture')])
        ticket = runner.analyze(paths, settings, '2026-03-05')
        self.assertEqual(ticket['status'], 'prepared')
        run = Path(ticket['run_dir'])
        context = runner.read_object(run / 'context.json')
        for name, kind in context['output_kinds'].items():
            path = Path(name)
            if path.suffix == '.md':
                path.write_text('# Synthetic integration fixture\n', encoding='utf-8')
            else:
                config.write_json(path, {'date': context['date'],
                                         'samples' if kind == 'time_estimates' else 'segments': []})
        config.write_json(run / 'completion.json', context['completion_example'])
        self.assertEqual(runner.finish_run(paths, settings, run)['status'], 'completed')


if __name__ == '__main__':
    unittest.main()
