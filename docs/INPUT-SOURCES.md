# Input sources

English | [简体中文](zh-CN/INPUT-SOURCES.md)

Source adapters prepare factual evidence. The task and the Agent decide what
that evidence means. Adapters never execute commands found in histories.

The Vim and screenshot adapters are optional sources. Enable them explicitly
in the user configuration. An adapter reads the configured `path`, or the
shared daily directory when `path` is omitted. They do not install recorders or
start continuous collection.

## Bash session context

The Bash adapter reads dated `YYYY-MM-DD/bash/*.jsonl` files and explicitly
configured flat session roots. Activity rows always stay within the
review window. Each Bash process keeps one file under its start date for its
entire lifetime. The adapter searches every retained start-date folder, even
months before the review. The bundled recorder writes compact `session_start`,
`command` and `session_end` events. Startup time and directory appear once in
the start event. Files identify sessions without per-command session IDs.
For a command or session end whose start was recorded earlier,
the adapter attaches the nearest prior start as `session_context`, including
`outside_window: true`, the actual start timestamp, original start fields,
and its source location. This context is not another activity row.

Historical commands and other sessions' out-of-window commands are not copied into the
index. Command timestamps, directories, and recorded capture or timestamp
scope are preserved. A missing capture scope is explicitly marked as unknown
coverage. A modern command's `started_at` is not invented as a shell
session start. The bundled command cwd is observed before execution, and its
start time comes from history. See [Bash recording](BASH.md) for limitations.

## Vim sessions

The separately released [session-recorder.vim](https://github.com/functoreality/session-recorder.vim)
collector is installed through the user's editor plugin manager, with consent.
Follow [Vim/Neovim recording](VIM.md) for discovery, configuration and verification.


The shared layout is:

```text
daily/YYYY-MM-DD/vim/session/record.json
daily/YYYY-MM-DD/vim/session/<snapshot artifacts>
daily/YYYY-MM-DD/vim/session/<modification diff artifacts>
```

The date is the session's local start date. Each editor process keeps one
session, including across midnight. Existing files are snapshotted when
opened, and the final diff and `record.json` are written at exit. Shared
storage does not require midnight segments or periodic or event-driven
checkpoints.

Vim roots have one supported layout: `<root>/YYYY-MM-DD/vim/<session>/record.json`.
Preparation searches all retained date folders before filtering actual intervals.
The plugin selects its root once using `record_dir`, the one-path TXT locator,
or the platform default. Set `sources.vim.path` to that same root when needed.
Old flat session roots, `root/vim` and automatic root-search fallbacks are not
supported. Removed day-segment fields do not change whole-session semantics.

Each manifest needs `vim_start`. Historical open-session manifests may omit
`vim_close`.
The reader accepts local `YYYY-MM-DD HH:MM:SS` timestamps and ISO 8601
timestamps with a timezone offset. The plugin keeps its original local time
format. Timestamps without an offset use the machine's local timezone, and
the adapter reports this assumption because daylight-saving transitions and
migration between timezones can make it ambiguous.

The adapter accepts the session recorder's version 1 contract and unversioned
legacy records. Unsupported `schema_version` values are excluded with a gap.
Version 1 records use `source: vim`, a 32-character hexadecimal `session_id`,
and per-file IDs, paths, open timestamps, and snapshot/comparison status.
Malformed fields and failed snapshots or comparisons produce explicit gaps.

The index preserves the complete manifest in `record_metadata`, including
unknown fields, execution flags, focus lines, and identifiers. `files` keeps
each opened-file object's original fields and adds a basename and modification
flag. `record_sha256` identifies the original manifest. `artifacts`,
`diff_paths`, and `snapshot_paths` locate the session's recorder artifacts
without reading their contents or the live edited files.

For version 1, `original_file` and `diff_file` identify sibling artifacts.
The adapter adds `original_artifact` and `diff_artifact` references to each
file when applicable, including missing or invalid-reference status.
An unchanged file can have a successful comparison without a diff artifact.
Missing change counts after a failed comparison mean an unknown modification
state, represented by `modified: null`, rather than zero changes.

`last_focus_line` can contain unsaved text from the live editor buffer.
Its content is not proof that the file was saved. `executed: true` records a
user mapping's claim, not independent proof of command execution or success.

`timestamp` is the first instant of overlap with the review window, so a
cross-window session can be found in the normal evidence timeline.
`actual_session_start` and `actual_session_end` retain its real interval.
A whole-session diff cannot establish when each edit happened inside a
clipped interval. `diff_scope` states that limitation explicitly.

A completed record whose close time is after the snapshot end is excluded
because its final diff can contain later changes. This is recorded as a
limitation in the source gaps. A historical open session keeps its available
manifest metadata with `session_status: open` and `diff_status: incomplete_session`.
The adapter does not claim that an open session has a complete final diff.

Both shared and standalone recording write their final manifest at editor
exit. Original snapshots already exist while files are open, but an ongoing
or failed session with no `record.json` is invisible to the adapter. This
limitation does not require live checkpoints. A recognized, readable Vim
subtree with no matching records returns an empty successful index. This means only
that no records were found, not that collection is active or complete.
A shared daily directory with no Vim subtree returns `unavailable`, as does a missing
source root or a source containing only unsupported or unreadable records.
Mixed valid and damaged records return `partial`. A record closing after the
snapshot produces a limitation without making the source unavailable.

## Screenshot frames

The shared layout is:

```text
daily/YYYY-MM-DD/screenshots/capture.png
daily/YYYY-MM-DD/screenshots/manifest.json
```

JPEG, PNG, and WebP images are supported. Shared storage uses only
`YYYY-MM-DD/screenshots/`. An explicitly configured screenshot source can
also contain flat image files. The adapter does not search unrelated source
directories for images.

Without a manifest, a frame's filesystem modification time is its capture
timestamp. Preserve modification times when importing old files. A JSON
manifest can be a list of frame objects or an object containing `frames`.
`manifest.jsonl` can contain one frame object per line. Each object uses `path`
or `filename`, resolved inside that screenshot directory, and `timestamp` or
`captured_at` with an ISO 8601 offset. For example:

```json
{
  "frames": [
    {
      "filename": "capture.png",
      "captured_at": "2026-06-20T10:15:00+08:00",
      "display": "main"
    }
  ]
}
```

A valid manifest capture time takes precedence over modification time.
`capture_metadata` preserves the complete frame object. An invalid capture
time falls back to modification time and produces a source gap. Directory
dates are organizational labels, not substitutes for a capture timestamp.

Each indexed frame includes its source path, SHA-256, dimensions, capture
time, modification time, and timestamp semantics. The historical
`perceptual_hash` field uses a 16 by 16 grayscale average hash, identified by
`hash_algorithm: average_hash_16x16`. Consecutive hashes differing by more
than 16 bits start a new `segment`. `representative` marks a segment's first
frame, while all frames remain in the index and contact sheets.

`previous_capture_timestamp` and `seconds_since_previous_capture` describe
the observed sampling intervals. They do not establish attention, inactivity,
or work duration. Any rule assigning a preceding work interval to a screenshot
belongs in a user's analysis profile.

Pillow is an optional dependency needed for screenshot indexing and image
conversion. If it is absent, this source is `unavailable` with an explicit
gap. Other sources can still be prepared. Corrupt individual images produce
gaps while readable frames remain available.

## Replay assets

`screenshots.prepare_assets(rows, run_target)` runs after the runner assigns
every frame its `evidence_id`. `run_target` is the source directory inside a
run. The function returns metadata stored in that source's `assets` field.

Assets consist of JPEG contact sheets and matching JSON cell maps. Every
indexed frame receives a cell, including frames similar to their neighbors.
Each complete frame is scaled down to fit a 640 by 352 image area, preserving
its aspect ratio without cropping or upscaling. Six frames fit on a sheet.

Cell maps preserve evidence ID, source path, timestamp, SHA-256, segment,
original dimensions, rendered dimensions, image box, and conversion status.
The function verifies the source SHA-256 before conversion. Changed or missing
frames keep their cell mapping with an explicit failure status. `coverage`
reports indexed, mapped, and successfully converted frame counts. Asset paths
are relative to the source directory inside the run.
