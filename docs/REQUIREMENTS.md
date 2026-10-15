# Storage and collection requirements

[简体中文](zh-CN/REQUIREMENTS.md)

These are product requirements for collectors, source adapters and review
tasks. Read this before changing dates, paths or recorder dependencies.

## Natural dates belong to collection

- Record timestamps as actual system time with the UTC offset. Vim keeps
  its original local `YYYY-MM-DD HH:MM:SS` format as an exception. Its reader
  reports the local-timezone assumption. Other sources still require offsets.
- Name session directories using the local system date when recording starts,
  equivalent to `date +%F`: `daily/YYYY-MM-DD/<source>/`.
  The date belongs to the recording's creation, not each subsequent write.
  Calendar and logical-day changes never move or split an existing recording.
- The Python equivalent is local `strftime("%Y-%m-%d")`. Do not require a
  Unix `date` executable on Windows or macOS just to format a date.
- Recorders do not know the review's working-day boundary and never subtract
  hours to select a date. Bash and Vim use their session-start dates.
- Bash keeps exactly one JSONL per recorded shell process. Resolve its path,
  initial directory and natural date once when the recorder is enabled.
  Append to that file even if the shell stays open for months or changes cwd.
  Command completion timestamps do not select the storage directory.
- Screenshots are independent captures, each stored by its capture date.
- Vim keeps one session per editor process under the session's local start
  date, including when it ends after midnight. Existing files are snapshotted
  when opened. Diffs and `record.json` are generated at exit. Do not add
  midnight segments or timer, read/write, or focus checkpoints.
- Shared storage governs paths, date registration and deletion. It does not
  change a collector's capture behavior to make records available sooner.

## Preserve Bash recording behavior

Bash preserves history-input recording: full compound input, history-based
command start time, completion time, exit status and post-command cwd.
Write `session_start` immediately and `session_end` on normal exit.
Do not repeat session IDs, PIDs or session-start metadata on every command.
JSONL must not lose commands because of native duplicate rules, leading-space
filters, HISTIGNORE, zero history size or disabled history-file persistence.
Preserve the user's native history content and execution settings.
`set +o history` is an unresolved capture gap, explicitly documented in
[Bash](BASH.md), along with the accepted history-numbering limitation.

## Review windows belong to analysis

`config.json` may select `day_start_hour`, such as 4. This affects preparation
and interpretation only. It is absent from collector storage configuration.

For a review of 14 October 04:00 through 15 October 04:00, the analysis layer
selects records by their actual timestamps. Bash and Vim readers search all
retained date trees because a matching session may have started months earlier.
Screenshot readers select the capture dates intersecting the window.
The end is exclusive. One natural-date folder can supply multiple reviews.
Folder names alone do not establish the review's time window or the exact
time of an edit in an aggregate diff.
A long session's final diff cannot be split reliably into daily activity.
Until exit, its original snapshots exist but no `record.json` is available
to the reader. This limitation does not require live checkpoint recording.

Review material under `daily/DATE/_analysis/` uses the reviewed date label.
That label does not change the natural-date ownership of its input captures.
Formal reports remain in `memory` or explicitly selected permanent targets.

## Recorders work independently

- Installing the main application or preparing its configuration is optional
  for using the Bash collector or the independent Vim plugin.
- `C/raw-logs-path.txt` is the shared one-line UTF-8 absolute capture-root
  locator. Without it, recorders use the platform data directory's `daily`.
  Bash, Vim and the main application's daily storage use this same path.
  A present malformed locator is an error. Never silently choose another root.
- Bash and Vim do not read `storage.json` or maintain day registries.
  The main application uses `storage.json` for its permanent data root and
  maintains minimal date-registration metadata for analysis and managed writes.
  This does not impose that protocol on independent recorders.
- Vim selects its root once: `record_dir`, then the one-path UTF-8
  `C/raw-logs-path.txt`, then the platform data directory's `daily`. It does
  not register dates or vendor the shared runtime protocol. All selections
  use `YYYY-MM-DD/vim/<session>/` without old-layout or migration fallbacks.
- Collectors do not launch an analysis Agent or read its personal policies.

## Manual cleanup

Users remove inactive old natural-date directories directly. No status-file
inspection is required. Registered dates that are removed are not
automatically recreated. Permanent records and minimal system facts survive.

A review can depend on earlier Bash or Vim start-date folders as well as
capture folders within its window. A start-date folder remains active while
its shell or editor sessions are recording, even months after startup.
Use a retention period that leaves active capture and review dates intact.
No collector must introduce a review-specific calendar to implement cleanup.

See [Storage](STORAGE.md), [Cleanup](CLEANUP.md), and
[Input sources](INPUT-SOURCES.md) for the current interfaces.
