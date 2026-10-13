# My Big Brother

Turn your recorded work with AI Agents into a daily Worklog, a timeline,
practical insights, and cautious task-duration samples.

My Big Brother prepares local evidence and lets an Agent lead the review.
It keeps records that you can later use for weekly reports, project summaries,
or background for another Agent. The first release is an ordinary local
repository, without a service, Skill, or MCP server.

## What it supports

- Inputs: native Codex session files and OpenCode's supported SQLite history.
  A bundled Bash recorder is optional. Vim and screenshots are not included.
- Unattended analysis: Codex, using your installed login and default model
  unless you configure a model explicitly.
- Interactive analysis: your current Agent can prepare inputs, follow the
  same Markdown task, and submit results without launching another Agent.
- Outputs: Worklog, Time Use in Markdown and JSON, Daily Insights, and
  conservative duration samples. Each output can be enabled independently.

Input sources and the unattended analyzer are separate choices. You can read
OpenCode history while using Codex for the daily review. The `analyzer` setting
does not restrict the Agent you use to ask questions about existing results.

Sparse AI conversations cannot reconstruct everything you did at your computer.
Reports state their coverage and distinguish recorded work, inferred activity,
and unknown human attention. Task elapsed time is not treated as focused effort.
OpenCode's older directory-based JSON storage is not supported. Source-format
errors are reported as gaps, not silently treated as an empty workday.

## Get started

Give [INSTALLATION.md](INSTALLATION.md) to an Agent that can work on your
machine. It describes setup, checks, a first review, and optional scheduling.
Python 3.11 or later is required. The core uses only the standard library.
Unattended analysis additionally requires a working Codex CLI.

From this repository:

```sh
python -m my_big_brother init --sources codex
python -m my_big_brother doctor
python -m my_big_brother analyze --date 2026-01-15
```

Choose a date that actually has records. The analyzer uses your Agent account
and may consume its quota. It writes personal data outside the installation.
The executing Agent can send selected evidence to its configured model
provider, according to that Agent's settings.
Choose `--sources codex,opencode` to include both histories, or edit the
generated personal config to enable the sources you want.

For a review in your current Agent conversation:

```sh
python -m my_big_brother prepare --date 2026-01-15
```

Give the reported run directory and
[daily-review/TASK.md](tasks/daily-review/TASK.md) to that Agent. Once it has
written the staged outputs and completion receipt, validate and publish them:

```sh
python -m my_big_brother finish --run-dir /absolute/path/to/the/run
```

Scheduled catch-up uses the same review path:

```sh
python -m my_big_brother due --max-days 7
```

It examines completed analysis days in the bounded lookback, oldest first,
skips successful reviews, and retries failed days on a later invocation.
Days without usable records are skipped rather than reported as analyzed.
Scheduling is optional and is not installed by default.

## Personal files

Run `python -m my_big_brother paths` to find configuration, raw logs, results,
and runtime state. Your installation can be moved or updated without storing
personal history inside Git.

- `config.json` selects sources, outputs, language, and the analyzer.
- `raw-logs-path.txt` contains the one shared absolute path for collectors.
- Results have stable dated paths under `records/`.
- Runtime state holds indexes, excerpts, drafts, diagnostics, and completion
  history outside the repository.

Native Agent histories stay in their own locations. This MVP does not
automatically delete raw logs or run materials. Review and manage their disk
usage separately. Excerpts can contain private conversation text.
The optional Bash recorder is described in [BASH.md](docs/BASH.md).

Another Agent can discover results through `paths` and read only the relevant
dated reports. A useful global instruction is: "For my recorded work history,
consult My Big Brother at <installation path> and use its paths command."
Installing this repository does not automatically expose it to every Agent.

## Scope and extension

The portable core is intended for Linux, macOS, and Windows. Development and
local execution use Linux. Complete macOS and Windows runs and their actual
scheduled actions require validation on those systems. Bash support applies
to Bash environments, including WSL as
a separate environment, and does not record PowerShell.

There is no built-in weekly-report generator or long-term knowledge updater
yet. Existing daily files can be summarized by your Agent. See
[EXTENDING.md](docs/EXTENDING.md) for the boundaries between collectors,
input adapters, analysis tasks, and analyzer launchers.
