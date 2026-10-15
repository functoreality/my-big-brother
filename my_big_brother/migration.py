"""Explicit, non-destructive migration from the v1 storage layout."""

import json
import shutil
import re
from datetime import datetime, timedelta
from pathlib import Path

from . import config, runner
from .paths import raw_logs_root
from .storage import Layout
from .sources.screenshots import _manifest


def copy_preserving(source, target):
    """A retry may reuse identical files, but must preserve later user edits."""
    if target.exists() and runner.digest(target) != runner.digest(source):
        raise ValueError('Migration would overwrite different data: ' + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def migrate(paths, *, apply=False, data_root=None):
    if (paths.config / 'storage.json').exists():
        layout = paths.layout
        return {'status': 'already-v2', 'daily': str(layout.daily), 'memory': str(layout.memory)}
    settings = runner.read_object(paths.config / 'config.json')
    hour = settings.get('day_start_hour', 0)
    layout = Layout({'schema_version': 2, 'data_root': str(data_root or paths.data), 'day_start_hour': hour})
    old_raw = raw_logs_root(paths)
    if (old_raw.resolve() == layout.daily.resolve()
            or old_raw.resolve() in layout.daily.resolve().parents
            or layout.daily.resolve() in old_raw.resolve().parents):
        raise ValueError('New daily storage must be separate from the legacy capture root')
    old_state = paths.data / 'state'
    old_results = Path(settings.get('results_root', paths.data / 'results'))
    completed_path = old_state / 'completed.json'
    ledger = runner.read_object(completed_path).get('days', {}) if completed_path.exists() else {}
    profile = config.load_profile(settings)
    if profile:
        declared = profile['context_files'] + (profile['post_review']['write_paths'] if profile['post_review'] else [])
        if any(Path(name) == old_state or old_state in Path(name).parents for name in declared):
            raise ValueError('Personal profile still refers to v1 state. Update its task bindings before migration.')
    if any(item.get('status') == 'actions-pending' for item in ledger.values()):
        raise ValueError('Finish or explicitly abandon pending v1 post-review work before migration.')
    if any(item.get('path') for name, item in settings.get('sources', {}).items()
           if name in ('bash', 'vim', 'screenshots') and item.get('enabled', True)):
        raise ValueError('Move explicitly configured legacy capture roots into shared storage before migration.')
    rows, copies, warnings, headers, frames = {}, [], [], {}, {}
    if old_raw.exists():
        for source in sorted(set(old_raw.glob('*/bash/*.jsonl')) | set(old_raw.glob('*.jsonl'))):
            events = [json.loads(line) for line in source.read_text(encoding='utf-8').splitlines() if line.strip()]
            if any(not isinstance(event, dict) for event in events):
                raise ValueError('Invalid Bash event: ' + str(source))
            starts = [event for event in events if event.get('event') == 'session_start']
            known = headers.setdefault(source.name, [])
            known.extend(event for event in starts if event not in known)
            for event in events:
                if not isinstance(event, dict):
                    raise ValueError('Invalid Bash event: ' + str(source))
                field = {'command': 'completed_at', 'session_start': 'started_at', 'session_end': 'ended_at'}.get(event.get('event'))
                if field is None:
                    continue
                recorded_at = event.get(field, event.get('timestamp'))
                if recorded_at is None:
                    raise ValueError('Missing Bash timestamp: ' + str(source))
                day = layout.day(recorded_at)
                key = (day, source.name)
                if key not in rows:
                    rows[key] = list(starts) if event.get('event') != 'session_start' else []
                if event not in rows[key]:
                    rows[key].append(event)
        for directory in sorted(old_raw.glob('*/screenshots')):
            metadata = _manifest(directory, warnings)
            for source in sorted(directory.iterdir()):
                if source.is_file() and source.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                    frame = metadata.get(source.resolve(), {})
                    value = frame.get('timestamp', frame.get('captured_at'))
                    moment = (datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone()
                              if value else datetime.fromtimestamp(source.stat().st_mtime).astimezone())
                    day = layout.day(moment)
                    copies.append((source, day, Path('screenshots') / source.name))
                    frames.setdefault(day, []).append({'path': source.name, 'captured_at': moment.isoformat()})
        for manifest in sorted(old_raw.glob('*/vim/*/record.json')):
            item = runner.read_object(manifest)
            start = datetime.fromisoformat(item['vim_start'].replace('Z', '+00:00')).astimezone()
            if not item.get('vim_close'):
                raise ValueError('An old Vim recording is still open: ' + str(manifest.parent))
            end = datetime.fromisoformat(item['vim_close'].replace('Z', '+00:00')).astimezone()
            if end < start:
                raise ValueError('Invalid Vim interval: ' + str(manifest))
            first, last = layout.day(start), layout.day(max(start, end - timedelta(microseconds=1)))
            day = datetime.fromisoformat(first).date()
            while day.isoformat() <= last:
                for source in manifest.parent.iterdir():
                    if source.is_file():
                        copies.append((source, day.isoformat(), Path('vim') / manifest.parent.name / source.name))
                day += timedelta(days=1)
            if first != last:
                warnings.append('Legacy whole-session Vim diff is copied independently per overlapping day: ' + manifest.parent.name)
    for (day, filename), events in rows.items():
        starts = headers.get(filename, [])
        rows[(day, filename)] = starts + [event for event in events if event not in starts]
    proposed = {'status': 'preview', 'daily': str(layout.daily), 'memory': str(layout.memory),
                'bash_files': len(rows), 'capture_files': len(copies), 'warnings': warnings,
                'legacy_sources_retained': True, 'cron_changed': False}
    if not apply:
        return proposed
    backup = paths.config / 'backups' / ('storage-v1-' + datetime.now().strftime('%Y%m%dT%H%M%S%f'))
    backup.mkdir(parents=True, mode=0o700)
    for name in ('config.json', 'raw-logs-path.txt', 'profile.json'):
        if (paths.config / name).exists():
            shutil.copy2(paths.config / name, backup / name)
    # Publish the shared configuration only after copies and configuration
    # preparation succeed. A failed copy leaves the v1 entry usable.
    layout = Layout.install(backup / 'pending-config', layout.root, hour)
    for (day, filename), events in rows.items():
        target = layout.ensure_day(day) / 'bash' / filename
        target.parent.mkdir(exist_ok=True)
        content = ''.join(json.dumps(event, ensure_ascii=False) + '\n' for event in events)
        if target.exists() and target.read_text(encoding='utf-8') != content:
            raise ValueError('Migration would overwrite different Bash data: ' + str(target))
        target.write_text(content, encoding='utf-8')
    for source, day, relative in copies:
        target = layout.ensure_day(day) / relative
        copy_preserving(source, target)
    for day, entries in frames.items():
        target = layout.daily / day / 'screenshots/manifest.jsonl'
        content = ''.join(json.dumps(entry) + '\n' for entry in entries)
        if target.exists() and target.read_text(encoding='utf-8') != content:
            raise ValueError('Migration would overwrite screenshot metadata: ' + str(target))
        target.write_text(content, encoding='utf-8')
    # Old run material is diagnostic only. It is not silently resumed under a
    # different storage protocol or passed to a new day's analysis.
    for run in sorted((old_state / 'runs').glob('*/*')):
        day = run.parent.name
        target = layout.ensure_day(day) / '_legacy' / run.name
        if not target.exists():
            shutil.copytree(run, target)
    for launch in sorted((old_state / 'launches').glob('*')):
        if launch.is_dir():
            day = layout.day(datetime.fromtimestamp(launch.stat().st_mtime).astimezone())
            target = layout.ensure_day(day) / '_launches' / ('legacy-' + launch.name)
            if not target.exists():
                shutil.copytree(launch, target)
    old_log = old_state / 'scheduler.log'
    if old_log.exists():
        day = layout.day(datetime.fromtimestamp(old_log.stat().st_mtime).astimezone())
        copy_preserving(old_log, layout.ensure_day(day) / 'legacy-scheduler.log')
    if old_results == paths.data / 'results':
        settings['results_root'] = str(layout.memory)
        output_days = {path.stem for path in (old_results / 'records').rglob('*')
                       if path.is_file() and re.fullmatch(r'\d{4}-\d{2}-\d{2}', path.stem)}
        for day in set(ledger) | {key[0] for key in rows} | output_days:
            old_relatives = [f'records/worklog/{day}.md', f'records/time-use/{day}.md',
                             f'records/time-use/data/{day}.json', f'records/insights/{day}.md',
                             f'records/time-estimates/{day}.json']
            new_relatives = [f'records/{day}/worklog.md', f'records/{day}/time-use.md',
                             f'records/{day}/time-use.json', f'records/{day}/insights.md',
                             f'records/{day}/time-estimates.json']
            for old, new in zip(old_relatives, new_relatives):
                source = old_results / old
                if source.is_file():
                    target = layout.memory / new
                    copy_preserving(source, target)
        for old, new in (('USER-MODEL.md', 'USER-MODEL.md'), ('SOURCES.md', 'MACHINE-CONTEXT.md')):
            source = old_results / 'records/knowledge' / old
            if source.exists():
                copy_preserving(source, layout.memory / new)
    for day, entry in ledger.items():
        layout.ensure_day(day)
        profile = config.load_profile(settings)
        mapping = runner.output_layout(settings, day, layout.daily / day, profile)
        entry.update(outputs=[item['final'] for item in mapping], results_root=settings['results_root'],
                     review_configuration={'language': settings['language'], 'day_start_hour': hour,
                                           'sources': settings['sources'], 'raw_logs': str(layout.daily)})
        layout.update_review(day, entry)
    config.write_json(paths.config / 'config.json', settings)
    config.write_json(paths.config / 'storage.json', layout.settings)
    proposed.update(status='migrated', backup=str(backup),
                    note='Retained v1 sources are rollback material. Retire old writers/importers before archiving them.')
    config.write_json(backup / 'receipt.json', proposed)
    return proposed
