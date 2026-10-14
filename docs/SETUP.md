# Setup

[English](SETUP.md) | [简体中文](zh-CN/SETUP.md)

Give [INSTALLATION.md](../INSTALLATION.md) to an Agent that can work on your
computer. It is the shared English installation guide. Tell the Agent which
histories you want included, your preferred report language, and whether you
want a daily schedule or optional Bash recording.

## Requirements

- Python 3.11 or newer. The core has no third-party dependencies.
- A clone of this repository in a stable directory.
- Codex or supported OpenCode SQLite history as input. Bash is optional.
- A working, authenticated Codex CLI for the bundled unattended launcher.
  Another capable Agent can instead use prepare/task/finish itself.

Use `python3` if that is your Python 3.11+ command. Run these commands from
the cloned repository:

```sh
python -m my_big_brother init --sources codex
python -m my_big_brother paths
python -m my_big_brother doctor
```

Use `--sources codex,opencode` for both native histories. Initialization does
not install recording hooks or schedules. It preserves existing settings.
Source selection with `--sources` is for first initialization. For an existing
installation, edit the personal config to change sources. Run `init` without
options to create missing files without replacing existing settings.
`doctor` checks paths and the launcher, but does not prove authentication or
source-format compatibility. A missing Codex executable does not prevent
another Agent from using `prepare` and `finish`.

## Configure your own installation

`paths` reports the locations of `config.json`, `raw-logs-path.txt`, results,
and runtime state. They live outside the repository. Edit the generated JSON
configuration to select sources, output types, report language, or a custom
absolute `results_root`.

For Chinese reports, change the existing language field to:

```json
"language": "zh-CN"
```

This is one field inside `config.json`, not a replacement for the entire file.
English remains the default. This setting affects generated prose, not JSON
field names, commands, or the language of the installed task instructions.

Collectors share only the absolute raw-log path in `raw-logs-path.txt`.
Do not put results paths or JSON syntax in that file. Reading native Agent
histories does not require a new collector plugin.

Optional Vim and screenshot adapters, record formats, and replay assets are
described in [Input sources](INPUT-SOURCES.md).

## Verify a first review

Pick a date with known activity in your selected histories:

```sh
python -m my_big_brother prepare --date 2026-01-15
```

Review the reported entry counts and source gaps. Preparation creates a run
without launching an Agent or publishing reports.

For the bundled Codex launcher, run:

```sh
python -m my_big_brother analyze --date 2026-01-15
```

This uses your installed Codex account and can consume quota. Selected evidence
can be sent to that Agent's configured model provider. Without usable evidence,
the analyzer is skipped. Inspect the resulting files and their limitations.

Alternatively, ask your current Agent to follow
[TASK.md](../tasks/daily-review/TASK.md) with the prepared run's context.
It writes staged reports and a completion receipt, then runs:

```sh
python -m my_big_brother finish --run-dir /absolute/path/to/the/run
```

Omit `--date` to review the last closed analysis day. Setting a custom
`day_start_hour` changes that day's boundary. Generated outputs may include a
Worklog, Time Use Markdown and JSON, Daily Insights, and duration samples.
Each output can be selected independently.

## Enable recurring reviews

After one review works, choose a schedule with your installing Agent.
Prefer a native local scheduling feature if your Agent provides one.
For a CLI-only setup, use cron, launchd, or Windows Task Scheduler.
See [Scheduling](SCHEDULING.md) for both routes and examples.

There is no automatic scheduler installer. `init` leaves scheduling disabled.
The project supplies review commands and catch-up logic, while your selected
scheduler starts them. Test an actual scheduled action in its user account
and environment before relying on it.

Bash recording is separately optional. See [BASH.md](BASH.md) before changing
shell startup files. Published results and configuration should be backed up.
Raw logs and private excerpts are not automatically cleaned in this release.
