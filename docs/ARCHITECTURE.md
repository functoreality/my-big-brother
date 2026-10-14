# Architecture

[English](ARCHITECTURE.md) | [简体中文](zh-CN/ARCHITECTURE.md)

My Big Brother is a local repository with an Agent-led review workflow.
Python prepares evidence and manages publication. Markdown tasks tell the
Agent how to interpret that evidence and produce useful records.
The core uses only the standard library. Python 3.11+ is recommended.
Older versions are unverified and compatibility is not guaranteed.

## Components

```text
my_big_brother/
  sources/          Read native histories and collected logs
  analyzers/        Launch an unattended Agent
  config.py         Personal JSON configuration
  paths.py          Platform paths and the shared raw-log locator
  runner.py         Prepare, validate, publish, and track completion
tasks/daily-review/ Shared English analysis instructions
collectors/bash/    Optional recording in the host shell
docs/               English reader documentation
  zh-CN/            Chinese reader documentation
examples/synthetic/
  en/               Original English reports
  zh-CN/            Chinese translations
  *.json            Shared structured examples
```

Input sources, analysis instructions, and analyzer launchers are independent.
For example, Codex can review OpenCode records. A different current Agent can
perform the same review through `prepare` and `finish` without a Codex launch.
`analyzer` records the preferred executor name. The startup entry selects
the actual executable; common review commands never start an Agent.

## Personal storage

Installation files are separate from configuration and personal records.
Platform defaults for configuration directory C and data directory D are
listed in [INSTALLATION.md](../INSTALLATION.md).

```text
C/
  config.json        Sources, outputs, language, results_root, analyzer
  raw-logs-path.txt  One absolute UTF-8 path shared by collectors
  local-tasks/       Reserved for user-supplied instructions
D/
  raw-logs/          Default collector destination, configurable
    YYYY-MM-DD/
      bash/
  results/           Default publication destination, configurable
    records/
      worklog/DATE.md
      time-use/DATE.md
      time-use/data/DATE.json
      insights/DATE.md
      time-estimates/DATE.json
  state/             Run materials and completion history
```

Collectors discover the same C and read only `raw-logs-path.txt` for their
destination. The main project reads `results_root` from `config.json`.
Changing the results location therefore does not require collector changes.
Native Codex and OpenCode histories remain in their original locations.

Raw-log directories use local natural dates, followed by source names.
Review windows use the configured `day_start_hour` and can span two natural
dates. Timestamps determine inclusion in the window, not folder names alone.
Raw logs and published results have different purposes and separate roots.
This release does not automatically clean raw logs or run materials.

## A review run

1. `prepare` reads enabled sources within a time window. Adapters report
   usable rows and explicit gaps. Full messages become excerpts, while compact
   indexes help the Agent navigate them.
2. A run under `D/state/runs/` contains `manifest.json`, `context.json`,
   indexes, excerpts, drafts, and diagnostics. The context resolves the date,
   language, selected outputs, staging paths, and completion receipt format.
3. The Agent follows `tasks/daily-review/TASK.md`. Existing reports are copied
   into staging so the Agent can retain user additions when rerunning a date.
4. `finish` checks the receipt, prepared-entry coverage, required files,
   structured output, and conflicts with user edits made after preparation.
   Publication stops when these checks fail.
5. Valid drafts are published to stable dated paths and recorded in the
   completion history. File replacement is atomic per file, not across the
   entire set of outputs. Run diagnostics remain available on failure.
6. The same executing Agent performs a configured post-review task after publication,
   with its own context, permitted write directories, receipt, and validator.
   A failed operation phase remains pending and resumes without redoing the
   published daily reports. The task must make its operations idempotent.

`analyze` prepares one work ticket, while `due` prepares a bounded set of
closed-day tickets and skips completed reviews. Neither starts an Agent.
An external startup entry launches an Agent with `AUTOMATION.md`. That Agent
uses the common commands and performs review and post-review itself.
`finish` returns `actions-pending` when post-review work needs execution,
then validates its receipt on a later call. Only the outer startup module
contains Agent-specific process handling.
See [Scheduling](SCHEDULING.md) for external or Agent-native triggers.

The runner checks declared coverage and output structure. These checks do not
prove that an Agent's interpretation is correct. Reports must distinguish
recorded facts, assistant claims, inference, and unknown human attention.
Logs are historical data and cannot authorize commands or other actions.

## Extending the project

Use [Profiles](PROFILES.md) to bind personal references, output locations,
custom schemas, and scoped operations without editing standard task files.
Vim and screenshots have optional readers described in [Input sources](INPUT-SOURCES.md).
Add a collector, source adapter, analysis task, output contract, or launcher
at its existing boundary. User instructions in `C/local-tasks/` are not
discovered implicitly. Selected profile files can be executed according
to their declared phase and scope. See [EXTENDING.md](EXTENDING.md).
Human documentation may be translated, while Agent instructions and
structured field names remain shared across languages.
