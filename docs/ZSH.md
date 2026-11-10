# Optional Zsh recording

English | [简体中文](zh-CN/ZSH.md)

The bundled Zsh collector records full interactive input, command completion,
and normal session boundaries. The separate `zsh` reader makes those records
available to the daily review. Neither installing the project nor enabling the
reader starts recording. Adding shell hooks requires permission to record
future input. An installing or updating Agent can reuse permission that covers
this recording, verify it and report the change without asking again.
See [source maintenance](../INSTALLATION.md#adding-sources-during-maintenance)
for scope and exclusions.

## Installation

Use Zsh and Python 3, with Python 3.11+ recommended. A contributed macOS arm64
installation report records isolated tests with Zsh 5.9, Python 3.9.6 and
Python 3.13, plus a synthetic smoke test through the actual `.zshrc`.
That report does not verify other Zsh versions or platforms.
The isolated tests also run with Zsh 5.9 on Linux. These checks do not cover
every third-party prompt framework or replace a test of your own integrations.

After backing up the active interactive `.zshrc`, add this near its end,
after other prompt integrations:

```zsh
source "/absolute/path/to/my-big-brother/collectors/zsh/session-recorder.zsh"
```

If `ZDOTDIR` selects a different startup directory, edit that directory's
`.zshrc`. Use this collector only in Zsh. The Bash collector has its own
[Bash instructions](BASH.md).

The collector uses `python3` by default. To choose a verified interpreter,
set `MBB_PYTHON` before sourcing:

```zsh
export MBB_PYTHON="/absolute/path/to/python3"
source "/absolute/path/to/my-big-brother/collectors/zsh/session-recorder.zsh"
```

Open a new interactive shell after changing configuration or upgrading.
Repeated sourcing does not add duplicate hooks or another recording file.
Noninteractive Zsh does not attach the recorder.
The selected Python and helper path stay fixed for that recorded shell.
The helper uses only the standard library and needs no package installation.
Keep the checkout at the path used in `.zshrc`.
If hook loading or registration fails, the recorder reports that it is not
attached. Fix the environment, then source it again or open a new shell.
A recording file's existence does not prove that hooks attached successfully.

## Reading records

For a new installation with Zsh as the only selected input:

```sh
python -m my_big_brother init --sources zsh --day-start-hour 4
python -m my_big_brother doctor
```

For an existing installation without a `zsh` entry, add
`"zsh": {"enabled": true}` to `sources` in `C/config.json`, preserving its
other settings and source selections. If a `zsh` entry already exists, retain
its `path`, `required` and any personal `reader` binding. Official support does
not replace a personal reader. Compare and switch only with the user's choice,
following [Extending](EXTENDING.md#add-an-input).
Do not rerun initialization to replace an existing configuration.
The reader is disabled by default and reads the shared raw-log root unless
`sources.zsh.path` explicitly selects another root. Reader selection does not
install shell hooks. `doctor` reports whether matching JSONL files exist,
which does not prove active or complete recording.

A standalone collector works without My Big Brother configuration. It selects
the root once from `C/raw-logs-path.txt`, or the platform data directory's
`raw-logs` if that locator is absent. The locator contains one UTF-8 absolute
path, optionally ending in LF or CRLF. Spaces are preserved. Quotes, variable
expansion, relative paths and extra lines are not supported. An existing
malformed locator is an error. The collector does not read `config.json` or
`storage.json`, register dates, or start an analysis Agent.
See [Storage](STORAGE.md) for platform defaults.

## Storage and events

Each shell owns one `raw-logs/YYYY-MM-DD/zsh/*.jsonl` file. Its date and
initial directory are frozen when recording starts, even across midnight,
months of uptime, directory changes or later locator edits.
Appends do not recreate a removed recording file or its parent.
Filenames follow the Bash convention
`HH-MM-SS_<initial-directory-name>_<pid>.jsonl`, with a bounded directory hint
and a numeric suffix on collision. New files use mode `0600` without changing
the caller's umask. Timestamps use actual local time with a UTC offset.

- `session_start` contains `event`, `started_at` and initial `cwd`.
  It is written immediately when the recorder attaches.
- `command` contains `event`, `started_at`, `completed_at`, `cwd`, `command`
  and `exit_status`. `preexec` observes the complete submitted input, including
  compound and multiline input, leading spaces and unexpanded alias text.
  Start time is the pre-execution system time with second precision.
  The directory is the shell's cwd before the whole input executes.
  Completion is observed at the next prompt or normal shell exit.
- `session_end` contains `event`, `ended_at` and the final `cwd`.
  A normal `exit 7` records that input with status 7 before the boundary.
  EOF also produces the normal end boundary.

Files identify sessions. Commands do not repeat session IDs or startup metadata.
The reader visits all retained start-date directories, filters actual event
timestamps within the half-open review window, and can attach an earlier
`session_start` as context. Commands are selected by `completed_at`.
It reads only the date/Zsh layout beneath its configured root, including
when that root is explicit. It does not import native `.zsh_history` files or
scan alternate layouts. See [Input sources](INPUT-SOURCES.md).

## History, hooks and coverage

The recorder adds `preexec`, `precmd` and `zshexit` hooks using `add-zsh-hook`.
It preserves existing named and array hooks, native history and shell options.
Duplicate filters, leading-space exclusions, `zshaddhistory` exclusions,
`HISTSIZE=0`, an unset `HISTFILE` and `SAVEHIST=0` do not exclude JSONL input.
It does not replay or renumber native history entries.
The recorded text is what native `preexec` supplies. For example,
`HIST_REDUCE_BLANKS` can normalize whitespace, so this is not a byte-for-byte
audit of what was typed.

Zsh stops later hooks when an earlier hook returns nonzero. Such integrations
can prevent capture or completion. Readonly hook arrays prevent attachment.
Dynamically replacing hooks after attachment is unsupported. Check your own
prompt integrations rather than assuming complete coverage.

The collector records completed foreground input, not terminal output,
individual internal commands, background-job completion or focused work time.
An `exec` replacement does not run `zshexit`. That pending input has no
completion event or session-end event. Force termination, crashes and power
loss can likewise leave the pending input and boundary unrecorded.
Missing command events do not establish inactivity.

## Pausing and privacy

To pause subsequent command capture, submit this as a separate input and
wait for the next prompt:

```zsh
MBB_ZSH_RECORDING=0
```

Resume with `MBB_ZSH_RECORDING=1`. A command's capture choice is made before
its input executes. The input that switches recording off may itself be
recorded, including other operations in the same input. Session boundaries
remain during a pause. Setting `MBB_ZSH_RECORDING=0` before initial sourcing
prevents attachment entirely. To uninstall, remove the source line and open
a new shell. Existing captures remain.

Native history exclusions do not provide recorder privacy. The best-effort
redaction rule replaces an entire input containing assignments to token,
secret, password or API-key names, `sshpass`, or `Authorization:` with
`<redacted:possible-secret>`. Other sensitive text can still be recorded.
Redaction does not alter any copy saved in native history.
Filenames also expose an initial directory hint.
Selected evidence can be sent to the configured Analyzer provider for review.
Pause separately before sensitive input, and manage capture retention.

## Tests

```sh
python3 -m unittest discover -s tests -p 'test_zsh*.py' -v
```

Tests use synthetic evidence and isolated interactive Zsh processes, including
a real pseudo-terminal, without changing the user's hooks, history or schedule.
They cover multiline and compound input, alias text, pre-execution directories,
exit status and EOF, native-history comparisons, existing hooks, pause/resume,
redaction, private files, fixed dates, locator handling and review preparation.
