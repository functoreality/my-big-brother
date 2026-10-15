# Manual cleanup

[简体中文](zh-CN/CLEANUP.md)

This release does not automatically remove source logs or run materials.
You can remove completed runs without removing published results.
Do cleanup between reviews, after the executing Agent has stopped and any
configured post-review work and correction acknowledgments have finished.

## Find the actual directories

From the checkout, using the Python environment used for installation:

```sh
python -m my_big_brother paths
```

Use its `raw_logs`, `state`, `results`, and `config` values.
Do not assume the checkout contains personal data.
Default Linux data lives below `~/.local/share/my-big-brother/`.
On macOS and Windows, use the paths reported by this command.
A selected profile can publish outside `results`: check `profile.output_paths`
or a run's `context.json` and its `final_output_paths` before cleanup.

| Location | Contents | Manual cleanup |
| --- | --- | --- |
| `raw_logs/YYYY-MM-DD/` | Application captures, grouped by natural date | Remove old dates after their records are no longer needed, writers have stopped using them, and relevant reviews are complete |
| `state/runs/DATE/RUN-ID/` | Selected indexes, excerpts, screenshot sheets, drafts, scripts, logs, receipts and optional `actions/` | Remove the whole run after completion and any final acknowledgments, or explicitly abandon an inactive unfinished run |
| `state/launches/INVOCATION-ID/` | Startup context, Agent output logs, date tickets and automation receipts | Remove after the Agent has stopped and the invocation has completed, or after diagnosing and abandoning a failed invocation |
| Scheduler log, often `state/scheduler.log` | Appended startup output | Archive or truncate old content between scheduled invocations |
| `state/completed.json` | Completion history used to skip completed dates | Keep |
| `state/locks/` | Coordination files | Keep, especially while any process may be running |
| Other profile/import state | Queues, deduplication and recovery information | Keep unless the extension's own instructions say otherwise |
| Published results and selected profile targets | Reports, cumulative knowledge and persistent post-review outputs | Keep |
| Configuration and installed local tasks | Settings, path pointer and personal instructions | Keep |

Native Agent histories stay in the Agent's own directories. They are inputs,
not copies owned by this project's cleanup procedure. Manage them through
their owning application's retention process.

## Remove old source captures

Open `raw_logs` in your file manager and sort date folders by name.
Check an old folder, then delete it or move it outside all configured source
roots for a temporary archive. Emptying the trash releases the disk space.
Moving an archive elsewhere on the same disk does not release space.

Directory age alone is insufficient. Legacy Bash sessions can keep writing
into their session-start date folder, and Vim sessions can close much later.
Do not delete a folder still used by an open terminal, editor or recorder.
Review windows can span two natural dates, for example 04:00 to next-day 04:00.
Check the adjacent review window before deleting a whole natural-date folder.

Removing source data does not remove published reports. It does limit future
reruns and corrections. Retained screenshot sheets are lower resolution and
do not replace the original frames. Some Vim evidence is also referenced in
place rather than copied into a run.

## Remove old analysis runs

1. Open `state/runs/`. Its first level is the **review date**.
   Within each date, run IDs start with the preparation timestamp, followed
   by a random suffix. A historical review can therefore have a recent run ID.
2. Open each run's `state.json`. A `completed` status means review publication
   and configured post-review validation completed for that run.
   Check that its published files still exist at `context.final_output_paths`.
3. Confirm that no Agent is using the run and no invocation or personal
   correction acknowledgment still needs its files.
4. Delete that `RUN-ID` folder, including its indexes, excerpts, screenshot
   sheets, drafts and `actions/`. A `DATE` folder can be removed as a whole
   only after checking every run inside it.

`prepared`, `empty`, `blocked`, `actions-pending`, and `actions-failed` are not
completed reviews. Neither an Agent-written `completion.json` nor the launch
status `agent-exited` proves successful completion. Preserve unfinished runs
for recovery, or explicitly decide to abandon them after all users stop.
Do not remove an `actions-pending` run and expect automatic recovery to work.

With published files and `state/completed.json` retained, normal completed-day
skipping does not require the old run directory to exist. That ledger can
retain the old path as historical metadata. After removal, you cannot resume
or revalidate that old run in place. An explicit rerun prepares a new run and
requires sufficient retained input. Custom extensions can have additional
dependencies on old runs, so check their instructions first.

## Remove old startup records and other copies

Launch IDs are random rather than date names. Read a launch's `state.json`
for `updated_at`, and `automation-context.json` or `tickets.json` for selected
dates. For a successful shared automation, check `automation-result.json`
has `status: completed`. `agent-exited` alone only reports process exit.
After the invocation is finished or explicitly abandoned, its directory can
be removed. Do not delete launch records while an Agent is writing them.
Native Agent schedulers may keep their own execution history instead.

Old installation backups, test fixtures and legacy recorder directories can
also consume space. They are not required for the daily report format, but
can be needed for rollback, import or recovery. Review them separately.
An enabled importer can recreate deleted raw captures from retained legacy
sources. Removing only the imported copy is not a permanent retention policy.

Keep the application data root and state root themselves. Do not clear all
of `state`, configuration, results, or profile-owned knowledge to remove
temporary material.
