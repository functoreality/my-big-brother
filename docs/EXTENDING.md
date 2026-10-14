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

## Add an Agent startup entry

The startup boundary alone knows the Agent's executable, authentication,
sandbox and timeout. Start it once with the shared
[automation task](../tasks/daily-review/AUTOMATION.md), the installation,
Python, date/lookback and permitted paths. The Agent calls common preparation,
publication and receipt checks itself, including configured post-review.
Do not introduce Agent calls into `runner.py`, input adapters, validators,
or the shared CLI. A native scheduled Agent can use the same task without
any additional launcher.

The installing Agent can write a local entry using its installed execution
interface. Read installed help or official documentation when needed.
The bundled example is `python -m my_big_brother.analyzers.codex`.
A new entry can live outside the checkout or be contributed under `analyzers/`.
Validate actual completion against common run state, not only process exit.
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
