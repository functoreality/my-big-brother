# Extending My Big Brother

English | [简体中文](zh-CN/EXTENDING.md)

The core prepares evidence and manages a review. An Agent reads the Markdown
task and leads analysis. Keep new features on the relevant side of this
boundary rather than turning each semantic step into a program workflow.

## Four independent extension points

| Component | Responsibility | Example |
| --- | --- | --- |
| Collector | Record activity in a host application | Bash hook or a future editor plugin |
| Source adapter | Read records and prepare indexed evidence | Codex JSONL or OpenCode SQLite |
| Analysis task | Explain interpretation and desired results | Daily review or a future weekly review |
| Analyzer launcher | Start one unattended Agent | Codex CLI or a future additional backend |

Codex as an input and Codex as a launcher are independent integrations.
A user can add an input without changing the selected analyzer.
A heavyweight editor plugin can be released in a separate repository, while
this repository maintains its source adapter and integration instructions.

## Add an input

### Personal readers outside the checkout

Keep personal code in `C/readers/<source>/reader.py`, with synthetic tests and
necessary notes alongside it. `C` is the configuration directory reported by
`python -m my_big_brother paths`. Source upgrades preserve these files.
Edit the existing `sources` object in `C/config.json` to add a binding such as:

```json
"some_agent": {
  "enabled": true,
  "path": "/absolute/history/store",
  "reader": "/absolute/config/readers/some-agent/reader.py"
}
```

This is a source entry, not a replacement for the complete configuration.
Source names match `[a-z][a-z0-9_-]*`. `path` selects data, while `reader`
selects executable Python. Enabled personal readers require both absolute paths.
`required` remains an optional boolean. `init --sources` lists builtins only.
For a personal-only setup, run `init`, then replace its generated source selection
with your explicit personal entry before analyzing. Existing omitted sources
are not merged back in. No builtin registration or checkout edit is required.

An explicit `reader` always wins over the same-name builtin, including a builtin
added by a later upgrade. A missing or broken reader reports `unavailable`,
with the normal source gap/blocking rules. It never silently falls back.
`doctor` checks path existence without executing the reader. The preparer alone
loads explicitly selected code, which runs with the Python process's permissions.
There is no directory scanning, automatic dependency installation or plugin market.

The selected file must implement the same interface as builtin readers:

```python
from datetime import datetime
from pathlib import Path
from my_big_brother.sources import SourceResult


def collect(path: Path, start: datetime, end: datetime) -> SourceResult:
    ...
```

Use a self-contained file with absolute imports. The runtime does not add its
folder to Python's import search path. Optional
`prepare_assets(rows, directory)` uses the existing asset-preparation interface.
Preparation records the selected path and SHA-256 in the dated manifest and
context. Changing the file invalidates completion reuse and publication of
prepared runs. Prepare again after editing it. Indirect dependencies are not
fingerprinted. Loading does not create bytecode caches in the reader directory.
Local code may need maintenance if the public interface changes.

When official support becomes available, keep the current binding until the
user agrees to switch. Compare the same window read-only, including timestamps,
roles, content, gaps, personal filters and review-session exclusion. Explain
semantic differences rather than judging by row counts alone. With consent,
remove only `reader`, retaining the existing data path, enabled/required flags
and other settings. Keep the old code for rollback. Never read both versions
as separate enabled sources for the same store.

### Interface and contributing upstream

For an upstream contribution, create a module in `my_big_brother/sources/`
on a development branch, implementing:

```python
def collect(path: Path, start: datetime, end: datetime) -> SourceResult:
    ...
```

`SourceResult` carries `rows`, `status`, and `gaps`. Use `ok`, `partial`, or
`unavailable`, and return rows sorted by timestamp inside `[start, end)`.
Rows are JSON-serializable dictionaries with an ISO timestamp with offset and
retain source-specific fields.
Conversation records include their role and content. The common preparer
separates readable excerpts from compact indexes.

Register the adapter in the source selection code and add its configuration,
task input rules, and synthetic format tests. The current registration is
explicit. Personal readers use the file binding above instead of this registry.
There is no universal activity schema. Document supported versions and represent
parsing failures as coverage gaps. Test synthetic fixtures and, with permission,
verify a known real session's meaning and review-session exclusion read-only.
Keep historical content as evidence, not instructions. Offer an upstream patch
only with consent and without private histories or machine-specific bindings.

Read upstream histories without changing them. Independent collectors use
`C/raw-logs-path.txt` or the platform default, then write
`raw-logs/YYYY-MM-DD/<source>/`. They do not require `storage.json`, runtime
registration or `results_root`. Keep their path selection simple. Bash, Vim
and screenshot source roots must contain the date/source structure, even
when explicitly configured. Do not add old-layout discovery or migration.

Application helpers, such as `capture-path` and `record-screenshot`,
write plain natural-date paths without a registry or permanent runtime state.
See [Storage](STORAGE.md).

Choose a recording's date and path when it begins, then keep that location.
Do not rotate a Bash or editor session at midnight or a review boundary.
Readers must find relevant events in older start-date folders. An independent
new screenshot uses its own capture date, not a daemon's original start date.

## Add an output

Extend the daily task's output contract for results based on the same day's
shared evidence, timeline, and task map. Add the output name, stable paths,
and any necessary validation in the core. Reuse the shared interpretation
instead of starting an independent full analysis per output.

Structured output needs a documented schema and meaningful validation.
Human-readable output needs clear content boundaries and rerun behavior.
Define how user edits are retained and prevent duplicates across reruns.

A task with a different purpose or time range can have its own task directory.
A future weekly review will usually read published daily records rather than
reprocessing a week's raw conversations.

## Add an Agent startup entry

The startup boundary alone knows the Agent's executable, authentication,
sandbox and timeout. Start it once with the shared
[automation task](../tasks/daily-review/AUTOMATION.md), the installation,
Python, optional explicit date and permitted paths. The Agent calls common preparation,
publication and receipt checks itself, including configured post-review.
Do not introduce Agent calls into `runner.py`, input adapters, validators,
or the shared CLI. A native scheduled Agent can use the same task without
any additional launcher.

The installing Agent can write a local entry using its installed execution
interface. Read installed help or official documentation when needed.
The bundled example is `python -m my_big_brother.analyzers.codex`.
A new entry can live outside the checkout or be contributed under `analyzers/`.
The Codex entry derives write roots from raw logs, results and the selected
profile's destinations. A local entry can add an explicitly authorized root
with `--write-dir /absolute/directory`. Covered child roots are omitted before
launch, without changing the combined permission scope. The entry never grants
an unselected common parent merely to shorten the list. Task output bindings
and post-review operation scopes remain separate from these filesystem grants.

The entry only starts one Agent and carries necessary execution settings and
logs. It must not plan review dates, prepare inputs, publish results,
or verify business completion. The executing Agent calls `begin-automation`
and `complete-automation` when using a launch context, and checks actual
completion against common run state. In exec mode the bundled entry returns
`agent-exited`. Its optional tmux mode returns `session-started` with an attach
command for the same interactive TUI. Neither status means checked completion.
The Agent writes the checked `automation-result.json`.
Do not copy the analysis algorithm into each startup script or automatically
launch a second Agent for post-review operations.

## User-specific tasks

Users can keep Markdown instructions in `C/local-tasks/` without editing the
installed standard tasks. The program does not discover files there implicitly.
An explicitly selected [personal profile](PROFILES.md) can load review rules,
declare references, bind outputs and validators, and configure a separately
scoped post-review task. Users can also give instructions to their current Agent.
Every extension defines inputs, destinations, permissions, and retry behavior.

Configured tasks may maintain long-term knowledge, edit a user-selected file, or
send a notification. Such operations need an explicit target and rerun
behavior. A notification must not be sent again merely because a report was
regenerated. Separate the report's completion from a later operation's status.

Add a small deterministic helper when needed for stable behavior, rather than
building a general task framework before a concrete use requires one.
