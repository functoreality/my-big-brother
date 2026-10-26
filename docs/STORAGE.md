# Storage

[简体中文](zh-CN/STORAGE.md)

Personal storage is separate from the source checkout and the platform
configuration directory C. `raw-logs` contains disposable dated working areas.
`memory` or explicitly configured permanent destinations retain only selected
formal reports and accumulated knowledge.

The `paths` command reports the disposable root as `raw_logs`.

```text
data-root/
  raw-logs/
    .publish.lock
    YYYY-MM-DD/
      bash/
      vim/
      screenshots/
      review.json
      _analysis/<run-id>/
        publication.json
        notifications/
        actions/
      _launches/<invocation-id>/
      scheduler.log
  memory/
    inbox/DATE--STABLE-ID.md
    USER-MODEL.md
    MACHINE-CONTEXT.md
    records/YYYY-MM-DD/
      worklog.md
      time-use.md
      time-use.json
      insights.md
      time-estimates.json
```

Only selected outputs and used directories are created. New installations
select all six output types, including knowledge, and users can disable each.
A personal profile may publish to existing external locations.
Profile instructions are configuration and stay under C.
The local reminder inbox defaults to `results_root/inbox/` and can be redirected
with `notifications.inbox`. It is permanent output, outside raw logs.
See [Local reminders](NOTIFICATIONS.md).
All completion markers, publication journals, action journals, receipts and
execution logs belong to `raw-logs/DATE` and disappear with that directory.
There is no permanent daily ledger or system-state directory in `memory`.
The sole technical exception outside date directories is fixed-size
`raw-logs/.publish.lock`, used to serialize publication of shared outputs.
It contains no date history and does not grow with reviews.

Personal source code and synthetic tests can live in `C/readers/<source>/`,
selected explicitly in `config.json`. These are configuration, not disposable
dated material. Source upgrades preserve them. Reader identity digests stay
inside dated run context, without a permanent registry.

## Paths and initialization

```sh
python -m my_big_brother init --sources bash --day-start-hour 4
python -m my_big_brother paths
```

`C/raw-logs-path.txt` is the shared raw-log root locator. It contains one
UTF-8 absolute path, normally D/raw-logs, with an optional final LF or CRLF.
Do not quote it, add comments or expand variables when reading it. Preserve
spaces. A missing locator uses the platform default. A malformed existing
locator reports an error. Bash, Vim and the main application use this locator.
Explicit source-path overrides remain available for intentionally separate sources.

Initialization creates ordinary configuration and needed directories. Default
paths work without a TXT file. The `--data-root` shortcut writes the TXT when
it is absent and preserves an existing locator. Neither the application nor
the independent recorders require `storage.json` or a storage
identity. Review settings, including `day_start_hour`, remain in `C/config.json`.
`results_root` selects permanent outputs and defaults to D/memory.

On first installation, `--data-root /absolute/path` is a convenience that selects
that path's `raw-logs` and `memory` through the locator and `results_root`.
It does not create a separate persistent data-root setting. Existing settings
are preserved. `--results-root` can select a separate permanent output root.
It cannot overlap raw-log storage. Formal outputs may use another filesystem
or mount, provided the executing Agent has permission to write there.
Changing the capture locator does not move existing outputs.
Platform C and D defaults are in [INSTALLATION.md](../INSTALLATION.md).

## Publication and interrupted writes

`finish` validates the staged outputs and checks destination digests before
writing reports. A publication lock serializes cooperating publishers.
Validated drafts are read and written directly to their formal destinations,
without an additional temporary publication copy or cross-directory rename.
Existing POSIX file modes are preserved. New files default to `0600` unless
the profile explicitly selects another mode.

Publication is not atomic, either per file or across the output set.
A reader may briefly see incomplete content. An interrupted write can leave an
empty or partial destination, while the complete draft remains in
`raw-logs/DATE/_analysis/RUN/drafts/`. There is no automatic rollback or extra
backup of the previous formal content.

`publication.json` in that run records completed file writes. Retry `finish`
with the same run if remaining targets still match their prepared originals
or complete drafts. A partial write or newer human edit causes a digest conflict
and stops publication. Inspect the affected target before manually restoring
its intact draft or merging edits. Use `context.json`'s `output_mapping` to
match each `staged` path to its `final` destination. After restoring the exact
draft, retry `finish`. If you merge different content, prepare a new review.
Do not discard newer edits or remove the dated recovery material prematurely.

## Natural capture dates and analysis windows

Capture ownership uses the recording's local creation date, equivalent to
`date +%F` at startup. Bash creates one JSONL under its start date and appends
there for the shell's entire lifetime. A shell started on 14 October still
writes into `raw-logs/2026-10-14/bash/` on 15 October or months later.
No midnight or logical-day boundary changes an existing recording's path.
Original event timestamps are never shifted. Screenshots are independent
captures and use their own capture date.

Vim selects its root once: `record_dir`, then `C/raw-logs-path.txt`, then the
platform data directory's `raw-logs`. One editor process produces one session
under its local start date, including exit after midnight. It snapshots existing
files when opened and publishes diff/JSON at exit. There is no midnight rotation
or periodic or event-driven checkpoint. Bash and Vim require no application
initialization. Existing sessions do not recreate removed files or session
folders. A new session uses its own current start date.

Only analysis interprets a working day. A review from 14 October 04:00 to
15 October 04:00 finds Bash and Vim sessions across all retained start-date
folders. Bash selects events by actual time, and Vim selects sessions by overlap,
including sessions that started before either date. Whole-session diffs cannot
establish which edits belong to each day. Before exit, original snapshots exist
but there is no final `record.json` to index. One natural date may contribute
to multiple reviews. Analysis material remains under the reviewed date's
`_analysis/` directory. Native Agent histories stay with their applications.

## Retention and reruns

Delete inactive old date directories directly, including failed runs. No
status-file inspection is required. Deletion removes their evidence, completion
markers and recovery journals together. Published reports, knowledge and
already applied changes remain. Do not delete a date still used by a running
shell, editor or review. See [Manual cleanup](CLEANUP.md).

Unattended review considers only the latest closed logical day. It does not
queue older dates, scan historical gaps or automatically catch up after downtime.
To rerun an older date, request it explicitly:

```sh
python -m my_big_brother analyze --date 2026-10-14
```

An explicit date may create its dated workspace. It cannot recover deleted
evidence. With no retained completion marker, that date has no remembered
runtime status. Selected formal outputs can still be copied into staging so
manual additions can be preserved during review.

## Collector and extension contract

Collectors and capture helpers write plain natural-date paths. No date
registration is required. Bash carries only the small platform/locator helper,
whose canonical copy is `my_big_brother/collector_paths.py`. Bash, Vim and
screenshots use date/source trees beneath their source root, including with
explicit paths. Do not add flat-layout discovery or migration fallbacks.

For an already configured capture program, `capture-path --source screenshots`
returns a destination. `record-screenshot --image /absolute/image.jpg` stores an
existing image and records its capture timestamp. Both accept `--timestamp`
with an explicit UTC offset. Neither takes screenshots or starts periodic capture.

Keep reasoning, excerpts, scripts, validation scratch space, full receipts,
action journals and candidate backups inside the selected day's analysis run.
Before side effects, record stable operation identities and uncertain outcomes
in the action directory. Retrying a retained run must inspect those journals
and verify idempotence. After deletion, no hidden operation history remains.
Extensions must verify external effects before explicitly requested reruns.

Startup launches one Agent. Logs use the explicitly requested date, or the
previous calendar date by default, independently of logical-day analysis.
All launch diagnostics are disposable. If log allocation fails, return stderr
and failure without creating fallback cache roots.
