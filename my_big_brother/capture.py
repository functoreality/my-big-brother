"""Store already captured images. This module never starts screen recording."""

import json
import shutil
import uuid
from pathlib import Path

from .storage import DiscardedDay, Layout, file_lock, timestamp


def directory(paths, source, captured_at=None):
    layout = Layout.for_collector(paths.config, paths.data)
    day = layout.day(captured_at)
    try:
        target = layout.ensure_day(day) / source
    except DiscardedDay:
        return {'status': 'discarded', 'date': day, 'directory': None}
    target.mkdir(exist_ok=True, mode=0o700)
    return {'status': 'ready', 'date': day, 'directory': str(target)}


def screenshot(paths, image, captured_at=None):
    source = Path(image)
    if not source.is_file() or source.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        raise ValueError('image must be an existing supported screenshot file')
    instant = timestamp(captured_at)
    selected = directory(paths, 'screenshots', instant)
    if selected['status'] == 'discarded':
        return selected
    target_dir = Path(selected['directory'])
    if source.resolve().parent == target_dir.resolve():
        target = source.resolve()
    else:
        target = target_dir / (instant.strftime('%H-%M-%S') + '-' + uuid.uuid4().hex + source.suffix.lower())
        shutil.copy2(source, target)
        target.chmod(0o600)
    layout = Layout.for_collector(paths.config, paths.data)
    with file_lock(layout.system / 'locks' / ('screenshots-' + selected['date'] + '.lock')):
        with (target_dir / 'manifest.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'path': target.name, 'captured_at': instant.isoformat()}) + '\n')
    return {**selected, 'image': str(target)}
