# Storage v2

[简体中文](zh-CN/STORAGE.md)

The personal data root has two areas. It is separate from the source checkout
and from the platform-discovered configuration directory C.

`raw-logs` contains disposable review material: captures, preprocessing results,
indexes, screenshot sheets, Agent drafts and execution logs. It can include
AI-generated material. The boundary is whether material belongs to a dated
working area or is published for long-term retention, not whether AI has read
or generated it. Keep published reports and accumulated knowledge in `memory`
or explicitly configured permanent destinations.

The `paths` command reports the disposable root as `raw_logs`.

```text
data-root/
  raw-logs/
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
disposable raw-log storage. Atomic publication keeps its temporary copy inside
the dated run, so formal outputs and `raw-logs` must share a filesystem.
Cross-filesystem publication stops before replacing any output.

`C/raw-logs-path.txt` is the shared capture-root locator. It contains one
UTF-8 absolute path, normally D/raw-logs, with an optional final LF or CRLF.
Do not quote it, add comments or expand variables when reading it. Preserve
spaces. A missing locator uses the platform default. A malformed existing
locator reports an error. Bash, Vim and the main application's capture and
analysis directories use this path. Explicit source-path overrides remain
available for intentionally separate sources.

Initialization writes the resolved path to the TXT unless one already exists.
It also writes `C/storage.json` with `schema_version: 2` and `data_root` for the
main application's permanent `memory` and system identity. Recorders do not
need this JSON. Review settings, including `day_start_hour`, remain in
`C/config.json`. Moving the capture root does not move permanent outputs or
system facts. Keep capture storage outside permanent memory and results.

The Bash collector works without installing or initializing the application.
It reads the TXT once and otherwise uses platform defaults. It does not read
`storage.json`, register dates or create user configuration. It creates one
session file and stops appending if that file or its parent is removed.

The independent Vim plugin uses a smaller path contract: `record_dir`, then
`C/raw-logs-path.txt` containing only an absolute capture-root path, then the
platform data directory's `raw-logs`. It reads that choice once at startup.
It does not load `storage.json`, vendor the storage protocol or maintain a day
registry. Its final diff and JSON use the saved session folder at exit.

Default C and D discovery is documented in [INSTALLATION.md](../INSTALLATION.md).
Changing an existing data root in place is unsupported.
See the product [Requirements](REQUIREMENTS.md) before changing this contract.

## Natural capture dates and analysis windows

Capture ownership uses the recording's local creation date, equivalent to
`date +%F` at startup. Bash creates one JSONL under its start date and appends
there for the shell's entire lifetime. A shell started on 14 October still
writes into `raw-logs/2026-10-14/bash/` on 15 October or months later.
No midnight or logical-day boundary changes an existing recording's path.
Original event timestamps are never shifted. Screenshots are independent
captures and use their capture date. Vim uses the session's local start date
for its entire lifetime, including exit after midnight. One editor process
produces one session, with original snapshots at file open and diff/JSON at
exit. There is no midnight rotation or periodic or event-driven checkpoint.
Shared storage governs paths and lifecycle without changing capture behavior.

Only analysis interprets a working day. A review from 14 October 04:00 to
15 October 04:00 finds Bash and Vim sessions across all retained start-date
folders. Bash selects events by actual time, and Vim selects sessions by time
overlap, including sessions that started before either date. Whole-session
diffs cannot establish which edits belong to each day. Before exit, original
snapshots exist but there is no final `record.json` to index.
A natural date can contribute to multiple reviews. Analysis
material remains under the reviewed date's `_analysis/` directory. Native
Agent histories stay with their applications.

You can delete inactive old date directories directly, including failed runs.
No status-file inspection is required. This abandons automatic recovery.
See [Manual cleanup](CLEANUP.md).

Writers using the shared runtime protocol register a day before creating it. Missing registered workspaces
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

The managed application protocol is `my_big_brother/storage.py`. Its writers
coordinate using persistent locks. Independent Bash and Vim recorders use only
the one-path locator and do not register or check date dispositions. Removed
active Bash files or Vim session folders are not recreated by those sessions.
A new recorder session uses its own current start date. No analysis calendar
is shared. Bash carries only the small platform/locator helper, whose canonical
copy is `my_big_brother/collector_paths.py`.

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
