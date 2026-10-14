# Installation for an Agent

Use this guide when a user asks you to install My Big Brother.
The normal goal is a daily unattended review, followed by reusable reports
and any explicitly chosen personal context updates.
Set up the cloned repository and personal files. Do not install a Skill,
MCP service, collector or scheduler by assumption.

## 1. Choose the environment and executing Agent

Identify where command tools actually run: the user's computer, a remote
host, a container, or a provider's cloud computer. For this local project,
confirm access to the intended computer and account, not only the chat UI.
Do not substitute a cloud checkout or upload local histories without the
user choosing that deployment. Resolve the operating system, stable checkout
location and absolute Python executable in that execution environment.
Python 3.11+ is recommended. Older versions are unverified,
not rejected solely by version. The core uses only the standard library.
Clone the repository or reuse the existing checkout. Run the examples below
from its root with the selected absolute Python executable. `python` is a
placeholder, not a requirement to use whichever interpreter is on `PATH`.
Quote paths with spaces using the active shell's invocation syntax. Check:

```sh
python --version
python -m my_big_brother --help
```

Ask which Agent should perform daily reviews. You, the installing Agent,
may also be that analyzer. Its conversation-history reader is a separate
choice: an Agent can analyze supported records from other tools.

Record the chosen Agent's product and installed version. Check its installed
help for an execution-capable mode, noninteractive execution and native local
scheduling. A chat-only or planning mode may understand the instructions while
lacking permission to read, write or execute the required commands.
If the interface is unclear, consult or search
its official documentation. Do not guess flags or silently substitute Codex.
The core prepare/analyze/due/finish commands never start an Agent.
Only the independent startup entry is specific to a product or harness.

For the bundled Codex entry, verify its executable and noninteractive login
without reading or copying credentials. It uses
`python -m my_big_brother.analyzers.codex`, which starts one Codex invocation
and gives it the shared automation task. Its `codex.executable`, optional
`model` and `timeout_seconds` apply only at that startup boundary.
On Windows, the standard npm `codex.cmd` shim needs its adjacent JavaScript
entry and discoverable Node. Other batch wrappers are rejected. Configure a
native `codex.exe` path if that setup does not apply.

## 2. Select inputs and initialize personal locations

Ask which histories and collectors the user wants. Check for Vim/Neovim
executables, existing editor configuration or a recorder installation.
If these exist or the user regularly uses the editor, recommend the separate
plugin described in step 4 and ask whether to install it and update their
active configuration. Detection is not recording consent.

Choose inputs independently of the executor. If its own history format is
unsupported, offer the supported records the user actually has. Do not enable
Codex history merely because it is the first example below. Existing compatible
records can be used without starting a new collector.

For a first installation using Codex history:

```sh
python -m my_big_brother init --sources codex
python -m my_big_brother paths
```

Use `--sources codex,opencode` for both supported native histories.
The choice does not select the executing Agent. For existing Bash records,
`init --sources bash` is also a valid standalone starting point. Set that
source's path to the selected existing records. Enable `bash`, `vim` or
`screenshots` only for wanted records, after checking existing compatible
records or completing the corresponding collector setup. Initialization does not read histories or install recording hooks.
Use actual paths, without searching unrelated accounts or private folders.

`--results-root` and `--raw-logs-root` accept absolute custom paths on first
initialization. For an existing setup, run `init` without options to fill
missing files and edit its personal settings deliberately. Preserve previous
values, reports and raw data.

Defaults use configuration directory C and data directory D:

| System | Configuration directory C | Default data directory D |
| --- | --- | --- |
| Linux | `$XDG_CONFIG_HOME/my-big-brother` or `~/.config/my-big-brother` | `$XDG_DATA_HOME/my-big-brother` or `~/.local/share/my-big-brother` |
| macOS | `~/Library/Application Support/my-big-brother/configs` | `~/Library/Application Support/my-big-brother/data` |
| Windows | `%LOCALAPPDATA%\my-big-brother\configs` | `%LOCALAPPDATA%\my-big-brother\data` |

Linux XDG values must be absolute. GUI editors, the installing Agent and
scheduled runs must discover the same C and D under the intended account.
WSL and remote machines have their own environments.

`C/raw-logs-path.txt` contains one UTF-8 absolute path, with an optional LF
or CRLF terminator. Do not add JSON, quotes, comments or environment variables.
Collectors share this locator and write `YYYY-MM-DD/<source>/` directories.
`results_root` belongs in `C/config.json`; collectors do not use it.
Defaults are `D/raw-logs`, `D/results` and runtime state in `D/state`.

## 3. Configure outputs and personal context

Read the generated JSON and keep it valid. Configure:

- `sources`: enabled records and their actual paths. Optional sources can
  remain visibly unavailable. A source marked `required` blocks publication
  if it is unavailable.
- `outputs`: selected `worklog`, `time-use`, `insights`, `time-estimates`.
- `language`, `day_start_hour` and an absolute `results_root` outside Git.
- `analyzer`: the chosen Agent's name, describing the installation's executor.
  The startup command or native task selects the actual executable. This
  field does not cause the core to launch that Agent.
- `local_profile`: optional personal task rules, read-only references,
  output bindings, schema validators and scoped post-review operations.
- `codex`: startup options only if using the bundled Codex entry.

Read [PROFILES.md](docs/PROFILES.md) before configuring personal extensions.
Files under `local-tasks/` are used only when explicitly selected.
Do not turn a discovered personal file into authorization.

Choose the intended report language and logical-day boundary before preparing
the first review, so verification covers the settings that will actually run.

Run `python -m my_big_brother doctor` to check the common setup.
A passing diagnostic does not prove a source format, Agent login or successful
review. Generic preparation and publication require no Codex installation.

## 4. Offer and verify optional collectors

### Vim and Neovim

Offer [session-recorder.vim](https://github.com/functoreality/session-recorder.vim)
when the environment check indicates relevant use. Explain that it records
original text, saved diffs, paths and cursor-line context. Ask whether to
install it, edit the active Vim/Neovim configuration and enable its input.
If the user declines, skip those changes and leave this source disabled
unless they explicitly choose existing records instead.

With consent, read the plugin's current README and [VIM.md](docs/VIM.md).
Back up the active configuration, use the existing plugin manager and install
the whole repository. For vim-plug, add inside the existing plugin block:

```vim
Plug 'functoreality/session-recorder.vim'
```

Adapt the declaration for another manager or Neovim Lua configuration.
Do not replace the entire vimrc or assume a fixed configuration path.
Use the shared raw-log locator. No extra path variable is normally needed.
An existing `record_dir` override bypasses shared discovery; migrate it only
with consent or explicitly configure a compatible legacy reader path.
Preserve exclusions and specify the intended native Python when needed.

Ask the user to restart their editor, then check `:RecorderStatus`.
Test a disposable file by opening, changing, saving and exiting normally.
Verify its manifest, original snapshot and diff under the shared raw root,
then enable `sources.vim` and prepare a date containing that closed session.
An open session may have no final manifest. Do not close unsaved user work.

### Bash

Offer the bundled recorder only when the user wants future shell activity
recorded. With consent, follow [BASH.md](docs/BASH.md), back up the active
`.bashrc` and preserve prompt hooks, traps and history settings.
It records the first simple command and the line's status independently of
history exclusions, so leading spaces or HISTIGNORE do not hide commands.
Use redaction and exclusions as appropriate. Do not source it in a different
shell or treat it as a PowerShell recorder.

### Screenshots

The optional reader consumes existing captures and uses Pillow for contact
sheets. Follow [INPUT-SOURCES.md](docs/INPUT-SOURCES.md). If captures are not
already available, explain that a portable collector is not bundled. Any
local capture setup needs the user's explicit choice and its own verification.
Do not start screen recording merely by enabling the reader.

## 5. Verify preparation before analysis

Choose a completed date with known records:

```sh
python -m my_big_brother analyze --date 2026-01-15
```

This prepares a work ticket and `prompt_path`, not an Agent launch.
`prepare` is also available for direct preparation. Check the run's manifest,
context, timestamps, source counts/gaps and resolved paths. The half-open
logical-day window may span two natural-date directories.
Omitting `--date` selects the last closed day. Use an explicit current date
only for an honest partial review. `--snapshot-end` accepts a timestamp with
UTC offset for a fixed cutoff.

## 6. Verify one complete review with the chosen Agent

Choose one verification route:

- To consume the exact ticket from step 5 in an existing Agent session, give
  that Agent the exact ticket, resolved checkout/Python/environment and its
  `prompt_path`. Start at **Review a prepared run** in the
  shared [AUTOMATION.md](tasks/daily-review/AUTOMATION.md). Do not prepare a
  second run by following the earlier **Prepare work** section again.
  If the installing Agent is the chosen executor, it can do this itself.
- To test an unattended entry, give it the resolved installation, Python,
  environment and explicit test date. It follows AUTOMATION.md from the start
  and obtains its own fresh ticket. Inspect that run, not the earlier ticket.

The Agent reads evidence, follows TASK/INPUTS/OUTPUTS/WORKFLOW, writes staged
reports and the exact completion receipt, then calls `finish`.
If `finish` returns `actions-pending`, that same Agent reads the returned
action prompt, completes authorized operations, writes the action receipt
and calls `finish` again. Never declare success from exit code alone or while
post-review work is pending. Do not bypass publication conflict checks.

For the bundled external Codex entry, a one-off test is:

```sh
python -m my_big_brother.analyzers.codex --date 2026-01-15
```

This can consume account quota and send selected evidence to the Agent's
configured provider. It starts one Agent, which executes the common workflow
and its configured post-review itself. It also calls `begin-automation` and
`complete-automation` to plan and verify the invocation. The startup entry's
`agent-exited` status only means that process exited successfully. Inspect
`automation-result.json` in the returned `launch_dir`, its completed status,
receipts, reports and actual coverage. Without usable evidence, preserve an
honest empty result. Required-source failures remain blocked.

For another Agent, use its native task or create a local one-shot startup
runner with its supported execution interface. The runner launches that Agent
with the same automation task, paths and date/lookback instructions.
Use its version's supported file and shell tools. Confirm that it can read
the checkout, selected inputs and personal references, and write state,
results and explicitly configured post-review targets. A workspace selection
alone may not grant those external paths. Identify the effective permission
scope, including settings that affect other
tasks. Prefer narrow grants and explain broader settings before asking the
user to choose them. Preserve product controls unless that change is explicitly
chosen. Test that unattended execution does not pause for an approval nobody
will answer.
Keep the runner limited to one Agent launch and necessary execution settings
and diagnostics. Put date planning, input preparation, queue handling,
publication and completion checks inside the executing Agent's task.
Never loop over dates by launching additional Agents or retry with another
Agent automatically. It must not duplicate semantic analysis or start a
second harness from inside the common scripts. Preserve scope, timeouts,
failure diagnostics and checked
completion. See [EXTENDING.md](docs/EXTENDING.md).
If the Agent cannot execute unattended on this machine, report that specific
limitation and the missing setup. Do not falsely mark automation installed.

## 7. Install one chosen trigger

After one complete review works, choose the desired daily time and timezone
using the agreed logical-day boundary. If that boundary changes, repeat the
review test first. Prefer the chosen Agent's native local scheduler when it
meets the checks below.
Start with [native-agent-task.md](examples/scheduling/native-agent-task.md).
Replace its placeholders and save the resolved task in the chosen scheduler
or an explicitly selected personal task file. Supply the actual checkout,
Python, account, configuration-discovery environment, expected personal paths,
lookback, timezone and result destination. Future runs must not depend on
this installation conversation. Schedule the analysis task, not INSTALLATION.md.
Keep a new job disabled or paused for testing when the product supports it.
If job creation enables recurrence immediately, first verify an equivalent
one-shot task in that same execution environment, then obtain the scheduling
choice before creation. If there is no disabled-job test or equivalent one-shot
route, do not enable recurrence before verification. Report that limitation and
choose another suitable route. A recurring job is not a harmless preview.
If task creation requires a UI you cannot operate, give the user the resolved
prompt and required fields, and mark that manual step pending. Do not invent
an undocumented scheduling API or claim it was installed.
A native scheduled Agent follows this task directly without a Codex launcher
or a fabricated Codex launch context. `begin-automation` and
`complete-automation` apply only when an actual launcher context is supplied.
Do not add an OS timer for the same task by default.

If it has no suitable native scheduler, implement the local startup runner
from step 6 and invoke it from cron on Linux, launchd on macOS, or Task
Scheduler on Windows. Consult installed help and official documentation when
uncertain about starting that Agent. Preserve authentication and use absolute
paths, the correct account, a stable working directory and separate logs.

For Codex, the included examples invoke the external entry:

```sh
python -m my_big_brother.analyzers.codex --max-days 7
```

The Agent itself calls common `due` to prepare the bounded catch-up tickets,
then reviews them oldest first and resumes pending actions.
Calling common `due` alone is not a scheduled analysis: it returns work.
The lookback is bounded and does not promise recovery of all historical gaps.
Read [SCHEDULING.md](docs/SCHEDULING.md) and test the actual trigger environment.
OS templates are examples. Use the actual native job test/manual-run control
or resolved OS entry to check the scheduled environment. A native scheduler may
use a different working directory, container, toolset or permission policy from
this interactive session. Confirm `paths` selects the same configuration and
state, inputs remain readable, and required writes complete without an
unexpected approval wait. Interactive verification alone is not a test of
the scheduled environment.

Keep each trigger to one executing Agent. Do not configure an Agent-target
notification, handoff, or job retry that automatically starts another Agent
for this same firing. Human-facing status delivery and local diagnostics are
sufficient. Provider/API request retries within the same executing Agent are
distinct from scheduler retries that start a fresh Agent run.
If the product cannot provide this execution mode, report that
constraint instead of claiming the requirement is met. A native scheduler
that cannot meet these checks is unsuitable for this setup. Use the chosen
Agent's supported one-shot entry with an OS timer if it can meet them instead.
If neither route works, retain the working one-off installation and report
the missing capability without substituting another Agent.

Verify the common `finish` results, receipts and published files after the
scheduled test. A scheduler's success badge can mean only that its Agent turn
ended, even if the response describes a blocker. `actions-pending`, `blocked`
and failed work are not completed reviews. An honest `empty` result is not an
analyzed day. Without a launch context, use the final results returned by the
common commands instead of expecting `automation-result.json`.
macOS and Windows execution remain unverified by this repository.

## 8. Handoff and maintenance

Report installation and personal paths, chosen executor, enabled records and
outputs, collector decisions, any actual schedule and one reviewed report.
Distinguish available mechanisms from untested runtime behavior.
Explain how retained outputs support weekly summaries and other conversations.

Back up configuration, results and completion state. Moving raw logs requires
pausing collectors, moving records, updating the locator and restarting writers.
Moving results needs only its own configuration update while reviews are stopped.
Do not delete active records. This release does not automatically clean raw
logs or derived materials. Do not replace existing user automation without
an explicit cutover choice.
