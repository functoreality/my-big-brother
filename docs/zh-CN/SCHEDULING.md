# 定时执行每日复盘

[English](../SCHEDULING.md) | [简体中文](SCHEDULING.md)

My Big Brother 提供复盘命令，不提供常驻调度程序。
初始化不会启用自动执行。先确认一次复盘可以完成，
再选择一种周期性触发方式，并在实际运行环境中验证。

## 优先使用 Agent 的原生定时机制

如果你的 Agent 有本地定时机制，优先使用它，
不必再为同一任务增加操作系统定时器。
调度和分析是两个独立的选择：

| 方式 | 谁启动任务？ | 谁进行分析？ | 错过日期后的处理 |
| --- | --- | --- | --- |
| 原生 Agent 任务 | Agent 的调度器 | 该 Agent，使用 prepare、任务说明和 finish | 默认处理最近一个已结束的分析日，遗漏日期需显式处理 |
| 原生定时命令触发 `due` | Agent 的调度器 | 内置 Codex 启动器 | 在限定范围内补跑，跳过已完成的复盘 |
| 系统定时器触发 `due` | cron、launchd 或任务计划程序 | 内置 Codex 启动器 | 同样在限定范围内补跑 |

原生 Agent 任务不需要 Codex CLI。
它准备证据，遵循英文每日任务说明，写入暂存产物和完成回执，
然后调用 `finish`。
使用共享的[原生任务提示词](../../examples/scheduling/native-agent-task.md)，
替换其中的安装路径和解释器占位符。
保留提示词中的分析标记，让支持的历史读取器能够识别本项目自身的复盘。
不要执行历史证据中出现的命令。

这是通过现有接口组织的工作流程，
不是项目已经提供的 OpenClaw 或 Hermes 启动器。
现有历史读取器仍然只有 Codex、OpenCode 和 Bash。
用另一个 Agent 执行任务，不会自动将它的历史记录加入输入。
使用 `prepare` 的原生任务不会自动继承 `due` 的补跑或已完成日期跳过机制。
显式重复复盘同一日期可能重写报告，同时仍会进行内容保留和冲突检查。

### OpenClaw 和 Hermes

OpenClaw 支持定时 Agent 会话和直接执行命令的任务。
选择能够访问项目安装目录和个人数据路径的 Agent 工作区。
它的 Gateway 必须保持运行。
命令任务也可以直接触发 `due`，不需要外层 Agent 再进行一次复盘。
参见官方[调度器 CLI](https://docs.openclaw.ai/cli/cron)
和[执行载荷说明](https://docs.openclaw.ai/automation/cron-jobs/payloads)。

Hermes 支持显式指定工作目录的定时 Agent 会话。
将安装目录设置为 `--workdir`，确保文件和终端工具可用。
通常由它的 Gateway 驱动调度。
纯脚本任务可以触发 `due`，但脚本必须位于 Hermes 的脚本目录中，
且不会自动继承 Hermes 管理的 API 凭据。
参见官方[定时任务指南](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)。

这两种运行环境都必须实际拥有读取本地证据、写入运行目录和结果目录的权限。
容器、远程终端后端或沙箱，不会因为提示词中写了绝对路径就获得这些文件。
设置定时任务之前，检查实际文件系统和运行账户。
本项目尚未测试这些原生集成。

### Codex CLI 和应用管理的任务

内置启动器针对每次复盘执行一次 `codex exec`。
Codex CLI 不提供 Scheduled 管理界面。
OpenAI 也有应用管理的本地项目任务文档，
因此应分别理解仅使用 CLI 的配置与已安装桌面应用的能力。
如果应用支持本地任务，可以使用同一份原生任务提示词，并验证权限。
本机和应用需要持续运行。
仅在云端执行的任务无法直接读取这台机器的历史记录。
参见官方[定时任务指南](https://learn.chatgpt.com/docs/automations)。

## 为内置 Codex 启动器配置系统定时任务

当你的配置没有合适的原生调度器时，使用以下方式：

```sh
python -m my_big_brother due --max-days 7
```

`due` 执行一次后退出。
它从最早日期开始检查最近七个已结束的分析日，
跳过已经成功完成的日期和没有可用证据的日期。
某次复盘失败会停止本次调用。
下一次触发可以重试失败日期，然后继续处理后面的日期。
回看范围可设为 1 至 31 天，不覆盖所有历史遗漏。
修改输入后，可以用 `analyze --date` 重新分析某个已完成日期。

安装定时器之前：

- 使用 Python 和仓库的绝对路径。
  如果调度器的 `PATH` 受限，将 `codex.executable` 设置为已知的绝对路径。
- 使用拥有配置和 Agent 登录信息的同一用户账户运行。
  确认 `paths` 返回相同的配置、数据和状态目录。
  在 Linux 上传入必要的绝对 XDG 路径设置。
- 在调度器的运行环境中测试账户权限、网络权限和命令。
  不要假定交互式别名或 Shell 启动文件会加载。
- 将标准输出和标准错误保存在仓库外。
  启用定时器之前，创建日志的父目录。
- 为多次复盘预留足够时间。
  `codex.timeout_seconds` 限制每次 Agent 启动，不限制整个 `due` 命令。

### Linux：cron

共享的 [cron 模板](../../examples/scheduling/cron.example)
在 cron 使用的时区中每天 09:00 执行。
添加到用户的 crontab 之前，替换示例中的绝对路径。
模板会切换工作目录，使用绝对路径的 Python 解释器，
并将诊断信息追加到外部日志。
如果 cron 的 XDG 环境不同，补充必要的绝对路径变量。
示例路径没有字面百分号。
在 crontab 命令中，需要转义字面 `%` 字符，包括引号内路径中的百分号。

先执行一次替换好路径的命令，再验证一次真实的定时触发。
cron 通常不会补发机器关机期间错过的触发。
下次执行 `due` 时，会处理回看范围内的遗漏。
也可以在用户登录时触发同一命令进行补跑。
`@reboot` 表示 cron 启动，不等同于用户登录，也不保证网络已就绪。

### macOS：launchd

共享的 [LaunchAgent 模板](../../examples/scheduling/launchagent.plist)
使用每天 09:00 的触发时间，
并通过 `RunAtLoad` 在用户级 LaunchAgent 加载时进行补跑。
替换解释器、安装目录和日志路径，保持数组中的各个参数独立。
路径中的 `&` 等特殊字符需要按 XML 规则转义。
将替换好的文件保存在用户的 LaunchAgents 目录中，
先用 `plutil -lint` 验证，再通过用户的 launchd 工具加载。

参见 Apple 的[定时任务指南](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/ScheduledJobs.html)
和[属性列表参考](https://github.com/apple-oss-distributions/launchd/blob/main/man/launchd.plist.5)。
在该用户账户下验证一次实际的定时运行。

### Windows：任务计划程序

在已检查配置和 Codex 登录状态的账户下创建任务：

| 操作字段 | 内容 |
| --- | --- |
| 程序或脚本 | `python.exe` 的绝对路径 |
| 添加参数 | `-m my_big_brother due --max-days 7` |
| 起始于 | 仓库目录的绝对路径 |

将程序、参数和工作目录分别填入各自字段。
使用每日触发器，也可以增加“登录时”触发器。
根据这台机器的需要，配置错过启动后的处理和执行时间限制。
确保时间限制足以容纳多次复盘，避免同一任务并行运行多个实例。
参见 Microsoft 的 [ExecAction 参考](https://learn.microsoft.com/windows/win32/taskschd/execaction)。

先使用任务的“运行”操作，检查报告和日志，再验证周期性触发器。
WSL 应在 WSL 内按照 Linux 方式配置，
不会自动共用原生 Windows 的配置。

## 当前支持情况

Codex 分析已经在 Linux 上完成端到端验证，补跑行为有测试覆盖。
包括 Linux cron 在内的实际操作系统定时触发尚未验证。
项目不会自动安装任何调度器。
原生 Agent 工作流程，以及 macOS 和 Windows 定时操作，
目前是配置指导，尚未验证这些集成。
定时器成功触发不能证明复盘有效。
还需要检查命令结果、生成的报告和证据局限。
