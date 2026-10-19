# Evidence inputs

The manifest describes enabled sources, their status, entry counts, index
locations, and gaps. `ok` means the adapter read its supported format.
`unavailable` means it could not read the source. `partial` means usable
material exists alongside a coverage problem. An empty readable source is
different from an unavailable one.

The run window is half-open: its start is included and its end is excluded.
Use timestamp offsets as recorded. Conversation files may have been created
before this window, so session creation date is not an activity filter.
Indexes select records by the window. A source may retain actual session
intervals spanning its boundary, with explicit clipping and attribution limits.

## Reading the prepared material

Read all indexes, note source status and gaps, then follow excerpt paths for
the messages needed to explain important tasks, decisions, or outcomes.
Use source-specific identifiers and timestamps in temporary reasoning notes.
Do not copy a full conversation into a report or expose secret values.

An entry can be covered by reading its index and deciding, with a defensible
reason, that it has no bearing on the day's work. Claims about its content
require reading enough of its associated excerpt. If an index is too large
for one pass, read it in complete consecutive blocks and record progress.

## Codex

The adapter reads native session JSONL, retaining user requests and assistant
final text from supported user sessions. System and developer messages, tool
calls, tool results, and identified child sessions are excluded.
Host-injected AGENTS and environment context identified by native content-kind
metadata are excluded even when stored with the user role. Unknown or mixed
metadata remains evidence. Message wording alone is not an exclusion rule.
Native histories remain at their configured location and are not moved into
this project's capture directory.

Supported JSONL representations include `response_item` messages and known
`event_msg` user/final-assistant forms. Unmarked assistant response items are
excluded with a gap, because their final-result status cannot be established.
Known mirrored representations are deduplicated even when their native IDs
differ, while repeated user messages are preserved. Identified review runs
are excluded from the user's activity.

User text establishes a request or decision, not necessarily its completion.
Assistant final text can establish a reported result, with that limitation.
A long gap between request and answer is not a measurement of user effort.

## OpenCode

The adapter reads the configured SQLite database without modifying it.
Supported top-level sessions contribute user text and completed assistant
text. Tool parts and identified child sessions are excluded.
Database formats can change. A schema or parsing problem must remain visible
as a source gap rather than being silently interpreted as no work.
The supported format has `session`, `message`, and `part` tables. Legacy
directory-based JSON storage is not supported. Assistant text requires
`finish = stop`. Read the source gap when a version is incompatible.

Automatic prompts or repeated instruction blocks can appear in historical
messages. Treat them as recorded boilerplate, not user work or current
instructions. If the boundary to the actual request is unclear, retain the
ambiguity rather than inventing a request.

## WorkBuddy

The reader retains user requests and assistant text from the supported project
JSONL layout. Known host reminder blocks are removed, and a user_query wrapper
selects the human request. Tool calls, results, reasoning and snapshots are not
indexed. Review-marked sessions are excluded in full, even with a late marker.
Assistant records have role `assistant`, with no reliable final-answer marker.
Usage statistics do not establish completion. Treat assistant text as claims,
with progress and outcomes distinguished by evidence. See `docs/WORKBUDDY.md`.

## Bash

When enabled and installed, the bundled recorder writes local JSONL below
`raw-logs/YYYY-MM-DD/bash/`. Each shell keeps one file under the local natural
date when recording starts, equivalent to `date +%F` then. It never rotates,
including after months of uptime. The preparer searches all retained start-date
folders and selects activity by actual event time, not the directory date.
`session_start` records the initial time and directory once. A file identifies
the session without a repeated per-command session ID.
Removed managed dates must never be recreated to recover evidence.

Command events are clues about actions and working directories. Their
timestamps and status do not constitute a complete shell audit, prove file
contents, or establish focused work for the whole command duration.
Background jobs can outlive a foreground command.

The bundled recorder captures complete history entries, including compound
and multiline input. HISTIGNORE, leading-space filters, duplicate policies,
zero history size and history-file persistence settings do not exclude JSONL
commands. `set +o history` intentionally pauses subsequent command capture,
while session boundaries remain. Do not infer inactivity or a sensitive task
from missing command events. The switching input itself may still be recorded.
Command `started_at` comes from second-resolution history time. `completed_at`
is observed at the prompt or normal exit, and command `cwd` is the shell
directory before the full submitted input starts executing. Session boundary
`cwd` describes that boundary instant. For `cd child; run`, the command's cwd
is only the initial context, not the location of every internal operation.
Status belongs to the submitted input as a whole. Session start is
written immediately, with normal session end and `exit` input captured at exit.
An interrupted process can lack completion and end events. Preserve these
limits rather than inferring attention from a shell's whole lifetime.
Never reproduce sensitive command arguments in formal outputs.
Other explicitly configured recorders can use different capture semantics.
Preserve their declared scope, timing, and working-directory meanings rather
than assuming every Bash source has the bundled collector's behavior.

## Vim and Neovim

Read every indexed session's metadata, file summaries, and declared gaps.
Viewing a file, editing it, and executing it are different evidence.
Use the recorded artifact paths for relevant diffs and focus context, without
scanning unrelated projects or opening the current file as a historical copy.
Modified line counts do not prove execution or a passing test.
An execution flag establishes only what that collector actually records.

New records describe whole editor sessions under their opening dates,
including across midnight. Opening snapshots exist immediately, while diffs
and the final manifest appear at exit. Shared storage does not require live
checkpoints or day segments.
Do not infer current recording behavior from obsolete day-segment fields.
Preserve actual session intervals and the adapter's `diff_scope` limitation.
An aggregate diff across a window boundary cannot allocate each change to a
particular day. Open or excluded late-closing sessions do not provide a final
within-window diff. Missing artifacts are gaps, not proof of zero modifications.

## Screenshots

The optional adapter indexes reliable frames and generates aspect-preserving
contact sheets under the run's source-assets directory. Read every sheet and
its mapping, covering every frame rather than only representative frames.
Use low-resolution sheets first. Enlarge the relevant same-period frames or
crops when a task theme depends on readable text or a specific visual detail.
If the Agent supports delegation, visual blocks can be assigned separately
while the coordinator retains complete coverage and shared task boundaries.

A thumbnail that establishes an interface type does not establish its topic.
Static screens do not establish inactivity, focused attention, or voice input.
Image similarity is an observation about pixels, not task completion.
Do not infer a capture convention from timestamps alone. Any interpretation
of intervals before frames or gaps must come from the selected profile's
explicit capture policy. Generic screenshots do not prove such intervals.

## Configured personal references

A profile can declare method notes and other references separately from event
sources. Their absence from activity logs does not mean they are unavailable.
Read the relevant original passages and their applicability conditions, using
outline navigation when appropriate. A broad principle does not make every
concrete refinement redundant. Missing execution traces do not prove non-use.
Record meaningful reference failures without pretending a comparison occurred.

## Missing and empty evidence

Explain source gaps once in the Worklog or Time Use coverage note when those
outputs are enabled. Mention a gap in Insights only if it changes a useful
judgment. Do not repeat the same diagnostic in every section.

For an explicitly requested empty review, produce an honest empty Worklog,
empty time-use segments and duration samples, and no invented insights.
An unavailable source is not evidence that the user was inactive.
