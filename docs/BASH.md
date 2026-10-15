# Optional Bash recording

English | [简体中文](zh-CN/BASH.md)

The Bash collector records interactive history input, with session start,
command completion, and normal session end events. It preserves complete
compound input instead of recording only the first executed simple command.

This collector is opt-in. Agent session history alone is sufficient to use the
MVP. Do not install it in someone else's shell without their permission.

## Installation

Use Bash and Python 3, with Python 3.11+ recommended. Older Python versions
are unverified and compatibility is not guaranteed. Add this line near the
end of your interactive `.bashrc`,
after prompt integrations:

```bash
source "/absolute/path/to/my-big-brother/collectors/bash/session-recorder.sh"
```

On macOS, use the startup file from which your interactive Bash configuration
is actually loaded. A login shell might read `.bash_profile` rather than
`.bashrc`. The script uses syntax available in Bash 3.2, but this release has
been executed only on Linux Bash. macOS execution remains unverified.
For Windows, WSL follows Linux paths. Native Windows Python with Git Bash has
not been tested. This is a Bash collector, not a PowerShell or Zsh collector.

If `python3` is not your intended Python installation, configure its executable
before sourcing the recorder:

```bash
export MBB_PYTHON="/absolute/path/to/python3"
source "/absolute/path/to/my-big-brother/collectors/bash/session-recorder.sh"
```

Python virtual environments are supported. The helper uses only the standard
library and does not need this package installed. Keep the cloned project at
the path used by your shell configuration.

## Locations and format

Each recorded shell process owns exactly one JSONL under
`daily/YYYY-MM-DD/bash/`, using the local date when the recorder is enabled.
The helper registers that date and creates the file once at startup.
The path stays fixed across midnight, months of uptime, `cd`, or later shared
configuration changes. Command start and completion times remain actual times.
If its start-date workspace is discarded or replaced, the session stops writing
without recreating it or switching to today's directory.
The bundled standard-library protocol needs no installed Python package.
The collector works without installing or initializing the main application.
An optional `C/storage.json` selects a custom data root. When absent, platform
defaults apply. Runtime registration is created automatically. An invalid
existing configuration or damaged registry reports an error.
See [Storage v2](STORAGE.md) for initialization.

Filenames use `HH-MM-SS_<initial-directory-name>_<pid>.jsonl`, for example
`09-30-12_my-project_12345.jsonl`. Time means when recording is enabled, not
the first command's time. The parent supplies the date. No timezone or random
suffix is displayed. A name collision adds `_2`, `_3`, and so on, without
overwriting or appending to another session's file.

The directory hint is the initial cwd's basename. Unsafe filename characters
become `_`. Names longer than 28 characters keep the first 18 and last 8,
separated by `..`. A 64-byte UTF-8 limit also preserves both ends without
splitting characters. An empty hint or a path-length restriction omits it.
The initial full path and startup timestamp are written once in `session_start`.
There is no per-command session ID, PID, or repeated session metadata.
New log files use POSIX mode `0600`. The recorder does not change the caller's
umask or existing file permissions.

## Events and timing

- `session_start`: `event`, `started_at`, and initial `cwd`. Written as soon
  as recording starts, even if the first command then runs for hours.
- `command`: `event`, `started_at`, `completed_at`, `cwd`, `command`, and
  `exit_status`. Start time comes from Bash history and has second precision.
  Completion is observed at the next prompt or normal shell exit. As in the
  original recorder, `cwd` is the directory after execution, including for `cd`.
- `session_end`: `event`, `ended_at`, and final `cwd`. Written on normal exit.
  A recorded `exit 7` command retains status 7 before the end event.

Timestamps use actual local time with a UTC offset. A file identifies its
session. The reader searches every retained start-date folder, filters events
by actual time, and can attach an earlier session-start event as context.
It does not copy old commands into a later day's activity.
A killed process, crash, or power loss may prevent command completion and
session-end events. This is not a terminal transcript or a live command-start
stream. Command output is not recorded.

## History compatibility

Repeated commands are recorded under `ignoredups`, `ignoreboth`, `erasedups`,
and the duplicate-only `&` pattern in `HISTIGNORE`. Your native history still
applies its original rules. Other `HISTIGNORE` patterns and leading-space
exclusion under `ignorespace` or `ignoreboth` continue to exclude input.
Disabled history or `HISTSIZE=0` produces no command events, while session
boundaries are still recorded. The recorder does not enable history.

To observe duplicates, the hook temporarily relaxes duplicate suppression
while waiting for input. Before execution it restores the original settings
and passes the full input through Bash's own history builtin. It does not use
`BASH_COMMAND` as the recorded text. Prompt hooks run with the original settings.
The JSONL format does not change with your history policy.

When the history list reaches `HISTSIZE`, temporarily reserving one slot and
restoring the limit can renumber history entries. History content and duplicate
policy are preserved, but numeric expansion such as `!123` may refer to a
different entry. Do not install this recorder if stable history numbers are
required. This tradeoff avoids dropping an old history entry just to observe
a duplicate. Commands or extensions that manipulate history can have additional
interactions. Test your own integrations before relying on them.

## Hooks and disabling

Existing scalar or array `PROMPT_COMMAND` hooks keep their order and receive
the preceding command's exit status. Existing DEBUG and EXIT actions are
chained, not discarded. `PS0`, functrace and repeated sourcing are covered by
isolated Linux tests. Array prompt hooks require Bash 5.1 or newer.
A readonly `PROMPT_COMMAND` prevents installation. Dynamic replacement of
prompt or trap integrations after loading is unsupported. Open a new shell
after changing integrations or upgrading the recorder.

`HISTCONTROL`, `HISTIGNORE`, and finite `HISTSIZE` must be writable for temporary
duplicate observation. Continuous recording remains opt-in. To pause command
recording, set `MBB_BASH_RECORDING=0`, then restore it to `1` when wanted.
Session-end events still identify normal closure. To disable a new session,
export `MBB_BASH_RECORDING=0` before sourcing. To uninstall, remove the source
line and open a new shell. This does not delete existing captures.

## Privacy

The recorder keeps the original best-effort redaction rule. Commands containing
assignments to token, secret, password or API-key names, `sshpass`, or
`Authorization:` are replaced with `<redacted:possible-secret>`.
Other secrets and private text may still be recorded. Use history exclusions
or pause recording before entering sensitive input. Selected evidence can be
sent to the configured Analyzer provider. File names also reveal directory hints.

## Tests

```sh
python3 -m unittest discover -s tests -p test_bash_recorder.py -v
```

The isolated Linux suite covers native-history comparisons, duplicate policies,
privacy exclusions, compound and multiline input, event fields, existing hooks,
exit status, permissions, fixed start-date paths, and a real pseudo-terminal.
It checks that a session-start event exists before a blocking command finishes.
No real shell configuration, history, or schedule is changed.
