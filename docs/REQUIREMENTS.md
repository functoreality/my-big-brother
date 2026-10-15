# Storage and collection requirements

[简体中文](zh-CN/REQUIREMENTS.md)

These are product requirements for collectors, source adapters and review
tasks. Read this before changing dates, paths or recorder dependencies.

## Natural dates belong to collection

- Record timestamps as actual system time with the UTC offset.
- Name capture directories using the local system date, equivalent to
  `date +%F`: `daily/YYYY-MM-DD/<source>/`.
- The Python equivalent is local `strftime("%Y-%m-%d")`. Do not require a
  Unix `date` executable on Windows or macOS just to format a date.
- Recorders do not know the review's working-day boundary. They never
  subtract hours or put a 02:30 event under the previous date.
- Bash uses the command completion date. Vim's existing checkpoints use
  natural-date segments, rotating at midnight. Original timestamps stay real.

## Review windows belong to analysis

`config.json` may select `day_start_hour`, such as 4. This affects preparation
and interpretation only. It is absent from collector storage configuration.

For a review of 14 October 04:00 through 15 October 04:00, the analysis layer
reads captures from both `daily/2026-10-14/` and `daily/2026-10-15/`, selecting
records by their actual timestamps. The end is exclusive. One natural-date
folder can supply two adjacent reviews. Folder names alone do not establish
the review's time window or the exact time of an edit in an aggregate diff.

Review material under `daily/DATE/_analysis/` uses the reviewed date label.
That label does not change the natural-date ownership of its input captures.
Formal reports remain in `memory` or explicitly selected permanent targets.

## Recorders work independently

- Installing the main application or preparing its configuration is optional
  for using the Bash collector or the independent Vim plugin.
- A missing `C/storage.json` selects platform-default data storage.
- An optional shared file selects a custom `data_root` and layout version.
  It contains no review settings. A present malformed file reports an error.
- Runtime date-registration metadata is created automatically. It is separate
  from optional user configuration and preserves deletion decisions.
- Vim's explicit `record_dir` supports standalone session output for other
  tools. It does not require shared configuration or the main application.
- Collectors do not launch an analysis Agent or read its personal policies.

## Manual cleanup

Users remove inactive old natural-date directories directly. No status-file
inspection is required. Registered dates that are removed are not
automatically recreated. Permanent records and minimal system facts survive.

A review spanning two natural dates can depend on both capture folders.
Use a retention period that leaves active capture and review dates intact.
No collector must introduce a review-specific calendar to implement cleanup.

See [Storage](STORAGE.md), [Cleanup](CLEANUP.md), and
[Input sources](INPUT-SOURCES.md) for the current interfaces.
