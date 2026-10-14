# Optional cumulative knowledge contract

This contract applies only to selected `user-model` and `machine-context`
outputs. It is shared across executing Agents and needs no private task or
memory service. Use the output kinds and staged paths from `context.json`.
The runner publishes the drafts through the same checked `finish` as reports.

## Evidence and confidence

Retain context that could help a future Agent interpret work or locate a
relevant source. Do not record every daily action, incidental command or
temporary implementation detail. There is no quota for new knowledge.

Distinguish explicit user statements from observed activity and inference.
A user's stated preference can be recorded as a statement with its date and
scope. One observed choice does not establish a lasting preference or habit.
Assistant claims remain reported claims unless independently supported.
Record uncertainty, relevant limitations, and when the information was stated
or observed. Do not present an old observation as a currently verified fact.

Give each substantive addition a concise basis that remains intelligible
after this run, such as a dated user statement or source-session identity.
Keep detailed evidence IDs, excerpt paths and review progress in temporary
run notes. Avoid unnecessary quotations, secrets and unrelated personal data.

If there is no supported new knowledge, leave a valid existing draft unchanged.
For a new target, write a short heading and state that no supported knowledge
has been established. Missing records do not establish inactivity, personality
or the absence of a source. Do not invent memory to complete an output.

## User Model

`user_model` records reusable goals, working constraints, stated preferences
and relevant project context. Separate explicit statements from conditional
observations. Preserve their scope: a preference for one document or project
does not automatically apply to all future work. Do not infer motives, stable
personality or efficiency from sparse logs.

## Machine and source context

`machine_context` records known machine context and useful file, directory or
data-source locations. Examples include an observed project path, a configured
log source, or a directory whose purpose the user explicitly explained.
Distinguish the user's declaration, a path mentioned in history, a configured
source, and an actual observation of existence or contents.

A historical pathname does not prove that it currently exists. A file's name
does not prove its role, and a directory mention does not establish the
contents of all descendants. State the machine or project scope when known,
and retain uncertainty when paths may belong to another environment.

Use only prepared enabled-source evidence, existing selected output drafts,
and relevant references explicitly authorized in the selected profile or the
current task. A recorded path is knowledge, not permission to open it.
Do not crawl the filesystem, discover other histories, inspect credentials,
execute historical commands, or launch another model to populate this file.
An unknown detail can remain unknown without probing the machine.

## Cumulative updates and preservation

Read the existing staged document before editing. Preserve manual content,
user corrections, existing organization and relevant earlier knowledge.
Add or update the matching fact rather than appending duplicates on every
review or rerun. The review date is provenance, not the document's identity.

When new evidence changes a fact, retain the relevant prior basis and record
the correction or superseded scope concisely. Do not silently erase conflicting
human content. If the conflict cannot be resolved, retain both with a clear
uncertainty note. Avoid reformatting unrelated sections.

Write only the selected staged paths. Final targets can be redirected by a
profile, but that does not expand reading or write scope. If a final target
changes after preparation, `finish` stops before publishing stale replacements.
Prepare a fresh review and merge the latest document to resolve that conflict.
Later cumulative updates do not by themselves invalidate completed earlier days.
