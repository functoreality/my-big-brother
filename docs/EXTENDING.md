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

Create a module in `my_big_brother/sources/` implementing:

```python
def collect(path: Path, start: datetime, end: datetime) -> SourceResult:
    ...
```

`SourceResult` carries `rows`, `status`, and `gaps`. Use `ok`, `partial`, or
`unavailable`, and return rows sorted by timestamp inside `[start, end)`.
Rows include an ISO timestamp with offset and retain source-specific fields.
Conversation records include their role and content. The common preparer
separates readable excerpts from compact indexes.

Register the adapter in the source selection code and add its configuration,
task input rules, and synthetic format tests. The current registration is
explicit. There is no third-party plugin loader or universal activity schema.
Document supported versions and represent parsing failures as coverage gaps.

Read upstream histories without changing them. For new collectors, use the
shared `C/raw-logs-path.txt` location contract and write under
`raw-logs/YYYY-MM-DD/<source>/`, with natural-date folders and timestamped
records. Collectors do not read `results_root`.

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

## Add an unattended analyzer

Add a launcher in `my_big_brother/analyzers/`, register its configuration, and
document its required executable, authentication, writable scope, and timeout
behavior. Pass the same task entry and resolved run context to the Agent.
Preserve validation and completion-receipt checks after its process finishes.

Do not change source parsing merely because the execution backend changed.
Do not make optional multi-Agent capabilities a requirement for the task.

## User-specific tasks

Users can keep Markdown instructions in `C/local-tasks/` without editing the
installed standard tasks. This MVP reserves that location but does not
automatically discover, schedule, or execute those files.
Users explicitly provide additional instructions to their current Agent and
define inputs, destinations, and permissions.

Future tasks may maintain long-term knowledge, edit a user-selected file, or
send a notification. Such operations need an explicit target and rerun
behavior. A notification must not be sent again merely because a report was
regenerated. Separate the report's completion from a later operation's status.

Add a small deterministic helper when needed for stable behavior, rather than
building a general task framework before a concrete use requires one.
