# Scheduling daily reviews

[English](SCHEDULING.md) | [简体中文](zh-CN/SCHEDULING.md)

My Big Brother supplies review commands, not a persistent scheduler.
Initialization does not enable automatic execution. After one review works,
choose one recurring trigger and test it in its actual runtime environment.

## Choose the executing Agent and trigger

The installing Agent can also be the daily analyzer. Prefer its native local
scheduler when it meets the installation checks. Otherwise have it create a
one-shot startup runner
using its supported unattended interface and invoke that runner with an OS timer.
Consult installed help and official documentation if the interface is unclear.
Follow [INSTALLATION.md](../INSTALLATION.md) to resolve the actual execution
host and scheduled permissions, verify business completion, and avoid native
retry, repair or Agent-target delivery settings that start another Agent run.
Do not guess launch flags or substitute a different Agent without the user's choice.

| Route | Startup boundary | Executing Agent |
| --- | --- | --- |
| Native scheduled Agent task | The chosen Agent's scheduler | That Agent |
| Local runner plus OS timer | A runner for the chosen Agent | That Agent |
| Bundled Codex entry plus OS timer | `python -m my_big_brother.analyzers.codex` | One Codex invocation |

All routes use the same [automation task](../tasks/daily-review/AUTOMATION.md)
and common preparation/publication commands. The Agent plans dates with `plan-due`, then runs `analyze --skip-completed`
for each date, reviews the prepared run, calls `finish`, and
handles returned post-review work itself before calling `finish` again.
The common commands never start an Agent. The outer startup entry alone
contains product-specific command, login, sandbox and timeout handling.
Keep startup limited to one Agent invocation and necessary execution settings
and logs. Date planning, input import, publication and final
business checks belong to that Agent. Never loop over dates or retry by
starting additional Agents. The Agent can choose its own delegation tools.
`analyze` and `due` now return work tickets rather than launch Codex, so older
schedule commands must be updated to an external startup entry.

Use the shared [native task prompt](../examples/scheduling/native-agent-task.md),
replacing the installation and Python placeholders. This works without a
Codex installation when another Agent executes it. By default, review only the
latest closed logical day. Older dates require an explicit user-requested date.
No historical queue is processed automatically. Keep the analysis marker so
supported readers can identify this project's own review records.
Source readers are independent: using an Agent does not add its history format.

If using OpenClaw or Hermes, verify that the installed version provides a
suitable local task and can access the installation and personal paths.
Consult [OpenClaw scheduling](https://docs.openclaw.ai/cli/cron) or
[Hermes scheduling](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/)
as applicable. These are references for the installing Agent, not shipped or
verified integrations. Another Agent can be set up the same way.

## System scheduling for the bundled Codex launcher

Use this route when your setup has no suitable native scheduler:

```sh
python -m my_big_brother.analyzers.codex
```

Choose `codex.mode` in personal configuration. The default `exec` runs
noninteractively. `tmux` starts a real interactive Codex TUI in a detached
session on Linux, macOS or WSL with tmux installed. Native Windows uses exec.
The installing Agent asks for this preference unless it is already clear.
Optional `codex.working_directory` selects an existing absolute main workspace
for either mode, with workspace write access and normal Codex project-instruction
discovery. By default, the Agent starts in its dated launch directory. Choosing
another workspace keeps prompts, logs and temporary files in the dated run.
Write permission for formal outputs outside that workspace must still be granted.
A per-invocation override is:

```sh
python -m my_big_brother.analyzers.codex --mode tmux
```

The tmux entry returns `session-started`, `session_name` and `attach_command`.
Attach to that session to watch or send follow-up instructions. Detaching does
not stop it, and completion leaves the TUI available until you close it.
A missing/unsupported tmux setup fails rather than silently switching modes.
Terminal logs are kept under the invocation's dated `logs/` directory.
Neither a started session nor a successful scheduler exit proves completion.

This starts one Codex session. It follows the shared task, using `plan-due` to
select only the latest closed logical day, then prepares and completes its
review and pending actions. A retained completed date is skipped. Empty dates
produce no invented reports and are not marked completed. The next invocation
still considers only its latest closed logical day. Older empty, failed or
missed dates are not queued for automatic catch-up.

The Agent calls `begin-automation` and `complete-automation` itself.
In exec mode the entry reports `agent-exited`, which only records process exit.
In tmux mode it returns before completion. Inspect the
Agent-written `automation-result.json` in its returned `launch_dir` to confirm
checked review completion. Failed or blocked results cannot pass that check.
For a user-requested older rerun, use the external entry's `--date`, or ask the
executing Agent to process an explicit `analyze --date` ticket. An explicit date
may create its dated workspace, but cannot recover deleted evidence or journals.

Before installing a timer:

- Use absolute Python and repository paths. Set `codex.executable` to its
  known absolute path if the scheduler has a restricted `PATH`.
- Run under the same user account that owns the configuration and Agent login.
  Confirm `paths` returns the same configuration, raw-log, and output locations.
  Carry any required absolute XDG settings on Linux.
- Test account access, network access, and the command from the scheduler's
  environment. Do not assume interactive aliases or shell startup files load.
- The launcher writes logs inside date directories under `raw-logs`. Do not add
  a permanent aggregate log outside `raw-logs`. Pre-log setup errors may only be
  available as stderr or the host scheduler's own diagnostics. Check that any
  outer redirection has a valid parent before relying on runner notifications.
- Allow enough time for the review and post-review work.
  `codex.timeout_seconds` applies to the exec Agent session. tmux sessions stay
  available for user interaction until explicitly closed.

### Linux: cron

The shared [cron template](../examples/scheduling/cron.example) runs daily
at 09:00 in cron's timezone. Replace the example absolute paths before adding
it to the user's crontab. It changes working directory, uses an absolute
Python executable, and lets the launcher retain dated diagnostics.
If cron uses a different XDG environment, add the required absolute variables.
These example paths contain no literal percent signs. In a crontab command,
escape literal `%` characters, including those in quoted paths.

Test the resolved command once, then verify one real trigger.
Cron generally does not replay a trigger missed while the machine was off.
The next invocation reviews only the latest closed logical day. A user login
trigger may invoke the same command, without recovering older missed dates.
`@reboot` means cron startup,
which is not the same as user login or guaranteed network readiness.

### macOS: launchd

The shared [LaunchAgent template](../examples/scheduling/launchagent.plist)
uses a daily 09:00 trigger and `RunAtLoad` to review the latest closed logical
day when the user agent loads. Replace its interpreter and installation paths,
keeping array arguments separate. XML-escape special characters such as `&` in paths.
Save the resolved file in the user's LaunchAgents directory and validate it
with `plutil -lint` before loading it with the user's launchd tools.

See Apple's [timed-job guide](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html)
and [property-list reference](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5).
Verify an actual scheduled run under that user's account.

### Windows: Task Scheduler

Create a task under the account with the checked configuration and Codex login:

| Action field | Value |
| --- | --- |
| Program/script | Absolute path to `python.exe` |
| Add arguments | `-m my_big_brother.analyzers.codex` |
| Start in | Absolute repository directory |

Keep the program, arguments, and working directory in separate fields.
Use a daily trigger and optionally an "At log on" trigger. Configure the
missed-start and execution-time settings to suit the machine. Ensure the
task's time limit can accommodate review and post-review work and avoid parallel
instances of the same task.
See Microsoft's [ExecAction reference](https://learn.microsoft.com/windows/win32/taskschd/execaction).

Use the task's "Run" action first and inspect its reports and logs, then
verify the recurring trigger. WSL follows the Linux route within WSL rather
than sharing native Windows configuration automatically.

## Current support

The common workflow and external entry have isolated tests. A real Codex
run on Linux used fictional records and a personal post-review task. It
started one Agent and completed five reports plus the post-review receipt.
It did not verify a production installation or a timer trigger.
Actual OS timer triggers, including Linux cron, have not been verified. No scheduler is installed automatically. The native-Agent
workflows and macOS/Windows scheduled actions remain unverified integrations. A timer firing successfully is not proof of a valid
review: check the command result, generated reports, and evidence limits.
