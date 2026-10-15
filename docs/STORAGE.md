# Storage v2

[简体中文](zh-CN/STORAGE.md)

The personal data root has two areas. It is separate from the source checkout
and from the platform-discovered configuration directory C.

```text
data-root/
  daily/
    YYYY-MM-DD/
      bash/
      vim/
      screenshots/
      _analysis/<run-id>/
      _launches/<invocation-id>/
      scheduler.log
  memory/
    USER-MODEL.md
    MACHINE-CONTEXT.md
    records/YYYY-MM-DD/
      worklog.md
      time-use.md
      time-use.json
      insights.md
      time-estimates.json
    _system/
      identity.json
      days/YYYY-MM-DD.json
      operations/
      locks/
```

Only selected outputs and used source directories are created. A personal
profile may keep published files in existing external locations.
Knowledge outputs remain optional. Profile instructions are configuration,
not accumulated user knowledge, and stay under C.

## Main application and independent recorders

```sh
python -m my_big_brother init --sources bash --day-start-hour 4
python -m my_big_brother paths
```

`--data-root /absolute/path` selects the whole data root on first installation.
`--results-root` may select a separate permanent output root. It cannot overlap
disposable daily storage. Atomic publication keeps its temporary copy inside
the dated run, so formal outputs and `daily` must share a filesystem.
Cross-filesystem publication stops before replacing any output.

Main application initialization writes optional collector configuration
`C/storage.json` with `schema_version: 2` and `data_root`. Review settings,
including `day_start_hour`, belong only to `C/config.json`.

Recorders also work without the main application or either user configuration
file. They use platform defaults when `C/storage.json` is missing and create
runtime metadata automatically. An optional valid shared configuration selects
a different data root. A malformed existing file or damaged runtime registry
is an error. Runtime `memory/_system/identity.json` records storage identity,
not a review calendar. No collector writes a user configuration file.

Default C and D discovery is documented in [INSTALLATION.md](../INSTALLATION.md).
Changing an existing data root in place is unsupported.
See the product [Requirements](REQUIREMENTS.md) before changing this contract.

## Natural capture dates and analysis windows

Capture dates use local calendar dates, equivalent to `date +%F`.
At 15 October 02:30, Bash writes into `daily/2026-10-15/bash/`, including when
the review boundary is 04:00. Original timestamps are never shifted.
Screenshots use their capture date. Vim uses the session's local start date
for its entire lifetime, including exit after midnight. One editor process
produces one session, with original snapshots at file open and diff/JSON at
exit. There is no midnight rotation or periodic or event-driven checkpoint.
Shared storage governs paths and lifecycle without changing capture behavior.

Only analysis interprets a working day. A review from 14 October 04:00 to
15 October 04:00 reads event records from both natural-date folders. Vim
readers search all retained date trees and select sessions by actual time
overlap, including sessions that started before either date. Whole-session
diffs cannot establish which edits belong to each day. Before exit, original
snapshots exist but there is no final `record.json` to index.
A natural date can contribute to multiple reviews. Analysis
material remains under the reviewed date's `_analysis/` directory. Native
Agent histories stay with their applications.

You can delete inactive old date directories directly, including failed runs.
No status-file inspection is required. This abandons automatic recovery.
See [Manual cleanup](CLEANUP.md).

Every writer registers a day before creating it. Missing registered workspaces
are marked discarded in small durable per-day records. Review, collection and
import must not recreate them. The completion fact and workspace disposition
are separate. Deleting a completed day's inputs does not erase its reports.
Configuration changes do not override the discard decision.

For a deliberate user-requested restoration:

```sh
python -m my_big_brother analyze --date 2026-10-14 --recreate-deleted
```

This prepares a new review generation. It does not launch an Agent, recover
deleted evidence or authorize unrelated operations. Automatic tasks must never
add this option themselves. Ordinary `--date` does not restore deleted dates.

## Collector and extension contract

The canonical standard-library implementation is `my_big_brother/storage.py`.
The Bash collector and independent Vim plugin vendor the same protocol so
the plugin can still run without installing the main package. First writers
coordinate using shared persistent locks. No collector needs a second user
copy of the root in shell/editor settings. No analysis calendar is shared.

For an already configured capture program, `capture-path --source screenshots`
returns a registered destination. `record-screenshot --image /absolute/image.jpg`
stores an existing image and records its capture timestamp. Both accept
`--timestamp` with an explicit UTC offset and return `discarded` for a removed
day. Neither command takes screenshots or starts periodic capture.

Write reasoning, excerpts, scripts, validation scratch space, full receipts
and backups of proposed changes inside the selected day's analysis directory.
Post-review tasks receive `operation_state_dir` for minimal durable operation
facts. Record stable identities before side effects, including effects whose
outcome is uncertain after a crash. Do not put raw content or full logs there.
Removing a day stops remaining work and does not undo already applied changes.
Custom extensions need their own verifiable idempotence and must honor discard.

Startup still launches one Agent. It allocates dated logs without planning
review work. A discarded target day uses the current natural date for startup
logs. If no legal directory or valid registry is available, return stderr and
a failure status without creating fallback cache roots.
