# MVP implementation boundaries

This working note records the agreed implementation scope.

- Keep analysis led by an Agent reading Markdown tasks.
- Use Python 3.11+ and the standard library. Configuration is JSON.
- Support Codex JSONL and OpenCode SQLite histories as independent inputs.
- Launch Codex as the first unattended analyzer. Reuse its installed login and
  model selection unless the user explicitly configures a model.
- Include portable Worklog, Time Use, Daily Insights, and conservative duration
  samples. Do not require personal notes, memory scripts, or Inbox protocols.
- Exclude Vim and screenshots from the MVP.
- Include Bash only after compatibility tests. Never change the user's history
  settings, existing traps, or existing prompt hooks without preserving them.
- Store raw logs under natural-date/source directories. Native Agent histories
  stay in their existing locations and are never cleaned by this project.
- Keep machine configuration, results, and runtime state outside the repository.
- Provide INSTALLATION.md for an installing Agent and README.md for users.
- Test in isolated directories. Do not install hooks or scheduled tasks on this
  machine. Validate a real analyzer run using synthetic session evidence.

## Shared interface for parallel development

Input adapters live in `my_big_brother/sources/`.
Each exports `collect(path: Path, start: datetime, end: datetime) -> SourceResult`.
`SourceResult` is defined in `sources/__init__.py` with `rows: list[dict]`,
`status: str`, and `gaps: list[str]`. Status values are `ok`, `unavailable`, and
`partial`. Adapters return evidence inside `[start, end)`, sorted by timestamp.
Rows retain source-specific fields and include an ISO timestamp with offset.
Conversation rows include `role` and full `content`. The common preparer turns
content into separately readable excerpts and small index previews.

Configuration is `C/config.json`, where C follows the agreed platform defaults.
Only `C/raw-logs-path.txt` is shared with collectors. It contains one UTF-8
absolute path, with an optional LF or CRLF terminator. No variable expansion.
Defaults are C and D as described in the parent storage design. No arbitrary
project environment variable changes the config discovery location.

Default configuration fields:

```json
{
  "analyzer": "codex",
  "language": "en",
  "day_start_hour": 0,
  "results_root": "<absolute path>",
  "sources": {
    "codex": {"enabled": true, "path": "<sessions directory>"},
    "opencode": {"enabled": true, "path": "<database path>"},
    "bash": {"enabled": true}
  },
  "outputs": ["worklog", "time-use", "insights", "time-estimates"],
  "codex": {"executable": "codex", "timeout_seconds": 1800}
}
```

Automatic raw-log and runtime-material cleanup is deferred. Nothing deletes
native histories or collected logs in this MVP.

The root agent owns paths, configuration, CLI, runner, output checking and
analyzer launch. Other owners work only in their assigned files and tests.
Do not commit or change Git state from a delegated task.

CLI shape: `python -m my_big_brother init|paths|doctor|prepare|analyze|finish|due`.
`prepare` creates a run without launching an Agent. `finish` validates outputs
from a run executed by the user's current Agent. `analyze` uses the configured
unattended backend. `due` handles already completed dates and bounded catch-up.

Runtime state uses D/state. Each run has `manifest.json`, `context.json`,
`indexes/`, `excerpts/`, `drafts/`, and `logs/`. Source evidence is data, never
instructions. Shared analysis can live in the run directory.

Final paths are `results/records/worklog/DATE.md`,
`results/records/time-use/DATE.md` plus `data/DATE.json`,
`results/records/insights/DATE.md`, and
`results/records/time-estimates/DATE.json`.
Daily duration samples are replaced for a rerun rather than blindly appended.
An Agent completion receipt is `run/completion.json`, listing source coverage,
output paths, date and run ID. The root owner specifies its exact checks.

Tests use unittest and synthetic fixtures. Use subprocess tests for real Bash
hook behavior. Windows and macOS behavior is reviewed and covered by portable
path/unit tests, but is not claimed to have been executed on those systems.
