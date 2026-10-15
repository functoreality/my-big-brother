# Optional Bash recording

English | [简体中文](zh-CN/BASH.md)

The Bash collector records interactive command activity without reading or
changing Bash history. It works independently of `HISTCONTROL`, `HISTIGNORE`,
and whether history is enabled. Repeated commands produce repeated records.

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

The helper writes `daily/YYYY-MM-DD/bash/` using the system calendar date,
equivalent to `date +%F`. It registers dates before writing.
Commands are assigned by completion time, with start time retained.
A discarded day is skipped without recreating its directory.
The bundled standard-library protocol needs no installed Python package.
The collector works without installing or initializing the main application.
An optional `C/storage.json` selects a custom data root. When absent, platform
defaults apply. Runtime registration is created automatically. An invalid
existing configuration or damaged registry reports an error.
See [Storage v2](STORAGE.md) for initialization.

Log filenames use the recorder's session start time and Bash process ID,
for example `2026-10-15T093012+0800-12345.jsonl`. This is when the recorder is
enabled in the shell, rather than the first command's time. The process ID
distinguishes local shells enabled in the same second. No random suffix is used.
The same session keeps its filename when writing into later date directories.
The filename stem is also the JSONL `session_id`.
New log files use POSIX mode `0600`.
The recorder does not change the caller's umask or existing file permissions.

Each JSONL record contains `event: "command"`, `session_id`, `started_at`,
`completed_at`, `cwd`, `command`, `exit_status`, `capture_scope`, and `redacted`.
Timestamps include a local UTC offset. `cwd` is the directory before execution.
The collector does not capture command output or terminal screenshots.

## What is captured

This is a lightweight activity trace, not a terminal transcript. A DEBUG hook
captures the first simple command encountered after a prompt. The next prompt
records its start time and the submitted command line's final exit status.
Every record explicitly declares `capture_scope: "first-simple-command"`.

For `printf first; printf second`, the command field is only `printf first`.
The status describes the entire line, including `printf second`. Pipelines,
conditional expressions, functions, aliases, loops, and multiline inputs can
likewise produce partial or expanded command text. Never interpret the field
as a complete original input line, or the status as necessarily belonging to
the captured first command. Function bodies and subprocess activity are not
fully traced. An Analyzer should state these evidence limits when relevant.

Commands that exit or kill the shell before another prompt are not flushed.
There is no guaranteed session-end event. Bash's `exit` command is generally
absent for this reason. The recorder leaves EXIT traps untouched.

The DEBUG hook gets its own timestamp before execution. This requires a small
Python subprocess at command start and another at the following prompt. It can
add noticeable overhead to very short commands.

## Hook compatibility

Existing scalar or array `PROMPT_COMMAND` hooks retain their order and receive
the preceding command's exit status. The recorder does not change history
options, history entries, EXIT traps, or the shell's umask. Sourcing the recorder
twice does not attach a second hook.
Array prompt hooks require Bash 5.1 or newer. Older Bash can use scalar hooks.

The recorder declines attachment when any of these are present:

- An existing DEBUG trap, including integrations based on bash-preexec.
- `functrace` (`set -T`), which changes DEBUG inheritance.
- A nonempty `PS0` pre-command integration.
- A readonly `PROMPT_COMMAND`.

It prints a recoverable diagnostic and leaves the existing integration active.
Bash temporarily hides a caller's DEBUG trap inside a sourced file. To avoid
overwriting such a trap, the check and attachment are deferred to the next
top-level prompt. A diagnostic may therefore appear after sourcing finishes.

Installing other prompt or DEBUG integrations after this recorder can disable
or conflict with recording. Source the recorder last. Dynamically changing
`functrace`, `PS0`, or prompt hooks during a session is unsupported. Start a new
shell after changing integrations.

## Privacy and disabling

Commands may contain private paths, project names, credentials, or personal
text. Files stay local, but selected raw evidence may later be sent to your
configured Analyzer provider. Enable this collector only where appropriate.

The helper replaces the entire command with a redaction marker when it detects
common password, token, secret, API-key, Authorization, sshpass, or URL-password
patterns. This is best-effort filtering. Arbitrary positional secrets, unusual
formats, encoded values, and other private text can still be recorded. Existing
history privacy options do not apply because this recorder does not use history.

Disable recording before entering sensitive commands:

```bash
MBB_BASH_RECORDING=0
# Enter sensitive commands here.
MBB_BASH_RECORDING=1
```

To disable it for a new shell, export `MBB_BASH_RECORDING=0` before sourcing.
To uninstall, remove the source line and open a new shell. There is no automatic
capture deletion in this MVP.

## Tests

Run the isolated compatibility suite from the project root:

```bash
python3 -m unittest discover -s tests -p test_bash_recorder.py -v
```

The Linux tests use temporary home/config/data directories, interactive Bash
subprocesses, and one pseudo-terminal session. They cover duplicate commands,
history filtering and disabling, scalar and array prompt hooks, exit-status
preservation, existing DEBUG and EXIT traps, umask preservation, redaction,
opt-out, shared storage validation, and duplicate attachment. Tests use isolated
subprocesses and do not install a recorder into your shell.
