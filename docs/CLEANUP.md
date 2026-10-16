# Manual cleanup

[简体中文](zh-CN/CLEANUP.md)

Open the `raw-logs` directory reported by:

```sh
python -m my_big_brother paths
```

Sort its `YYYY-MM-DD` folders by name, select inactive old dates, and delete
those folders in your file manager. You do not need to open status files,
inspect each run, or distinguish successful dates from failed dates.
Empty the trash when you want to release disk space.

Each date owns its raw captures, `_analysis` indexes, excerpts, screenshot
sheets, drafts, temporary scripts, action material and `_launches` logs.
Deleting the date removes that disposable unit. Capture folders use natural
calendar dates. Bash and Vim sessions stay under their local start date across
midnight, so a review can depend on earlier dates as well as dates within its
window. Final session diffs do not divide edits precisely by date. Analysis
material uses the reviewed date label.
Do not delete dates that are actively being recorded or reviewed, including
an earlier date with a Bash or Vim session that is still recording.
A months-old folder can still be active when it owns a long-running shell.

Deletion removes completion markers, publication journals and action journals
with the evidence and run material. It stops recovery of that run. Published
reports, accumulated knowledge and applied changes remain. There is no
permanent daily state to keep elsewhere.

Unattended reviews consider only the latest closed logical day and do not
queue older dates. Request an older rerun explicitly with `--date YYYY-MM-DD`.
This may create its dated workspace but cannot recover deleted evidence or
operation journals. Verify external effects before repeating any operations.
New capture sessions use their own creation dates, and capture helpers can
create natural-date directories without a retained date registry.

Keep `memory`, including its directly visible knowledge and `records`,
configuration and personal tasks. A profile may publish permanent files outside
`memory`. Deleting disposable dates does not remove those formal outputs.
Leave the fixed-size `raw-logs/.publish.lock` in place. It coordinates publication
and contains no date history.

Removing raw evidence limits later reruns. Keeping a low-resolution sheet is
not a replacement for the original screenshot. Native Agent histories belong
to their applications and are not removed by this project.
