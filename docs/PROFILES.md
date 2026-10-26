# Personal review profiles

English | [简体中文](zh-CN/PROFILES.md)

A local profile supplies selected methods, private reference locations,
existing report destinations and optional operations after a daily review.
It is an explicit extension of the review, so its instructions can change
interpretation and structured output semantics. Keep profiles, instructions,
reference files and validators outside the installed checkout.

Set `local_profile` in `C/config.json` to the absolute path of one JSON file.
The default is `null`, which keeps the standard daily task and destinations.
Files under `C/local-tasks/` are only used when this profile names them.
The program does not discover other profiles or private notes.

## Profile fields

The profile has `schema_version: 1` and these optional fields:

| Field | Meaning |
| --- | --- |
| `instructions` | Absolute paths of review instruction files |
| `context_files` | Existing absolute paths allowed for read-only reference |
| `output_paths` | Selected output destinations, with `{date}` for daily outputs |
| `output_file_mode` | Optional POSIX publication mode, as a four-digit octal string |
| `output_schema` | `default`, or a named custom schema with a validator |
| `validation_command` | Validator executable and arguments, as an array |
| `post_review` | A separately scoped task after report publication |

`context_files` registers allowed reading locations. It does not copy their
contents into run material or load every file into the Agent's context.
The task should read relevant portions, preserving outline ancestor conditions
when needed. Directory entries allow related material in that directory,
but do not request a scan of all private contents. Historical material stays
evidence and never becomes authorization or instructions.

Reading is not limited to the launch directory. When the user authorizes
machine-wide reference discovery, declare the appropriate filesystem roots
in `context_files` and post-review `read_paths`. Then follow task-relevant
project and asset references across those roots. Listed individual references
are useful entry points, not a requirement to enumerate every relevant file.
This grants no additional write targets and does not enable other evidence
sources automatically.

The dated `output_paths` keys are `worklog`, `time_use_markdown`, `time_use_json`,
`insights`, and `time_estimates`. These must be absolute and contain `{date}`.
Standard knowledge outputs use `user_model` and `machine_context`.
Their absolute Markdown destinations can be stable paths without `{date}`.
New installations enable them by default. Select or disable them through
`config.json`'s `outputs`, as described in [KNOWLEDGE.md](KNOWLEDGE.md).
Unspecified keys use the standard results layout. Only enabled outputs are
prepared and published. Distinct outputs must have distinct destinations.
Staging always stays inside the run directory, even with custom destinations.

On POSIX systems, publication preserves an existing destination's permission
bits and gives new files mode `0600`. Set `output_file_mode` explicitly, for
example `"0664"`, when published reports need a shared workspace's permissions.
This option affects formal reports only. Configuration and runtime files remain
private. It has no effect on Windows file permissions.

For example, a profile can use local methods and an existing report layout:

```json
{
  "schema_version": 1,
  "instructions": ["/example/configs/local-tasks/review-rules.md"],
  "context_files": ["/example/notes/methods.md"],
  "output_paths": {
    "worklog": "/example/records/worklog/{date}-work-log.md",
    "time_use_markdown": "/example/records/time-use/{date}.md",
    "time_use_json": "/example/records/time-use/data/{date}.json",
    "insights": "/example/records/insights/{date}.md",
    "time_estimates": "/example/records/duration-candidates/{date}.json"
  }
}
```

Use real existing absolute paths for instructions and references.
Missing files cause a configuration error rather than a guessed replacement.

## Output validation

With `output_schema: "default"`, the standard output contracts and validators
apply. An optional `validation_command` then adds a further check.
For a custom schema, the command is required and replaces the standard shallow
structured checks. Regular output files, nonempty Markdown, valid JSON objects
and the exact analysis date are still required.

The command is an argument array whose first entry is an absolute executable
path. `{run_dir}` and `{date}` are its only placeholders. It runs with the
review directory as its working directory, has a five-minute timeout, and
must exit zero. There is no shell expansion. Validator stdout and stderr stay
in the run's `logs/`, including failures. A validator is trusted local code
selected by the user and should check outputs without changing formal files.

The validator can read `context.json` and use `output_mapping` or `output_kinds`
to identify each staged file. It should check all requirements of the custom
schema, including relationships and cross-output consistency where relevant.
Naming a schema does not implement a validator or prove semantic correctness.

For example, an existing structured timeline can declare its own schema:

```json
{
  "schema_version": 1,
  "output_schema": "legacy-v4",
  "validation_command": [
    "/example/venv/bin/python3",
    "/example/configs/validate-review.py",
    "{run_dir}",
    "{date}"
  ]
}
```

Completion-receipt identity, exact prepared-source counts, expected staged
paths, profile consistency and protection against post-prepare user edits
remain mandatory. A custom validator cannot bypass them.

## Operations after the review

Public [local reminders](NOTIFICATIONS.md) use the top-level `notifications`
setting, without a private profile. New installations enable them by default.
They run before a configured private `post_review`. Existing configurations
without the new field retain prior behavior. Check for duplicate reminder
responsibilities before enabling both public and private delivery.

The two standard cumulative knowledge outputs use normal staging and
publication. Redirecting them needs only `output_paths`, without a private
maintenance task or `post_review` operation.

Use `post_review` for other explicitly authorized knowledge operations,
candidate ledgers, cross-day duration libraries or local Inbox operations.
The review phase writes only staging and temporary material.
The runner first validates and
publishes daily reports, then returns `actions-pending` with an action prompt.
The same executing Agent performs each returned task and calls `finish` again
until the review is `completed`.
The common runner never starts a harness or a second Agent.

`post_review` requires an existing absolute `task` file and a nonempty
`validation_command`. `read_paths` lists existing allowed reading locations.
`write_paths` lists absolute directories where changes are authorized.
The external startup entry or native Agent must grant those declared write
locations to the executing Agent. The common scripts do not grant harness
permissions or start an Agent. Validators still run as ordinary subprocesses.
The task can further restrict filenames and operation types inside those roots.
Declare narrow directories suited to the task.

```json
{
  "schema_version": 1,
  "post_review": {
    "task": "/example/configs/local-tasks/maintain-review-knowledge.md",
    "read_paths": ["/example/notes/methods.md"],
    "write_paths": ["/example/records/knowledge"],
    "validation_command": [
      "/example/venv/bin/python3",
      "/example/configs/validate-actions.py",
      "{run_dir}",
      "{date}"
    ]
  }
}
```

The action directory is `<review-run>/actions/`. Its `context.json` supplies
the task, declared scope, published report paths, `review_context`,
`review_run_dir`, and an
`action_receipt_example`. The task writes `action_receipt.json` matching the
example's `run_id`, `date` and `status: "completed"` only after completing all
required work. The runner checks the receipt and runs the action validator.
For this validator, `{run_dir}` means the action directory, rather than the
parent review directory. Its output goes into the action `logs/`.
The task can read relevant prepared evidence and temporary drafts from that
same review, including candidates that did not need a daily report or message.

Daily duration samples can remain a dated `samples` JSON file. A separate
post-review task can deduplicate and append them to an existing `samples.jsonl`
library and update its task-type estimate index. The profile must supply that
library's comparison, correction, retention and validation rules. The standard
daily schema does not itself implement a cross-day estimation library.

## Retry and policy changes

A day is complete only after both its reports and configured operations
succeed. If operations fail, published reports remain, the day stays pending,
and a later `due` or `analyze --date` returns the same pending action ticket
without regenerating reports. The caller then performs the task. Human report additions made after publication are kept.
`finish --run-dir` can also retry that run. A successful action receipt is
revalidated without repeating the completed operations.

The post-review task must be idempotent. Preserve operation records and stable
identities, search existing entries, and check before appending or sending.
Retries after partial work must not duplicate messages, duration samples or
memory facts. Receipts prove declared completion and validation, not that the
Agent independently measured every semantic condition.

Reports use ordinary file writes, with progress in `publication.json`.
Publication is not atomic. An interrupted write can leave a partial target.
Retrying `finish` continues only when destination digests still match the
prepared originals or complete drafts. Conflicts stop further writes.
Intact staged drafts remain available for manual recovery.
See [Storage](STORAGE.md#publication-and-interrupted-writes) before recovering
an interrupted write. Reports and later operations are not one transaction.

The profile fingerprint includes its JSON, named instruction/task contents
and declared validator scripts with `.py`, `.sh`, `.js` or `.ps1` suffixes.
Changing policy after preparation prevents stale publication. Changed policy
also makes `due` reconsider a completed day. Reference data contents are not
fingerprinted, so updating a ledger does not automatically rerun every day.
Change the profile when an intentional new policy should invalidate completion.
Source selection, language, day boundary and shared storage are
also checked against preparation and invalidate incompatible completion records.

Source configuration also accepts `required: true`. An enabled required
source marked `unavailable` blocks analysis. `partial` retains usable records
and visible gaps, including legitimate boundary exclusions. A readable empty
source is different from an unavailable one. Optional Vim and screenshot
sources are disabled by default and use the shared raw-log directory unless their
configuration names an explicit `path`.
Unexpected collection or asset-preparation errors also mark that source
`unavailable`, preserving the error and traceback in `logs/<source>-error.json`.
Other optional sources continue, while a required source failure blocks review.
Prepared records remain available for diagnosis even if visual preparation fails.

The Python runner accepts an optional timezone-aware `snapshot_end` for
`prepare_run` and `analyze`. The actual end is the earliest of that cutoff,
the current time and the logical day end. The window remains half-open.
This allows two preparations to be compared using the same cutoff without
including evidence that arrived later. A cutoff before or at the day start,
or one without a timezone offset, is rejected.
Pending operations keep their original run window on a normal retry.
An explicit matching cutoff resumes them, including equivalent timestamps
with different offsets. A different explicit cutoff prepares a new review.

## Storage lifecycle

Keep operation identities, uncertain outcomes, payloads, full logs and candidate
backups inside the dated run's action directory. Record stable identities before
side effects and inspect retained journals on retry. Deleting the date removes
all of that state without undoing applied changes. Explicitly requested reruns
must verify external effects because no permanent operation history remains.
Extensions must verify their own idempotence.

Formal output overrides must be outside `raw-logs`. They may use another
filesystem or mount with appropriate write permissions. See [Storage](STORAGE.md).
