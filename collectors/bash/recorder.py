#!/usr/bin/env python3
"""Standard-library writer for the opt-in interactive Bash collector."""

import datetime as dt
import errno
import json
import os
from pathlib import Path
import re
import sys
import importlib.util

_spec = importlib.util.spec_from_file_location("mbb_storage", Path(__file__).with_name("storage.py"))
_storage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_storage)


def locations():
    return _storage.platform_paths()


SECRET = re.compile(r'(?i)(?:token|secret|password|api_?key)\s*=|sshpass|authorization:')


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def directory_label(cwd):
    label = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', '_', Path(cwd).name).strip(' .')
    if len(label) > 28:
        label = label[:18] + '..' + label[-8:]
    encoded = label.encode('utf-8')
    if len(encoded) > 64:
        label = (encoded[:30].decode('utf-8', errors='ignore') + '..'
                 + encoded[-32:].decode('utf-8', errors='ignore'))
    return label.rstrip(' .')


def new_session(pid, cwd):
    if not re.fullmatch(r"[1-9][0-9]*", pid):
        raise ValueError("invalid Bash process identifier")
    started = now()
    clock = dt.datetime.fromisoformat(started).strftime('%H-%M-%S')
    layout = _storage.Layout.for_collector(*locations())
    day = started[:10]
    directory = layout.ensure_day(day) / 'bash'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    label = directory_label(cwd)
    counter = 1
    while True:
        suffix = '' if counter == 1 else '_' + str(counter)
        filename = clock + '_' + (label + '_' if label else '') + pid + suffix + '.jsonl'
        try:
            descriptor = os.open(directory / filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                stream.write(json.dumps({'event': 'session_start', 'started_at': started,
                                         'cwd': cwd}, ensure_ascii=False) + '\n')
            break
        except FileExistsError:
            counter += 1
        except OSError as error:
            if not label or (error.errno != errno.ENAMETOOLONG
                             and getattr(error, 'winerror', None) not in (123, 206)):
                raise
            label = ''
    return {
        'date': day,
        'filename': filename, 'storage_settings': layout.settings,
        'workspace_id': layout.record(day)['workspace_id'],
    }


def record():
    fields = sys.stdin.buffer.read().split(b"\0")
    if len(fields) != 7 or fields[-1]:
        raise ValueError("invalid recorder payload")
    context, event, cwd, command, status, started = [
        value.decode("utf-8", errors="replace") for value in fields[:-1]
    ]
    session = json.loads(context)
    filename = session['filename']
    if (not filename.endswith('.jsonl') or Path(filename).name != filename
            or '\\' in filename):
        raise ValueError('invalid session filename')
    if event not in ('command', 'session_end'):
        raise ValueError('invalid recorder event')
    row = {'event': event, 'cwd': cwd,
           'completed_at' if event == 'command' else 'ended_at': now()}
    if event == 'command':
        command = command.lstrip()
        row.update(command='<redacted:possible-secret>' if SECRET.search(command) else command,
                   exit_status=int(status),
                   started_at=dt.datetime.fromtimestamp(int(started)).astimezone().isoformat())
    layout = _storage.Layout(session['storage_settings'])
    day = session['date']
    state = layout.record(day)
    if (not state or state['disposition'] == 'discarded'
            or state['workspace_id'] != session['workspace_id']):
        return
    directory = layout.daily / day / 'bash'
    flags = os.O_APPEND | os.O_WRONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(directory / filename, flags)
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    operation = sys.argv[1]
    if operation == "session":
        print(json.dumps(new_session(sys.argv[2], sys.argv[3]), ensure_ascii=False))
    elif operation == "record":
        record()
    else:
        raise ValueError("unknown recorder operation")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, IndexError, UnicodeError) as error:
        print(f"my-big-brother Bash recorder: {error}", file=sys.stderr)
        sys.exit(1)
