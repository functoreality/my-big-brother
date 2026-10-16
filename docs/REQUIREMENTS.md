# Product requirements (PRD)

English | [简体中文](zh-CN/REQUIREMENTS.md)

This document defines the current product from the user's point of view.
It consolidates agreed behavior, rather than proposing new capabilities.
[Architecture](ARCHITECTURE.md) explains the implementation.
[Contributing](../CONTRIBUTING.md) defines how either contract may change.

## P1. Purpose and everyday use

My Big Brother turns locally recorded computer work into useful daily reports
and accumulated context. An Agent connects evidence from different tools,
distinguishes outcomes from claims, and records uncertainty.
Users should not have to reconstruct the day separately for each output.

Daily unattended review is the primary workflow. Its published records also
support two user-directed uses: asking an Agent to summarize a week or another
period, and letting an Agent working elsewhere consult relevant work, user or
machine context. These reuse accumulated outputs. There is no built-in weekly
report command or automatic discovery by every external Agent.

## P2. Installation and control

The product is an ordinary local repository. Users can give their Agent
`INSTALLATION.md` to perform installation. The public installation must work
without this author's paths, proxy, private notes or pre-existing memory files.
Program files, personal configuration and recorded data remain separate.
Human documentation is available in English and Simplified Chinese.

Users choose evidence sources, output types, report language, destinations and
an unattended executor. The executor choice does not restrict which Agents'
histories are read or which Agent users employ for interactive work.
Installing the project does not itself authorize continuous recording or a
schedule. The installer obtains the user's choices before enabling either.
See [Setup](SETUP.md) and [Agent installation](../INSTALLATION.md).

## P3. Inputs and collection

| Input | Current capability | User action needed |
| --- | --- | --- |
| Agent conversations | Readers for supported native Codex sessions and OpenCode SQLite history | Select the source and its actual location |
| Bash activity | Bundled optional recorder and reader | Explicitly enable recording in an interactive Bash environment |
| Vim/Neovim activity | Reader and integration with independently released session-recorder.vim | Consent to installing/configuring the separate plugin |
| Screenshots | Reader and contact-sheet preparation, with optional Pillow | Supply captures from a separately configured collector |

There is no bundled periodic screen-capture service, browser recorder, VS Code
collector or universal reader for every Agent. These are possible extensions,
not implemented requirements or approved work merely because README lists them.

Selected sources report their coverage and gaps. Missing optional material
must not silently become evidence of inactivity. If a source marked required
is unavailable, the review must not publish a successful result.
Native histories remain in their applications' locations.
For exact formats and limits, see [Input sources](INPUT-SOURCES.md).

## P4. Trigger and reviewed period

An external scheduler or an Agent's native scheduling feature initiates the
unattended review. Each invocation starts exactly one executing Agent.
That Agent may use its own supported delegation facilities, but program code
must not chain multiple Agent launches to complete one invocation.

By default, an unattended invocation reviews only the latest closed logical
workday in the machine's local timezone. The configurable workday boundary
defaults to 00:00. The schedule's clock time is a separate installation choice,
not an internal waiting loop. For example, a user can select 04:00 as the
boundary and 10:00 as the daily trigger. Those are not global defaults.

There is no automatic catch-up of older days after downtime or a late record.
Users explicitly request an older date when needed. Only analysis uses the
logical boundary. Collection timestamps and recording locations do not shift.
See [Scheduling](SCHEDULING.md) for installation and manual operation.

## P5. Selected outputs

| Output | User value | Availability |
| --- | --- | --- |
| Worklog | Concrete objects, actions, outcomes and related tasks | Standard, selected by default |
| Time Use, Markdown and JSON | Observable chronology, coverage and uncertainty about attention | Standard, selected by default |
| Daily Insights | Grounded observations, hypotheses and useful suggestions | Standard, selected by default |
| Time Estimates | Conservative dated samples for future budgeting | Standard, selected by default |
| User Model | Supported reusable understanding of the user | Standard, optional |
| Machine Context | Known projects, directories and data-source locations | Standard, optional |

Outputs can be selected independently. Standard daily reports use stable dated
locations under the configured results root. Optional cumulative knowledge
uses stable cross-day files. Profiles can bind these to existing personal files.

Reports distinguish observed facts, requests, reported results and inference.
Elapsed time is not automatically human effort. Unsupported facts, continuous
attention and daily quotas of new insights must not be invented.
Outputs share one interpretation of the evidence and task relationships.
See the [output contracts](../tasks/daily-review/OUTPUTS.md) and
[Knowledge](KNOWLEDGE.md) for exact content and formats.

## P6. Recording behavior visible to users

Bash and Vim keep an entire session at the location chosen on its natural
start date, including sessions spanning midnight or months. They do not move
or split records when a day changes. Each screenshot uses its own capture date.
A later review must still find relevant events from an earlier-started session.

Bash records session start, complete submitted history inputs and normal exit.
Command context describes the directory before the whole input executes.
Native history filtering and duplicate policies do not exclude JSONL records,
and recording preserves native history content, filtering/duplicate policy
and settings. A full history list can be renumbered, affecting `!number`.
`set +o history` remains a known capture gap. A forced process termination may
prevent an end event. See [Bash](BASH.md) for precise fields and limitations.

Vim snapshots existing files when opened and writes its final diff/manifest at
exit. It does not add timers, midnight segments or live checkpoints. An ongoing
session without its final manifest is unavailable to review, and a whole-session
diff cannot precisely date individual edits. See [Vim](VIM.md).

## P7. Completion, reruns and failures

Prepared material is not a published report, and an Agent's zero exit code
alone does not establish completed analysis. Selected outputs and coverage
must pass the configured checks before completion is reported.
Validation checks structure and receipts, not the truth of model reasoning.

Reruns merge with existing formal outputs, preserving human additions and
corrections. Conflicting edits made during review stop publication rather than
being silently replaced. Failed review or follow-up work retains diagnostics
and can resume while its dated materials remain available. A repeated automatic
trigger skips a retained completed date. Pending follow-up work resumes without
regenerating its already published reports.
An explicit older rerun can create its dated directory, but cannot recover
previously deleted evidence or execution history.
See [Architecture](ARCHITECTURE.md) for the failure and conflict strategies.

## P8. Retention and manual cleanup

Users can sort `raw-logs/YYYY-MM-DD/` and delete inactive old dates directly,
without opening status files or deciding which run succeeded.
Each date contains its disposable captures, preprocessing, drafts, startup
logs, completion markers, publication journals and follow-up recovery records.
Do not delete dates still used by an active recorder or review.

Only selected formal outputs and accumulated knowledge are retained long-term.
One fixed-size `raw-logs/.publish.lock` is an explicitly allowed coordination
file outside date directories. There are no permanent per-day runtime ledgers,
operation histories or automatic correction queues. Applications do not require
`storage.json`. New retention categories require a reviewed requirement change.

Deleting a date abandons its recovery. It does not delete published reports or
undo changes already applied to other files. Verify existing effects before
explicitly repeating a follow-up operation. Cleanup is manual, with no built-in
automatic purge. See [Cleanup](CLEANUP.md) and [Storage](STORAGE.md).

## P9. Personalization and access

A selected private profile can supply methods, references, existing output
formats/destinations, validators and follow-up tasks. Reference notes are
optional. Standard behavior must remain useful without the author's files.
Personal paths, proxy settings, note formats and local policies stay private.
Generally useful additions should be evaluated as public optional capabilities,
not hidden in one installation or forced into every user's defaults.

Read scope comes from user authorization, not the Agent's launch directory.
A user can authorize relevant reference discovery across the machine.
This does not turn read access into permission to modify arbitrary files.
Follow-up operations require their own declared task, targets and completion
checks. Historical logs cannot authorize actions.
See [Profiles](PROFILES.md) for the configuration and scope contract.

## P10. Current boundaries and acceptance examples

The core targets Linux, macOS and Windows, but complete native macOS/Windows
execution and timer triggers remain unverified. Bash collection applies to
Bash environments, not PowerShell. Formal outputs and raw-log storage currently
must share a filesystem. Agent launchers and native log readers have independent
support lists. Do not advertise broader verified support than the evidence.

| Scenario | Required result |
| --- | --- |
| A morning trigger after several days offline | Review only the latest closed day, without silently filling earlier gaps |
| A shell crosses midnight and changes directory | Continue the original file and retain each input's initial directory context |
| A user asks for a weekly summary | Their Agent can use published records without a dedicated weekly command |
| A user deletes an inactive failed date | Its runtime state disappears with it, formal outputs remain |
| A human edits a report after preparation | Publication detects the conflict and preserves the newer file |
| A review cannot read a required source | Report failure/blocked work, not successful empty coverage |
| Another Agent performs the review | Use the same evidence and task contracts without invoking Codex internally |

Future ideas require the [document-first change process](../CONTRIBUTING.md).
Neither a proposal, a code implementation nor a passing test silently adds a
new product requirement.
