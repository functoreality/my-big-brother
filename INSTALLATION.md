# Installation for an Agent

Use this guide when a user asks you to install My Big Brother on their machine.
Set up the ordinary cloned repository and personal configuration first.
Do not install a Skill, MCP server, daemon, or scheduler by assumption.

## 1. Confirm the environment

Identify the operating system, an absolute Python 3 executable path, and
the user's preferred stable installation directory. Clone the repository
there, or use the existing clone. Run all commands below with that repository
as the working directory. No dependency installation is required for the core.

Python 3.11+ is recommended. Older versions are unverified and compatibility
is not guaranteed. Do not reject an interpreter solely for being older than
3.11. Check the actual commands below.

Check Python:

```sh
python --version
python -m my_big_brother --help
```

Use `python3` or the selected absolute executable if `python` resolves to an
older interpreter. For unattended reviews, check that Codex is installed,
authenticated, and usable noninteractively. Follow its installed help for
account setup. Do not open or copy credential files.
The official [Codex non-interactive guide](https://learn.chatgpt.com/docs/non-interactive-mode)
describes the execution mode used by the launcher.

On native Windows, the launcher supports a standard npm `codex.cmd` shim by
invoking its adjacent Codex JavaScript entry with Node directly. Node must
also be discoverable. An unrecognized batch wrapper is rejected. Configure
`codex.executable` with an absolute native `codex.exe` path in that case.
The launcher does not concatenate a batch-shell command from configured paths.

Codex is the first unattended backend. Existing OpenCode conversations can
still be an input. If the user only has another capable Agent, it can perform
the interactive prepare/task/finish workflow without a Codex launch.

## 2. Initialize personal paths

Ask which available histories the user wants included before preparation.
For a Codex-only installation:

```sh
python -m my_big_brother init --sources codex
python -m my_big_brother paths
```

For both Agent histories, use `init --sources codex,opencode`. Add `bash` only
when the user also wants its recorded files included. Omitting `--sources`
creates defaults, with optional Vim and screenshot readers disabled.
Explicitly select `vim` or `screenshots` only when their collectors and records
are available. Follow [INPUT-SOURCES.md](docs/INPUT-SOURCES.md) and install
Pillow in the selected interpreter for screenshot contact sheets.
Initialization itself does not
read their contents or install recording hooks.
`--results-root` and `--raw-logs-root` can set absolute custom locations on
first initialization. Existing configuration is preserved rather than replaced.
Change an existing installation by editing its personal config and path file.
`init` with source or path options is for first initialization. For an existing
installation, run it without options to create missing files and retain settings.

Inspect the reported locations before changing configuration. Defaults are:

| System | Configuration directory C | Default data directory D |
| --- | --- | --- |
| Linux | `$XDG_CONFIG_HOME/my-big-brother` or `~/.config/my-big-brother` | `$XDG_DATA_HOME/my-big-brother` or `~/.local/share/my-big-brother` |
| macOS | `~/Library/Application Support/my-big-brother/configs` | `~/Library/Application Support/my-big-brother/data` |
| Windows | `%LOCALAPPDATA%\my-big-brother\configs` | `%LOCALAPPDATA%\my-big-brother\data` |

Linux XDG variables must contain absolute paths. Ensure the installation
Agent, collectors, and scheduled process discover the same C. A desktop
application does not necessarily inherit variables from an interactive shell.
Treat WSL as its own Linux environment, with its own paths and Python.

The shared `C/raw-logs-path.txt` is one UTF-8 line containing an absolute path.
An LF or CRLF line terminator is allowed. Do not add JSON syntax, quotes,
comments, or variables such as `~` or `$HOME`. This path is only for collectors.
The `results_root` path belongs in `C/config.json` and is not shared with them.
By default they resolve to `D/raw-logs` and `D/results`, respectively.
Runtime state stays under `D/state`.

## 3. Configure sources and outputs

Read the generated `config.json` and keep its valid JSON structure. Its
principal settings are:

- `analyzer`: the one unattended backend, currently `codex`.
- `language`: output language, initially `en`.
- `day_start_hour`: the local analysis-day boundary, initially `0`.
- `results_root`: an absolute path outside the installation.
- `sources`: independent `codex`, `opencode`, `bash`, `vim`, and `screenshots` settings.
  Native Agent sources have an `enabled` flag and an absolute `path`.
  Collected sources use the shared raw root unless an explicit reader path
  is configured. A source can be `required`, blocking publication when unavailable.
- `local_profile`: optional absolute JSON path for selected personal rules,
  reference files, output bindings, validators, and post-review operations.
- `outputs`: any supported names from `worklog`, `time-use`, `insights`, and
  `time-estimates`. The generated configuration enables all four.
- `codex`: `executable`, `timeout_seconds`, and an optional `model`.
  Omit `model` to inherit the installed Codex default.

Use the user's actual source paths. Do not scan unrelated accounts or copy
histories into this repository. Disable sources the user does not want read.
Leave unavailable optional sources visibly unavailable rather than inventing
data. Reading native histories does not require a new recording plugin.
Read [PROFILES.md](docs/PROFILES.md) before configuring private extensions.
Keep that profile and its files outside Git. Do not infer operation permission
from the mere presence of a file under `local-tasks/`.

Then run:

```sh
python -m my_big_brother doctor
```

Resolve reported path or analyzer problems needed for the chosen workflow.
Do not claim that a passing diagnostic proves end-to-end analysis succeeds.
`doctor` reports source-path presence, not source-format compatibility or
authentication. It returns a nonzero status if Codex is absent, which does not
prevent a different current Agent from using `prepare` and `finish`.

## 4. Verify input preparation first

Choose a completed date with known activity in the enabled records:

```sh
python -m my_big_brother prepare --date 2026-01-15
```

Inspect the reported run's `manifest.json` and `context.json`. Confirm the
date, timezone offsets, source entry counts, source gaps, and resolved output
paths. The input window includes its start and excludes its end.
The configured boundary can make one analysis day span two natural dates.

A prepared run does not launch an Agent and does not publish final reports.
If records are empty, select a known active date or fix the source settings.
Do not fabricate inputs and present them as the user's actual work.
Omitting `--date` selects the last completed analysis day. An explicit current
date prepares only the elapsed portion of that day, not future activity.
Use `--snapshot-end <ISO timestamp with UTC offset>` on `prepare` or `analyze`
when a fixed cutoff is needed for a controlled rerun or comparison.

## 5. Verify one analysis

Choose either unattended or current-conversation analysis.

For an unattended review:

```sh
python -m my_big_brother analyze --date 2026-01-15
```

This invokes the configured Codex executable and can consume the user's
account quota.
The program checks a completion receipt and structured outputs before
publishing the stable daily files. A process exiting successfully is not
sufficient proof of valid reports. Inspect the command result and output
paths, then review the reports' factual grounding and limitations.
If a personal profile includes `post_review`, publication is followed by a
separate Codex invocation with its declared write directories. `finish` also
performs that configured phase. A failed phase remains pending and is resumed
without regenerating published reports. Profiles define operation idempotency
and their validators, not permission to execute historical instructions.
Without usable evidence, `analyze` returns an empty run without invoking the
Agent. `--allow-empty` is an explicit override for an honest empty review.
An unavailable required source returns `blocked`. Unattended `analyze` and
`due` exit unsuccessfully for that status so a scheduler can report the failure.

For the current Agent, use the prepared run from step 4. Read
`tasks/daily-review/TASK.md`, the related task contracts, and the run's context.
Write to `context.output_paths`, which are staged paths. Write the exact
`completion.json` receipt indicated by `context.completion_example`. Then:

```sh
python -m my_big_brother finish --run-dir /absolute/path/to/the/run
```

If existing results changed after preparation, do not overwrite them by
forcing publication. Prepare again and preserve those changes during review.

## 6. Optional Bash recording

Bash recording is separate from reading existing AI conversations. Only add
the bundled recorder if the user wants future interactive command activity
recorded. Read [BASH.md](docs/BASH.md) and preserve the
user's existing prompt hooks, traps, and history settings.

It writes below `raw-logs/YYYY-MM-DD/bash/`. Explain that command recording
can include private information and that redaction is not comprehensive.
The recorder observes the first simple command after a prompt and the whole
input line's status. It does not depend on history settings, so commands
excluded from history can still be recorded. Conflicting DEBUG/pre-command
integrations cause it to decline attachment rather than replace them.
It does not replace PowerShell recording. Do not source a Bash script from
another shell's startup file.

## 7. Optional scheduling and login catch-up

Once one review works, offer an explicit schedule. Scheduling is not enabled
by initialization. Prefer the user's Agent-native local scheduler when it
can access this installation, the selected evidence, and personal data paths.
Do not add a second OS scheduler for the same work by default.

Choose the executor separately from the trigger:

- A native Agent task can run `prepare`, follow the English daily task using
  the returned run context, then call `finish`. It reviews the last closed
  day by default. The `analyzer` setting does not restrict this route.
- A native command task can invoke `due` as a trigger for the configured
  unattended analyzer. This still launches Codex in the current release.
- For a CLI-only setup without a native scheduler, use the system scheduler
  described below to invoke `due`.

OpenClaw and Hermes provide native scheduling. Treat their task setup as
instructions using this project's existing interfaces, not as pre-tested
launcher or history-reader integrations. See [SCHEDULING.md](docs/SCHEDULING.md)
for official references, the native task prompt, and shared OS templates.
Codex CLI does not provide the Scheduled management interface. OpenAI's
[scheduled-task documentation](https://learn.chatgpt.com/docs/automations)
describes separate app-managed scheduling, including local-project tasks.
Check the installed surface's actual capabilities and local access.

For the bundled Codex launcher, invoke:

```sh
python -m my_big_brother due --max-days 7
```

Use the absolute interpreter path, a stable repository working directory,
the same user's account and config-discovery environment, and a known Codex
executable path. Interactive shell aliases and startup files may not apply.
Capture stdout and stderr outside the repository for diagnosis.
Codex account access and network connectivity must work in that environment.
Confirm that `paths` under the scheduled account reports the same configuration,
results, raw logs, and state paths used during setup. Both XDG configuration
and data values can matter on Linux. A different state location loses access
to the existing completion history even if reports stay in the same place.

`due` considers completed analysis days within its bounded lookback,
oldest first. It skips already successful dates and dates without usable
evidence. Failures can be retried on later invocations. A seven-day lookback
does not promise recovery of all historical gaps.
`due` is a one-shot command, not a background timer. Its catch-up and skip
behavior belongs to the bundled launcher route. A native Agent performing
prepare/task/finish must explicitly handle missed dates if catch-up is wanted.
After adding a source or correcting a completed review's evidence, rerun that
date explicitly with `analyze --date`. The completion history does not perform
automatic source-change detection for already successful dates.

### Linux

Use the user's cron service for a daily trigger, with a cron entry that
changes to the absolute installation directory before invoking the absolute
Python executable. Properly quote both paths, including spaces. Explicitly
carry absolute XDG values if the installation depends on them.

A user service or login startup entry can invoke the same `due` command for
catch-up. A cron `@reboot` entry means cron startup, not user login, and may run
before network or Agent account access is ready. Choose the trigger based on
the user's intended environment. Avoid putting a long review in every shell
startup file.

### macOS

Use a per-user LaunchAgent when requested. Set `ProgramArguments` as an array
containing the absolute Python executable, `-m`, `my_big_brother`, `due`,
`--max-days`, and `7`. Set `WorkingDirectory` to the absolute repository path.
Use `StartCalendarInterval` for the requested daily time and optionally
`RunAtLoad` for login catch-up. Set explicit output and error log paths.
Paths with spaces remain single array values rather than shell snippets.
See Apple's [launchd property-list reference](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5)
and [timed-job guidance](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html).

### Windows

Use a task for the user in Task Scheduler when requested. Set the program
to the absolute Python executable, arguments to
`-m my_big_brother due --max-days 7`, and "Start in" to the repository directory.
Use a daily trigger and optionally an "At log on" trigger. Run under the
account whose configuration and Agent authentication you checked.
Use separate program, arguments, and working-directory fields rather than
constructing a command through `cmd.exe` or PowerShell.
Microsoft documents these separate fields in
[ExecAction](https://learn.microsoft.com/windows/win32/taskschd/execaction).

These are scheduling instructions, not an automated scheduler installer.
Verify the actual scheduled action in its intended user environment, first
with a one-off run and then with its trigger. macOS and Windows scheduled
actions have not been verified on those systems in this release.

## 8. Handoff and maintenance

Give the user the installation path, configuration location, results root,
enabled sources, enabled outputs, and any schedule actually installed.
Show one reviewed daily report and explain the observed coverage.

To move results, stop active reviews, move the results directory, and update
`results_root`. Collectors do not need changing. To move raw logs, pause
collectors and reviews, move the records, update `raw-logs-path.txt`, and
restart the collectors so they rediscover the location.

Back up configuration and published results. Runtime state includes completion
history as well as private excerpts, so preserve relevant state when migrating
an installation. This MVP does not perform automatic raw-log or run-material
cleanup. Avoid deleting material still being recorded or used by a review.
