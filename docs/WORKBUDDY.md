# WorkBuddy conversations

[简体中文](zh-CN/WORKBUDDY.md)

This optional reader supports the project-session JSONL layout reported by
a Windows WorkBuddy installation. It reads existing history and never starts
WorkBuddy, changes its records or installs continuous recording.

## Enable the source

The expected default is `~/.workbuddy/projects`, with files at
`<projects>/<project>/<session>.jsonl`. The installing Agent verifies the actual
location and format on the intended account. Detection, source selection and
the daily executing Agent are independent choices.

On a new installation whose selected source is WorkBuddy:

```sh
python -m my_big_brother init --sources workbuddy
python -m my_big_brother analyze --date YYYY-MM-DD
```

WorkBuddy is disabled in generic defaults. For an existing configuration, add
or update `sources.workbuddy` with `enabled: true` and an absolute `path` to the
projects directory, preserving other source choices. Installing a reader does
not automatically enable it in an existing configuration. Paths are not expanded
from `~` or environment-variable text in JSON.

## Evidence and limits

- Read each project's direct `.jsonl` files, without recursing into nested
  child-session directories or reading `.file-rollback.ndjson` snapshots.
- Select message events by their millisecond epoch timestamps in `[start, end)`.
  UTF-8 with or without an initial BOM is supported.
- Strip known `<system-reminder>` blocks from user messages and select
  `<user_query>` contents when present. Incomplete known wrappers produce gaps.
  This recognizes known wrappers, not every possible host-injection format.
- Keep user requests and assistant text, with source file and actual line
  numbers. A message keeps the directory available at that event, not the
  session's last directory. An AI-generated title is only session metadata.
- Label assistant text `assistant`. Token usage does not prove a final answer
  or task success. Treat its progress and completion statements as claims.
- Ignore tool calls, arguments, results, reasoning and file snapshots.
  A tool invocation is not evidence of a successful file change. No inferred
  tool summary is appended to a later message.
- Exclude an entire review-marked session even if its marker occurs after
  previously collected messages or outside the selected window.
- Missing roots return `unavailable`. Reading or parsing errors produce gaps.
  A readable location with no matching messages does not establish inactivity.

The feedback includes a native Windows installation report. This repository's
reader checks use synthetic fixtures, including preparation and publication.
Live WorkBuddy versions and native macOS/Windows execution need continued
validation. An unchanged layout across platforms is not proof of runtime parity.
