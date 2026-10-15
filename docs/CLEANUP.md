# Manual cleanup

[简体中文](zh-CN/CLEANUP.md)

For storage v2, open the `daily` directory reported by:

```sh
python -m my_big_brother paths
```

Sort its `YYYY-MM-DD` folders by name, select inactive old dates, and delete
those folders in your file manager. You do not need to open status files,
inspect each run, or distinguish successful dates from failed dates.
Empty the trash when you want to release disk space.

Each date owns its raw captures, `_analysis` indexes, excerpts, screenshot
sheets, drafts, temporary scripts, action material and `_launches` logs.
Deleting the date removes that disposable unit. Dates are logical workdays:
with a 04:00 boundary, 14 October includes records through 15 October 04:00.
Do not delete dates that are actively being recorded or reviewed.

Deletion means abandoning automatic recovery. Review catch-up, collectors
and compatible importers do not recreate that date. Deleting a failed date
also stops its remaining operations. Already published reports and applied
changes remain. Only an explicitly user-authorized `--recreate-deleted` may
open a new generation. Ordinary `--date` does not grant that permission.

Keep `memory`, including its directly visible knowledge, `records` and
`_system` directories. Minimal per-day completion and discard records are
persistent system facts, not caches. Keep configuration and personal tasks.
A profile may also publish permanent files outside `memory`.

Removing raw evidence limits later reruns. Keeping a low-resolution sheet is
not a replacement for the original screenshot. Native Agent histories belong
to their applications and are not removed by this project.

For an old installation, complete the [v1 migration](STORAGE.md) first.
Retained v1 directories are one-time rollback copies to archive after old
writers stop, not additional v2 daily-cleanup locations. Legacy standalone
collectors do not provide the v2 deletion guarantee.
