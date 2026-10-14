# Agent-led workflow

## 1. Establish the run

Read the task contracts, context, and manifest. Check that every enabled
source has an index and a stated status. Inspect existing staged outputs
before changing them. Keep all temporary work in the run directory.

## 2. Read and organize evidence

Read each complete index. For a long review, record covered blocks and
remaining work in `progress.md`. Follow excerpts that can change task
attribution, factual details, outcomes, or uncertainty.

Build a compact timeline and task map under `drafts/`. Each important claim
should point to source entries in these temporary notes. Separate independent
workflows from real subtasks. Preserve uncertain attribution and concurrent
tasks rather than forcing every record into one exclusive timeline.

Only delegate when the current Agent supports it and its host instructions
allow it. Delegation is optional. The coordinator remains responsible for
complete index coverage, compatible task boundaries, and consistent outputs.

## 3. Derive the enabled outputs together

Use one shared interpretation of the timeline and task relationships for all
outputs. Do not repeat a full independent analysis for each report.

Worklog records actions and outcomes. Time Use describes observed timing and
uncertainty. Insights adds useful judgments instead of repeating those facts.
Time Estimates selects only defensible reusable duration samples.
If selected, User Model retains reusable user context and Machine Context
retains known machine and source locations. Use the shared evidence and
`KNOWLEDGE.md`, without starting another analysis Agent or crawling the machine.

The time-use JSON, when enabled, is the authority for its Markdown view and
any duration samples derived from it. When time-use is disabled, retain the
same reasoning in temporary notes before producing duration samples.

## 4. Review and write staged outputs

Check that requests have not become claimed accomplishments, reported
results have not become independently verified results, and sparse evidence
has not become continuous focused effort. Check task grouping across outputs.
Remove duplicated items, unnecessary source quotations, and temporary paths.

On a rerun, update the same day's complete outputs. Merge new evidence into
the matching task or finding. Preserve user-authored notes and corrections.
If their provenance or meaning is unclear, retain them with a brief conflict
note rather than silently replacing them. Do not append another daily copy
or duplicate a duration sample because the run ID changed.
For cumulative knowledge, merge into the existing cross-day document rather
than replacing it with a daily report. Preserve human content and corrections,
deduplicate existing facts, and retain the basis of revisions.

Write only the resolved staged paths. JSON must be valid UTF-8 JSON with no
comments, fences, or trailing commas. Ensure time-use Markdown agrees with
its JSON. Empty evidence can legitimately produce empty lists.

## 5. Submit the completion receipt

Read `context.completion_example`, copy its identifiers and coverage shape,
and fill it with the exact prepared entry counts and staged output paths.
Write `completion.json` only after all required outputs are ready.

The receipt requests validation. It does not itself establish publication.
The executing Agent calls `finish` to validate the receipt and outputs before
publishing stable results. It then completes any returned post-review task
and calls `finish` again to validate that phase.
