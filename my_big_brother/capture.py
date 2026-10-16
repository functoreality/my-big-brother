"""Store already captured images. This module never starts screen recording."""

import json
import shutil
import uuid
from pathlib import Path

from .storage import file_lock, timestamp


def directory(paths, source, captured_at=None):
    if source not in ('bash', 'vim', 'screenshots'):
        raise ValueError('source must be bash, vim or screenshots')
    day = timestamp(captured_at).strftime('%Y-%m-%d')
    target = paths.raw_logs / day / source
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    return {'status': 'ready', 'date': day, 'directory': str(target)}


def screenshot(paths, image, captured_at=None):
    source = Path(image)
    if not source.is_file() or source.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        raise ValueError('image must be an existing supported screenshot file')
    instant = timestamp(captured_at)
    selected = directory(paths, 'screenshots', instant)
    target_dir = Path(selected['directory'])
    if source.resolve().parent == target_dir.resolve():
        target = source.resolve()
    else:
        target = target_dir / (instant.strftime('%H-%M-%S') + '-' + uuid.uuid4().hex + source.suffix.lower())
        shutil.copy2(source, target)
        target.chmod(0o600)
    with file_lock(target_dir / '.manifest.lock'):
        with (target_dir / 'manifest.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'path': target.name, 'captured_at': instant.isoformat()}) + '\n')
    return {**selected, 'image': str(target)}
