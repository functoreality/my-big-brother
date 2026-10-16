# Architecture

[English](ARCHITECTURE.md) | [简体中文](zh-CN/ARCHITECTURE.md)

Date and recorder requirements: [Requirements](REQUIREMENTS.md).

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
  paths.py          Platform paths and the shared storage contract
  runner.py         Prepare, validate, publish, and track completion
  automation.py     Plan and verify invocations when called by the Agent
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
the actual executable. It starts exactly one Agent and carries execution
settings and logs. Date planning, imports and business checks belong
to that Agent. Common review and automation commands never start an Agent.

## Personal storage

Installation files are separate from configuration and personal records.
Platform defaults for configuration directory C and data directory D are
listed in [INSTALLATION.md](../INSTALLATION.md).

```text
C/
  config.json
  raw-logs-path.txt  Optional one-path raw-log locator
  local-tasks/
D/
  raw-logs/YYYY-MM-DD/
    bash/
    vim/
    screenshots/
    review.json
    _analysis/<run-id>/
      publication.json
      actions/
    _launches/<invocation-id>/
  memory/
    USER-MODEL.md
    MACHINE-CONTEXT.md
    records/YYYY-MM-DD/
```

Collectors use the system calendar date at creation, equivalent to `date +%F`.
An existing recording keeps its creation-date location. Bash and Vim sessions
never rotate at midnight. Their readers search all retained start-date folders.
`C/raw-logs-path.txt` selects raw-log storage, and `results_root` selects
permanent outputs, defaulting to D/memory. Neither requires `storage.json`.
All dated completion, publication and action state stays in `raw-logs/DATE`.
Each inactive old date directory is disposable without inspecting status.
Formal selected outputs and knowledge remain in memory or profile-selected
permanent targets. One fixed-size `raw-logs/.publish.lock` coordinates shared
publication without keeping date history. See [Storage](STORAGE.md).

## A review run

1. `prepare` reads enabled sources within a time window. Adapters report
   usable rows and explicit gaps. Full messages become excerpts, while compact
   indexes help the Agent navigate them.
2. A run under `D/raw-logs/DATE/_analysis/` contains `manifest.json`, `context.json`,
   indexes, excerpts, drafts, and diagnostics. The context resolves the date,
   language, selected outputs, staging paths, and completion receipt format.
3. The Agent follows `tasks/daily-review/TASK.md`. Existing reports are copied
   into staging so the Agent can retain user additions when rerunning a date.
4. `finish` checks the receipt, prepared-entry coverage, required files,
   structured output, and conflicts with user edits made after preparation.
   Publication stops when these checks fail.
5. Valid drafts are published to stable dated paths and recorded in the
   dated `review.json`. File replacement is atomic per file, not across the
   entire set of outputs. Run diagnostics remain available on failure.
6. The same executing Agent performs a configured post-review task after publication,
   with its own context, permitted write directories, receipt, and validator.
   A failed operation phase remains pending and resumes without redoing the
   published daily reports. The task must make its operations idempotent.

`analyze` prepares one work ticket. `plan-due` and `due` consider only the latest
closed logical day. `due` skips retained completed reviews. None starts an Agent.
Older dates require explicit user-requested `--date` reruns. There is no
automatic historical queue or missed-day catch-up.
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
