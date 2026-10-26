# Daily output contracts

Use `context.output_paths` as the exact write destinations. All paths there
are staged inside this run. `context.final_output_paths` describes stable
published destinations and can be used for links between daily reports.
Write in the configured language. The date is the analysis day from context.
The default paths and schemas below apply without a profile override.
If a selected profile declares custom output bindings or schema, use the
resolved context and its instruction files. A custom schema requires its
configured validator. Receipt and publication checks still apply.

Only write selected outputs. Do not create additional output files or modify
private user documents as a side effect of this standard task.

## Worklog

Published at `records/YYYY-MM-DD/worklog.md` below the results root.

Organize by meaningful workflows or projects, with subtasks where appropriate.
For each substantial item, name the object, action, and supported outcome.
Distinguish proposed, attempted, reported, and verified work when necessary.
Combine scattered periods of one task without erasing distinct decisions or
deliverables. Do not impose a daily item count or a symmetric heading tree.

Include approximate periods when supported. Say that timing is uncertain
when it cannot be inferred. A short coverage note should identify enabled
sources and consequential gaps. Do not turn missing evidence into downtime.

## Time Use

Published at `records/YYYY-MM-DD/time-use.md` and
`records/YYYY-MM-DD/time-use.json`. JSON is the canonical representation.
Markdown is its readable view, not another independently maintained timeline.

Use this JSON structure:

```json
{
  "date": "2026-01-15",
  "segments": [
    {
      "start": "2026-01-15T10:00:00+00:00",
      "end": "2026-01-15T10:00:00+00:00",
      "activity": "Requested a review of the parser",
      "confidence": "high",
      "human_attention": "Observed message submission, duration unknown",
      "limitations": ["Conversation evidence does not show continuous work"]
    }
  ],
  "limitations": []
}
```

Use ISO timestamps with timezone offsets inside the run window, in time order.
An isolated interaction may have equal start and end. Do not invent a longer
interval to make the timeline appear complete. Use `high`, `medium`, or `low`
confidence with the evidence limitations explaining its basis.

`human_attention` is a concise description of observed or inferred attention,
or explicitly unknown attention. It is not a computed duration and need not
equal the activity's elapsed span. Background AI progress is not human effort.
Concurrent activities may overlap when justified, but do not count human
attention twice. Unknown gaps remain unallocated.

The Markdown view should state the observable range when available, show
chronological entries, and explain important uncertainty and source gaps.
The input window is not a claim that all of it was observed.

## Daily Insights

Published at `records/YYYY-MM-DD/insights.md`.

Write useful analysis, hypotheses, and suggestions grounded in specific
recorded work. Possible subjects include task arrangement, avoidable rework,
concrete techniques, delegation opportunities, and background or instructions
worth making reusable for future AI work.

Use a conclusion or testable question as each finding's heading. Identify its
purpose in a short type label such as "time management", "working method",
"AI delegation", "reusable context", or "question". Explain the minimal
evidence, likely benefit, applicability, confidence, and what could disprove it.

Without a profile, do not pretend private method notes or preferences exist.
With a profile, compare relevant passages in its explicitly declared references.
Do not infer that a method was omitted merely because it is absent from logs.
One observation can support a conditional suggestion, but not an established
habit or a personality judgment. No daily quota of new insights is required.
If no distinct supported finding exists, say so briefly.

## Time Estimates

Published at `records/YYYY-MM-DD/time-estimates.json`.

These are dated evidence samples for later budgeting, not a claim that a
reliable estimation model already exists. Use:

```json
{
  "date": "2026-01-15",
  "samples": [
    {
      "task": "Validate a small parser change against a fixture",
      "elapsed_minutes": 8,
      "human_minutes": null,
      "confidence": "medium",
      "basis": "Observed request and reported result eight minutes apart. Human effort is not established."
    }
  ]
}
```

Choose bounded tasks with clear completion conditions and comparable scope.
An open-ended project, loosely bounded research session, or unexplained
conversation gap usually does not qualify. Do not emit samples merely to
fill this file. `samples: []` is valid and often appropriate.

`elapsed_minutes` measures a supported task span, not focused work.
`human_minutes` must be null unless evidence independently supports that
estimate. Never copy elapsed minutes into human minutes by default.
Explain interruptions, concurrent work, assistant-reported completion, and
coverage limitations in `basis` when relevant. Do not add overlapping spans
to fabricate a parent task duration.

Replace each day's staged sample file on rerun, preserving relevant manual
corrections. Never append duplicate samples merely because a run repeated.

## Cumulative knowledge

`user-model` publishes `USER-MODEL.md`, with output kind
`user_model`. `machine-context` publishes `MACHINE-CONTEXT.md`,
with output kind `machine_context`. Both are ordinary standard Markdown
outputs, available to any executing Agent without a personal profile.
New installations select both by default. Users may disable either output.
Existing explicit output selections remain unchanged. Their targets are
cumulative across dates.

Follow `KNOWLEDGE.md` for their evidence, preservation and scope rules.
Existing targets are copied into staged drafts before analysis, including
manual edits. Update those drafts without replacing earlier knowledge with
only this day's findings. A supported absence of new knowledge permits an
unchanged draft. A new file can briefly state that no supported knowledge
has been established. Never invent facts to satisfy output completion.

## Stable results and temporary notes

Daily outputs describe the work, not the review process. Do not add run IDs,
temporary evidence registries, excerpt paths, or repeated revision sections
to reports. Keep evidence tracing, progress, and checks in the run directory.
Preserve user additions when updating existing reports.
