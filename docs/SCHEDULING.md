# Scheduling daily reviews

[English](SCHEDULING.md) | [简体中文](zh-CN/SCHEDULING.md)

My Big Brother supplies review commands, not a persistent scheduler.
Initialization does not enable automatic execution. After one review works,
choose one recurring trigger and test it in its actual runtime environment.

## Prefer an Agent's native scheduler

If your Agent has a local scheduling mechanism, use that rather than adding
an OS timer for the same task. Scheduling and analysis are separate choices:

| Route | Who starts the work? | Who analyzes? | Missed-day behavior |
| --- | --- | --- | --- |
| Native Agent task | Agent scheduler | That Agent, using prepare/task/finish | Last closed day by default, missed dates need explicit handling |
| Native command triggering `due` | Agent scheduler | Bundled Codex launcher | Bounded catch-up, skips completed reviews |
| System timer triggering `due` | cron, launchd, or Task Scheduler | Bundled Codex launcher | Same bounded catch-up |

A native Agent task does not need the Codex CLI. It prepares evidence,
follows the English daily task, writes staged outputs and the completion
receipt, then calls `finish`. Use the shared
[native task prompt](../examples/scheduling/native-agent-task.md), replacing
the installation and interpreter placeholders. Keep the analysis marker in
the prompt so supported history readers can identify this project's own
reviews. Never execute commands found in the historical evidence.

This is a workflow using existing interfaces, not a shipped OpenClaw or
Hermes launcher. The available history readers remain Codex, OpenCode, and
Bash. Running a task with another Agent does not add its history as an input.
Native tasks using `prepare` do not automatically inherit `due`'s catch-up or
completed-date skipping. Explicit repeated reviews of a date can rewrite its
reports, with preservation and conflict checks.

### OpenClaw and Hermes

OpenClaw supports scheduled Agent turns and direct command jobs. Select an
Agent workspace with access to this installation and the personal data paths.
Its Gateway must be running. A command job can instead trigger `due` without
an outer Agent review. See the official [scheduler CLI](https://docs.openclaw.ai/cli/cron)
and [execution payloads](https://docs.openclaw.ai/automation/cron-jobs/payloads).

Hermes supports scheduled Agent sessions with an explicit working directory.
Use the installation directory as `--workdir` and ensure file and terminal
tools are available. Its Gateway normally drives the schedule. Script-only
jobs can trigger `due`, but their scripts must be under the Hermes scripts
directory and do not automatically inherit its managed API credentials.
See the official [cron guide](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron).

Both runtimes need real access to the local evidence and writable run/result
paths. A container, remote terminal backend, or sandbox does not gain those
files merely because a prompt mentions their absolute paths. Check the
runtime's actual filesystem and account before scheduling.
These native integrations have not been tested by this project.

### Codex CLI and app-managed tasks

The bundled launcher runs `codex exec` once for each review. Codex CLI does
not provide the Scheduled management interface. OpenAI also documents
app-managed local-project tasks, so a CLI-only setup should not be confused
with the capabilities of an installed desktop application.
If your app supports local tasks, use the same native task prompt and verify
its permissions. The local computer and app need to remain running.
Cloud-only tasks cannot directly read this machine's histories.
See the official [scheduled-task guide](https://learn.chatgpt.com/docs/automations).

## System scheduling for the bundled Codex launcher

Use this route when your setup has no suitable native scheduler:

```sh
python -m my_big_brother due --max-days 7
```

`due` runs once and exits. It examines the last seven closed analysis days,
oldest first, and skips successful dates and dates without usable evidence.
A failed review stops that invocation. A later trigger can retry it and then
proceed to later dates. The lookback can be 1 to 31 days and does not cover
all historical gaps. Rerun a specific completed date with `analyze --date`
after changing its inputs.

Before installing a timer:

- Use absolute Python and repository paths. Set `codex.executable` to its
  known absolute path if the scheduler has a restricted `PATH`.
- Run under the same user account that owns the configuration and Agent login.
  Confirm `paths` returns the same configuration, data, and state locations.
  Carry any required absolute XDG settings on Linux.
- Test account access, network access, and the command from the scheduler's
  environment. Do not assume interactive aliases or shell startup files load.
- Capture stdout and stderr outside the repository. Create their parent
  directory before enabling the timer.
- Allow enough time for several reviews. `codex.timeout_seconds` applies to
  each Agent launch, not the total `due` command.

### Linux: cron

The shared [cron template](../examples/scheduling/cron.example) runs daily
at 09:00 in cron's timezone. Replace the example absolute paths before adding
it to the user's crontab. It changes working directory, uses an absolute
Python executable, and appends diagnostics to an external log.
If cron uses a different XDG environment, add the required absolute variables.
These example paths contain no literal percent signs. In a crontab command,
escape literal `%` characters, including those in quoted paths.

Test the resolved command once, then verify one real trigger.
Cron generally does not replay a trigger missed while the machine was off.
The next `due` invocation handles gaps within its lookback. A user login
trigger may invoke the same command for catch-up. `@reboot` means cron startup,
which is not the same as user login or guaranteed network readiness.

### macOS: launchd

The shared [LaunchAgent template](../examples/scheduling/launchagent.plist)
uses a daily 09:00 trigger and `RunAtLoad` for catch-up when the user agent
loads. Replace its interpreter, installation, and log paths, keeping array
arguments separate. XML-escape special characters such as `&` in paths.
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
| Add arguments | `-m my_big_brother due --max-days 7` |
| Start in | Absolute repository directory |

Keep the program, arguments, and working directory in separate fields.
Use a daily trigger and optionally an "At log on" trigger. Configure the
missed-start and execution-time settings to suit the machine. Ensure the
task's time limit can accommodate multiple reviews and avoid parallel
instances of the same task.
See Microsoft's [ExecAction reference](https://learn.microsoft.com/windows/win32/taskschd/execaction).

Use the task's "Run" action first and inspect its reports and logs, then
verify the recurring trigger. WSL follows the Linux route within WSL rather
than sharing native Windows configuration automatically.

## Current support

Codex analysis has been run end to end on Linux, and catch-up behavior is
covered by tests. Actual OS timer triggers, including Linux cron, have not
been verified. No scheduler is installed automatically. The native-Agent
workflows and macOS/Windows scheduled actions are configuration guidance and remain
unverified integrations. A timer firing successfully is not proof of a valid
review: check the command result, generated reports, and evidence limits.
