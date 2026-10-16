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

If using the bundled Codex entry, ask which startup mode the user wants,
unless already specified:

- `exec` (default): a noninteractive run with captured logs and a timeout.
- `tmux`: a detached, interactive Codex TUI that the user can attach to, watch
  and message. It stays available after the review until the user closes it.

Record this as `codex.mode`. tmux mode needs tmux in a Linux, macOS or WSL
execution environment. Native Windows supports exec here. Do not silently
substitute exec if a requested tmux setup is unavailable. Both modes start
one Agent with the same task and permissions. tmux does not mean exec in a pane.
For tmux, check that the installed Codex supports `--no-daemon`. The interactive
entry uses it so this invocation does not reuse another server's environment.

## 2. Discover native histories and initialize personal locations

The installing Agent discovers native conversation sources and resolves their
paths. Do not ask the user to identify routine history directories or provide
a list of installed Agents before checking the intended computer and account.
Currently supported native readers are Codex sessions and OpenCode SQLite.

Inspect installed applications, known history locations, relevant environment
settings and application configuration. Start with this project's current path
defaults, honoring settings such as `CODEX_HOME` and `XDG_DATA_HOME`, and check
the actual location and readable format. Locations have defaults, but are not
one hardcoded path for every account or installation. Do not search unrelated
accounts or private folders. A usable history can be included even when its
Agent executable is no longer installed. Conversely, finding an executable
does not prove readable history exists.

On a first installation, configure detected supported native sources by default
and tell the user which sources and locations will feed daily reviews. The user
can exclude a source. Honor existing explicit inclusions, exclusions and path
settings instead of overriding them during reinstallation. Do not ask again
for every clearly identified native source. Ask for help only when a location
cannot be established, permissions prevent discovery, or multiple candidates
cannot be distinguished. If an installed supported Agent has no histories yet,
configure its known expected location and explain that no records exist yet.
Future records can use that configuration. Missing/unreadable histories remain
coverage gaps, never successful evidence. Unsupported formats are not added
merely because the application is installed.

Choose inputs independently of the executor. If its own format is unsupported,
use supported histories actually detected instead of silently substituting
Codex. Reading existing native histories does not install a new collector.
New Bash, Vim or screenshot recording remains a separate user choice.

Ask which additional collectors the user wants. Check for Vim/Neovim
executables, existing editor configuration or a recorder installation.
If these exist or the user regularly uses the editor, recommend the separate
plugin described in step 4 and ask whether to install it and update their
active configuration. Detection is not recording consent.

Initialize using the discovered, non-excluded source set. For example, when
Codex is the detected native source:

```sh
python -m my_big_brother init --sources codex
python -m my_big_brother paths
```

Use `--sources codex,opencode` when both native sources are detected and included.
These are examples, not a reason to enable an undetected Codex source.
This choice does not select the executing Agent. For existing Bash records,
`init --sources bash` is also a valid standalone starting point. Resolve that
source's actual path. Enable `bash`, `vim` or `screenshots` only for wanted
records, after checking existing compatible records or completing the chosen
collector setup. Initialization does not read histories or install hooks.

Use `--data-root` as a first-install shortcut selecting its raw-logs and memory,
`--day-start-hour` for its analysis-only working-day boundary, and `--results-root` for
an optional permanent output root.
The shortcut writes the locator and `results_root`, without a separate
persistent data-root setting. See [Storage](docs/STORAGE.md).

Defaults use configuration directory C and data directory D:

| System | Configuration directory C | Default data directory D |
| --- | --- | --- |
| Linux | `$XDG_CONFIG_HOME/my-big-brother` or `~/.config/my-big-brother` | `$XDG_DATA_HOME/my-big-brother` or `~/.local/share/my-big-brother` |
| macOS | `~/Library/Application Support/my-big-brother/configs` | `~/Library/Application Support/my-big-brother/data` |
| Windows | `%LOCALAPPDATA%\my-big-brother\configs` | `%LOCALAPPDATA%\my-big-brother\data` |

Linux XDG values must be absolute. GUI editors, the installing Agent and
scheduled runs must discover the same C and D under the intended account.
WSL and remote machines have their own environments.

`C/raw-logs-path.txt` can select a capture root with one UTF-8 absolute path.
The first-install `--data-root` shortcut writes it only when absent. Default
installation can use platform paths without this file. Bash, Vim, capture
helpers and analysis workspace storage use the same locator. Missing TXT means
platform defaults. Malformed TXT is an error. No application requires
`storage.json`, a storage identity or a permanent date registry. Permanent
outputs use configured `results_root`, defaulting to D/memory. Bash and Vim
work without application setup. Capture dates use each recording's creation
date. Bash and Vim keep their start-date paths across midnight and months of
uptime, while screenshots use their own capture dates.

All captures, analysis, completion markers, publication/action journals and
logs live in `raw-logs/YYYY-MM-DD/` and are deleted together. Only selected
formal reports and accumulated knowledge stay in permanent destinations.
One fixed-size `raw-logs/.publish.lock` coordinates publication without date
history. Native Agent histories remain with their applications.
Confirm every active collector follows these paths before promising date-only cleanup.
Formal outputs can use another writable filesystem or mount. Publication uses
ordinary file writes, so an interrupted write may require manual recovery from
the intact dated drafts. Explain this boundary and the recovery instructions in
[Storage](docs/STORAGE.md#publication-and-interrupted-writes).

## 3. Configure outputs and personal context

Read the generated JSON and keep it valid. Configure:

- `sources`: detected native records and any chosen additional records, with
  paths resolved by the installing Agent. Optional sources can
  remain visibly unavailable. A source marked `required` blocks publication
  if it is unavailable.
- `outputs`: selected `worklog`, `time-use`, `insights`, `time-estimates`,
  and optional cumulative `user-model` and `machine-context`.
  See [KNOWLEDGE.md](docs/KNOWLEDGE.md) for default paths, evidence rules and
  simple profile redirection to existing knowledge files.
- `language`, `day_start_hour` and an absolute `results_root` outside Git.
- `analyzer`: the chosen Agent's name, describing the installation's executor.
  The startup command or native task selects the actual executable. This
  field does not cause the core to launch that Agent.
- `local_profile`: optional personal task rules, read-only references,
  output bindings, schema validators and scoped post-review operations.
- `codex`: startup options only if using the bundled Codex entry, including
  `mode: "exec"` or `mode: "tmux"`. `timeout_seconds` applies to exec, not the
  retained interactive tmux session.
  Optional `working_directory` selects an existing absolute workspace directory.
  It becomes the Agent's working directory and writable main workspace, and
  can change which project instructions and settings Codex loads. Use this
  when personal tasks expect an existing workspace. Otherwise omit it to keep
  the dated launch directory as the default. Do not select the checkout or
  configuration directory. Keep prompts, logs and scratch files in the dated
  run even when the Agent starts elsewhere.

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
The plugin resolves `record_dir`, then the one-path UTF-8 file
`C/raw-logs-path.txt`, then the platform data directory's `raw-logs` at startup.
For a custom data root, configure that TXT to contain the same `raw-logs` path
used by the enabled Vim source, unless an intentional `record_dir` overrides it.
It does not read `storage.json`, register dates or migrate previous records.
Preserve exclusions and specify the intended native Python when needed.

Ask the user to restart their editor, then check `:RecorderStatus`.
Test a disposable file by opening, changing, saving and exiting normally.
Verify its manifest, original snapshot and diff under the shared raw-log directory,
then enable `sources.vim` and prepare a date containing that closed session.
An open session may have no final manifest. Do not close unsaved user work.

### Bash

Offer the bundled recorder only when the user wants future shell activity
recorded. With consent, follow [BASH.md](docs/BASH.md), back up the active
`.bashrc` and preserve prompt hooks, traps and native history contents.
It records complete input and session boundaries, including repeated input,
leading-space input and HISTIGNORE matches. The native history list keeps its
original filtering rules. Zero history size and disabled history-file saving
do not stop JSONL capture. Explain that history exclusions no longer provide
recorder privacy. Use `MBB_BASH_RECORDING=0` to pause recording.
The unresolved `set +o history` case has no command capture. Do not promise
full coverage for that setup. A full history list can be renumbered, affecting
numeric expansion such as `!123`, as documented in BASH.md. Do not enable it
for users requiring stable numbers. Keep the existing redaction rule.
Do not source it in a different shell or treat it as a PowerShell recorder.

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
logical-day window selects records by actual time. Bash and Vim discovery
searches all retained start-date folders, not just the window's dates.
Screenshot discovery uses the capture dates intersecting the window.
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
`complete-automation` to plan and verify the invocation. In exec mode, the
startup entry's `agent-exited` status only means that its process exited
successfully. Inspect
`automation-result.json` in the returned `launch_dir`, its completed status,
receipts, reports and actual coverage. Without usable evidence, preserve an
honest empty result. Required-source failures remain blocked.

In tmux mode, the entry returns `session-started` with `session_name` and an
attach command. It returns before analysis finishes. Attach to that exact
session, verify a real interactive TUI accepts input, and check the same
`automation-result.json` after the Agent completes its work. Detaching must
leave it running. The session remains open for user follow-up after completion.
Terminal diagnostics stay under that invocation's dated `logs/`. The exec
process timeout does not kill a retained TUI. Never start another Agent merely
to provide interaction or check business completion.

For another Agent, use its native task or create a local one-shot startup
runner with its supported execution interface. The runner launches that Agent
with the same automation task, paths and optional explicit-date instructions.
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
latest-closed-day policy, timezone and result destination. Future runs must not
depend on this installation conversation. Schedule the analysis task, not INSTALLATION.md.
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
python -m my_big_brother.analyzers.codex
```

The Agent itself calls common `plan-due` for only the latest closed logical
day, then prepares and finishes that date with `analyze --skip-completed`.
It completes post-review in the same run. Calling common `due` alone is not a
scheduled analysis: it returns work. Do not queue older dates or automatically
catch up missed dates. Older reruns require the user's explicit `--date`
request, which may create the workspace but cannot recover deleted evidence.
Read [SCHEDULING.md](docs/SCHEDULING.md) and test the actual trigger environment.
OS templates are examples. Use the actual native job test/manual-run control
or resolved OS entry to check the scheduled environment. A native scheduler may
use a different working directory, container, toolset or permission policy from
this interactive session. Confirm `paths` selects the same configuration,
raw-log and output paths, inputs remain readable, and required writes complete without an
unexpected approval wait. Interactive verification alone is not a test of
the scheduled environment.

Check the scheduled command's outer redirections too. A missing log parent
prevents the shell from entering the runner, so its failure notification cannot
run. Use existing dated diagnostics or prepare an authorized dated log inside
the local wrapper. Do not redirect to a removed permanent state directory.

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

Back up configuration and selected formal outputs. Completion and recovery
state are disposable with their dates. In-place relocation of
initialized storage is unsupported. The analysis boundary is configured
separately and never changes capture-date ownership.
Moving results needs only its own configuration update while reviews are stopped.
Do not delete active records. This release does not automatically clean captures
or derived materials. Do not replace existing user automation without
an explicit cutover choice.
