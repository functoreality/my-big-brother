# Optional long-term knowledge outputs

English | [简体中文](zh-CN/KNOWLEDGE.md)

Two standard outputs retain useful context across reviews. They are available
to any executing Agent, with no personal task or memory service required.
They are optional, and the default four output selections are unchanged.

| `config.json` output | Output kind | Default path below `results_root` |
| --- | --- | --- |
| `user-model` | `user_model` | `records/knowledge/USER-MODEL.md` |
| `machine-context` | `machine_context` | `records/knowledge/SOURCES.md` |

Add either or both names to the existing `outputs` array. For all standard
outputs, use:

```json
{
  "outputs": [
    "worklog", "time-use", "insights", "time-estimates",
    "user-model", "machine-context"
  ]
}
```

This is a configuration fragment. Keep your other configured fields.
The executing Agent reads the shared [knowledge contract](../tasks/daily-review/KNOWLEDGE.md)
and uses the same evidence analysis as the daily reports. No extra Agent is
launched, and enabling these outputs does not request a machine inventory.

For catch-up reviews, use `plan-due --max-days N` to list dates without
preparing evidence. Process them oldest first with
`analyze --date YYYY-MM-DD --skip-completed`, completing the review and
`finish` before preparing the next date. Each later draft then starts from
the latest cumulative knowledge. Preparing all dates up front with `due`
can leave later drafts stale when an earlier review updates their shared target.

User Model records relevant goals, constraints and stated preferences.
Machine Context records known machine, file, directory and source locations.
Both distinguish explicit user statements, observations and uncertain
inference, with dated basis and scope. Mentioning a path in history does not
authorize reading it or prove it currently exists.

Existing targets, including manual edits, are copied into staged drafts.
The Agent merges supported updates, preserves earlier knowledge and user
corrections, and avoids duplicates on rerun. Without supported new facts, an
existing draft can remain unchanged. A new file can state that no supported
knowledge has been established.

`finish` validates and publishes the staged files with the daily outputs.
A conflicting change to a final target after preparation blocks stale
publication. Prepare a fresh review to merge the current version. Run drafts
retain the submitted version for that review. Publication
preserves existing file permissions unless the profile explicitly overrides
them. Later cumulative updates do not invalidate earlier completed dates.

To use existing knowledge files, select a [local profile](PROFILES.md) with:

```json
{
  "schema_version": 1,
  "output_paths": {
    "user_model": "/example/notes/USER-MODEL.md",
    "machine_context": "/example/notes/SOURCES.md"
  }
}
```

These absolute Markdown paths need no `{date}` placeholder. The selections
in `config.json` still control whether they are prepared and published.
No Codex-specific binding or custom post-review task is required. Additional
private reference files remain explicitly scoped through the profile.
