# MVP validation

Validated on Linux on 2026-10-13 with Python 3.13.7 and Codex CLI 0.162.1.
macOS and Windows runtime behavior has been reviewed but not executed on
those operating systems. Native Windows Bash tests are skipped intentionally.

## Automated checks

```sh
python3 -m unittest discover -s tests -v
bash -n collectors/bash/session-recorder.sh
```

All 40 tests pass in the Linux environment. They cover:

- Codex message formats, mirrored-message deduplication, child-session
  exclusion, own-analysis exclusion, malformed data, and window boundaries.
- Read-only OpenCode SQLite, URI-special paths, text-part ordering,
  final-answer filtering, child exclusion, and unsupported schemas.
- Bash repeated commands under different history controls, history filters
  and disabled history, prompt strings and arrays, existing DEBUG/EXIT traps,
  exit status, umask, redaction, opt-out, and a real pseudo-terminal session.
- Platform directory rules and the single-line raw-log pointer contract.
- Separate excerpts and indexes, staged publication, completion checks,
  user-edit conflicts, backend failures, empty days, and catch-up idempotence.
- Concurrent publication of different dates without losing completion state.
- Windows npm-wrapper command construction through Node instead of a shell.
  These are fixture tests, not execution of Windows Codex.

A read-only native-format check also parsed current local Codex and OpenCode
records successfully. Their private text was not printed or copied into the
repository. Native parsing alone does not establish semantic analysis quality.

## Real analyzer smoke test

```sh
python3 tests/smoke.py
python3 tests/smoke.py --run-analyzer
```

The first command prepares isolated synthetic evidence without a model call.
The explicit second command invokes the installed Codex account and consumes
quota. This CLI isolation harness currently requires Linux/XDG.

It creates a separate configuration and data root under ignored `.local/`,
including paths containing spaces and a database name containing `#`.
It supplies four Codex messages, two OpenCode messages, and one Bash event.
No personal source history is used for this model test.

The real Codex run completed and published five files for four output types:

- Worklog.
- Time Use Markdown and canonical JSON.
- Daily Insights.
- Daily task-duration samples.

All seven prepared entries were confirmed in the completion receipt.
The program checked the receipt and output structure before publication.
Manual review confirmed that the Worklog describes the fixture work,
publishing remains pending, assistant claims are distinguished from direct
verification, overlapping activity is not added as human effort, and
unsupported human duration remains null.

The initial attempt was blocked by the test host's read-only Codex runtime
directory. Retrying with its normal runtime access succeeded while preserving
the isolated evidence and results. The underlying CLI logged model-list
refresh timeouts, but the analysis itself completed successfully.

The outputs from the successful run are available as
[synthetic examples](../examples/synthetic/README.md). They contain no private
work history. Local diagnostic files remain ignored by Git.
The saved run used UTC source timestamps. The current harness uses local
clock times to keep its events within one review day in different time zones.

## Installation checks and remaining limits

The isolated smoke test exercises `init`, `prepare`, `analyze`, and the
internal finish/publish path. Separate isolated installation checks also
executed `init`, `paths`, `doctor`, and `prepare` successfully.
The current-conversation finish path is covered by synthetic output fixtures.
The English installation instructions were checked against the implemented
commands and configuration fields.

No real shell hook, cron entry, LaunchAgent, or Windows scheduled task was
installed on the developer's machine. Scheduling instructions require a test
in the user's actual login and network environment.

Vim, screenshots, legacy OpenCode JSON storage, automatic cleanup, and a
standalone knowledge updater are outside this release. Bash is a partial
activity trace, with the specific limits in [BASH.md](BASH.md).
Windows timeouts terminate the launcher process but do not yet guarantee
termination of its entire child-process tree.
