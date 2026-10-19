# Setup

[English](SETUP.md) | [简体中文](zh-CN/SETUP.md)

Give [INSTALLATION.md](../INSTALLATION.md) to an Agent that can work on your
computer. It is the shared English installation guide. The installer discovers
supported local Agent histories, resolves their paths and tells you which
sources will be included. You do not need to know their history directories.
Tell it any sources to exclude, your preferred report language, and whether
you want a daily schedule or optional Bash recording.

## Requirements

- Python 3, with 3.11 or newer recommended. Older versions are unverified
  and compatibility is not guaranteed. The core has no third-party dependencies.
- A clone of this repository in a stable directory.
- At least one selected supported record source, such as Codex/OpenCode history
  or existing Bash, Vim or screenshot records. The executor and inputs are
  independent choices. New recording needs separately chosen collectors.
- A working, authenticated Codex CLI for the bundled unattended launcher.
  Another capable Agent can instead use prepare/task/finish itself.

Use `python3` if that selects your intended Python 3 interpreter. The commands
below show a manual first installation with Codex history. An installing Agent
uses the detected, non-excluded source set. Run them from the cloned repository:

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
`doctor` checks the common configuration and paths, but does not prove Agent
authentication or source-format compatibility. A missing Codex executable does not prevent
another Agent from using `prepare` and `finish`.
Inspect the warnings even when `doctor` exits zero. Capture-root existence
does not prove recording is active. All enabled sources unavailable, or none
enabled, blocks analysis. A readable source with no window entries can return
`empty`, without claiming the user did no work.
Use `--sources workbuddy` for the supported [WorkBuddy layout](WORKBUDDY.md).
Without `--sources`, a fresh `init` uses generic defaults instead of discovering
installed applications. Explicit source selection is recommended for installation.

## Configure your own installation

`paths` reports `config`, `raw_logs`, `memory`, `results` and `checkout`.
Personal configuration and data live outside the repository. Edit the generated
JSON configuration to select sources, output types, report language, or a custom
absolute `results_root`.

For Chinese reports, change the existing language field to:

```json
"language": "zh-CN"
```

This is one field inside `config.json`, not a replacement for the entire file.
English remains the default. This setting affects generated prose, not JSON
field names, commands, or the language of the installed task instructions.

`init` creates ordinary configuration and needed directories. All applications
use `C/raw-logs-path.txt` or platform defaults, without requiring `storage.json`.
Permanent outputs use `results_root`, defaulting to D/memory. All dated runtime
state stays with disposable `raw-logs/DATE` material. Collectors use natural
calendar dates. See [Storage](STORAGE.md) before changing paths.
Reading native Agent histories does not require a new collector plugin.

Optional Vim and screenshot adapters, record formats, and replay assets are
described in [Input sources](INPUT-SOURCES.md).

For an unsupported history format, the installer can ask to develop and test a
[personal reader](EXTENDING.md#add-an-input). Its code stays in `C/readers/`,
selected by an explicit `reader` binding. Upgrades preserve the binding even
when official support is added later. Switching requires your choice.

## Verify a first review

Pick a date with known activity in your selected histories:

```sh
python -m my_big_brother prepare --date 2026-01-15
```

Review the reported entry counts and source gaps. Preparation creates a run
without launching an Agent or publishing reports.

For the bundled Codex launcher, run:

```sh
python -m my_big_brother.analyzers.codex --date 2026-01-15
```

This uses your installed Codex account and can consume quota. Selected evidence
can be sent to that Agent's configured model provider. Without usable evidence,
the Agent records an empty result. With `codex.mode: "exec"` (the default),
`agent-exited` means process exit only. With `mode: "tmux"`, the entry returns
`session-started` and an attach command while the interactive TUI keeps running.
Join that same session to watch or send instructions. tmux needs Linux, macOS
or WSL with tmux installed. Inspect the Agent-written `automation-result.json`
in the returned `launch_dir`, then the resulting reports and their limitations.

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

The shared [automation task](../tasks/daily-review/AUTOMATION.md) also covers
pending post-review work: read the action prompt, perform it in the same Agent,
write the exact action receipt, then call `finish` again. Generic `analyze`
and `due` return work tickets; they do not start an Agent. Use the external
startup command above for Codex, or a native task/local runner for your Agent.
See [Vim/Neovim recording](VIM.md) for the separately installed editor plugin.

## Enable recurring reviews

After one review works, choose a schedule with your installing Agent.
Prefer a native local scheduling feature if your Agent provides one.
For a CLI-only setup, use cron, launchd, or Windows Task Scheduler.
See [Scheduling](SCHEDULING.md) for both routes and examples.

There is no automatic scheduler installer. `init` leaves scheduling disabled.
The project supplies review commands for the latest closed logical day, while
your selected scheduler starts them. Older dates require explicit `--date` reruns.
Test an actual scheduled action in its user account and environment before relying on it.

Bash recording is separately optional. See [BASH.md](BASH.md) before changing
shell startup files. Published results and configuration should be backed up.
Captures and private excerpts are not automatically cleaned in this release.
See [Manual cleanup](CLEANUP.md) for removable run directories, startup logs,
and the formal outputs to retain.
