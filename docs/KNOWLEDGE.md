# Long-term knowledge outputs

English | [简体中文](zh-CN/KNOWLEDGE.md)

Two standard outputs retain useful context across reviews. They are available
to any executing Agent, with no personal task or memory service required.
New installations enable both by default, alongside the four daily output
types. Users can disable either. Existing explicit output selections are preserved.

| `config.json` output | Output kind | Default path below `results_root` |
| --- | --- | --- |
| `user-model` | `user_model` | `USER-MODEL.md` |
| `machine-context` | `machine_context` | `MACHINE-CONTEXT.md` |

The default `outputs` array selects all six standard output types:

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

Unattended review processes only the latest closed logical day. If the user
explicitly requests several older dates, process those dates oldest first with
`analyze --date YYYY-MM-DD`, completing publication and post-review before
preparing the next date. Each draft then uses the latest cumulative knowledge.
There is no automatic historical queue or missed-day recovery.

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

## Choosing where knowledge lives

The installation Agent follows this priority: your explicit request or existing
binding, suitable documents already maintained by the daily analysis Agent,
then the two project default files. It checks actual purpose, workspace, host
maintenance rules and write method. Names such as `USER.md`, `TOOLS.md` and
`MEMORY.md` are only hints. An installer using another Agent should choose for
the daily analyzer's workspace rather than its own private memory.

The installer can decide clear cases and tells you the final paths and whether
they are shared. It asks about unresolved ambiguity, preserves explicit choices
and binds the paths once. Daily reviews do not rediscover or switch documents.
A memory store requiring a special API is not automatically integrated as a
Markdown file. The installer explains the limitation and selects another
suitable document or the project defaults.

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

The two types are independent selections, not a requirement for two files.
Both keys can point to the same suitable Markdown file, for example
`/example/workspace/MEMORY.md`. When both are enabled, preparation makes one
complete merged draft and `finish` publishes that file once. The completion
receipt lists its staged path once. A shared file retains its original
organization and unrelated content, including host instructions and manual
corrections. Updates respect the host's length and maintenance rules and avoid
turning long-term memory into a daily activity log.

Removing one type from `outputs` stops updates for that type. Its existing
content remains in a shared document while the other type is updated.
Custom validators must handle the shared mapping described in
[Profiles](PROFILES.md#output-validation). Sharing is supported only between
these two cumulative Markdown types, not between daily reports or JSON outputs.
