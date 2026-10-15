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

_spec = importlib.util.spec_from_file_location("mbb_collector_paths", Path(__file__).with_name("paths.py"))
_paths = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_paths)


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
    directory = _paths.capture_root(*_paths.platform_paths()) / started[:10] / 'bash'
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
    return str(directory / filename)


def record():
    fields = sys.stdin.buffer.read().split(b"\0")
    if len(fields) != 7 or fields[-1]:
        raise ValueError("invalid recorder payload")
    filename, event, cwd, command, status, started = [
        value.decode("utf-8", errors="replace") for value in fields[:-1]
    ]
    path = Path(filename)
    if event not in ('command', 'session_end'):
        raise ValueError('invalid recorder event')
    row = {'event': event, 'cwd': cwd,
           'completed_at' if event == 'command' else 'ended_at': now()}
    if event == 'command':
        command = command.lstrip()
        row.update(command='<redacted:possible-secret>' if SECRET.search(command) else command,
                   exit_status=int(status),
                   started_at=dt.datetime.fromtimestamp(int(started)).astimezone().isoformat())
    flags = os.O_APPEND | os.O_WRONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except FileNotFoundError:
        return
    with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    operation = sys.argv[1]
    if operation == "session":
        print(new_session(sys.argv[2], sys.argv[3]))
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
