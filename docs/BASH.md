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

Git Bash users whose interpreter is named `python` can resolve it before
loading: `export MBB_PYTHON="$(command -v python)"`. Verify that interpreter
first. This selection does not establish native Windows recording compatibility.

Python virtual environments are supported. The helper uses only the standard
library and does not need this package installed. Keep the cloned project at
the path used by your shell configuration.

## Locations and format

Each recorded shell process owns exactly one JSONL under
`raw-logs/YYYY-MM-DD/bash/`, using the local date when the recorder is enabled.
The helper creates the file once at startup. Bash caches the plain file path.
Later appends neither reread the locator nor select a directory date.
The path stays fixed across
midnight, months of uptime, `cd`, or later shared configuration changes.
Command start and completion times remain actual times. If the file or its
parent is removed, appends stop without recreating it or selecting a new date.

The collector works independently, using only Python's standard library.
It reads `C/raw-logs-path.txt` once at startup, or uses the platform data
folder's `raw-logs` when the file is absent. The TXT contains one UTF-8 absolute
capture-root path, without quotes, comments or variable expansion. One final
LF or CRLF is allowed. Spaces in the path are preserved. A present invalid
file is an error. It neither reads `storage.json` nor creates runtime registries
or user configuration. The main application and Vim share this locator.
See [Storage](STORAGE.md) for platform defaults and initialization.

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
  Completion is observed at the next prompt or normal shell exit. `cwd` is
  the shell directory immediately before the submitted input starts executing.
  For `cd child`, it is the directory from which the change was requested.
  For `cd child; run`, it describes the whole input's initial context, not the
  directory of every internal command. No second directory field is recorded.
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

JSONL records repeated input, leading-space input and commands matching
`HISTIGNORE`, independently of native history filtering. Bash's own history
still applies the user's `HISTCONTROL`, `HISTIGNORE` and size settings.
`HISTSIZE=0`, an unset or empty `HISTFILE`, and `HISTFILESIZE=0` do not prevent
JSONL capture. The recorder does not assign `HISTFILE` or write to it.

While waiting for input, the hook temporarily relaxes history filtering and,
when needed, reserves one extra entry. Before execution it observes the full
input, restores the original filters, and submits it to Bash's history builtin.
With an original size of zero it removes the observation without retaining it.
It then restores the size before commands and prompt hooks execute.
It does not use `BASH_COMMAND` as the recorded text.

**Recording pause:** `set +o history` disables command capture. The recorder
respects that choice and does not force history on. If history is already off
when the recorder is sourced, it prints a notice to stderr immediately.
Later on-to-off transitions produce a notice before the next input.
The first prompt does not repeat a startup notice, and continued pauses stay quiet.
Session start/end times and directories are still recorded.
`set -o history` resumes capture of subsequent inputs.
This is a supported exclusion, distinct from disabling history-file persistence.

The complete input is observed before execution, so an input that turns history
off may itself be recorded, including later commands in that same compound or
multiline input. Submit `set +o history` separately and wait for the next prompt
before sensitive input. Switching it off does not erase existing records or
make the session untraceable.

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
input observation. Continuous recording remains opt-in. To pause command
recording, set `MBB_BASH_RECORDING=0`, then restore it to `1` when wanted.
Session-end events still identify normal closure. To disable a new session,
export `MBB_BASH_RECORDING=0` before sourcing. To uninstall, remove the source
line and open a new shell. This does not delete existing captures.

## Privacy

The recorder keeps the original best-effort redaction rule. Commands containing
assignments to token, secret, password or API-key names, `sshpass`, or
`Authorization:` are replaced with `<redacted:possible-secret>`.
Other secrets and private text may still be recorded. History exclusions do
not disable this recorder. Pause with `MBB_BASH_RECORDING=0` before sensitive
input and set it back to `1` afterward. Selected evidence can be
sent to the configured Analyzer provider. File names also reveal directory hints.

If a command was also saved in native history, JSONL redaction does not remove
that other copy. Native history may remain only in memory or exclude commands,
so it does not establish that a secret has already been saved to disk or leaked.
The extra JSONL copy can have different retention, synchronization and analysis
destinations. Redaction reduces exposure in this copy, with limited protection
and no guarantee that all secrets are detected.

## Why Bash uses a Python helper

The sourced Bash file observes shell events, full history input, exit status
and the command's starting directory. It must run inside the interactive shell
to see that state. Capturing the directory uses the existing pre-execution
hook and one shell variable. It adds no Python invocation.

The helper handles JSON escaping, Unicode and multiline text, local timestamps
with UTC offsets, platform paths and append-only files. The original personal
script used `/usr/bin/jq` and GNU-specific `date` options. Python's standard
library replaces those dependencies with one portable implementation.

The cost is requiring Python and starting a helper process at session start,
command completion and normal session end. It is not a background Python
service. No Python process is added solely to capture the starting directory.
Only Bash hooks observe shell activity. The helper does not execute captured
commands or launch an analysis Agent. Native macOS and Windows execution
remain unverified, as described above.

## Tests

```sh
python3 -m unittest discover -s tests -p test_bash_recorder.py -v
```

The isolated Linux suite covers native-history comparisons, duplicate policies,
history-file settings, filtering independence, compound and multiline input,
event fields, existing hooks,
exit status, permissions, fixed start-date paths, and a real pseudo-terminal.
It checks that a session-start event exists before a blocking command finishes.
No real shell configuration, history, or schedule is changed.
