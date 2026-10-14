# 定时执行每日复盘

[English](../SCHEDULING.md) | [简体中文](SCHEDULING.md)

My Big Brother 提供复盘命令，不提供常驻调度程序。
初始化不会启用自动执行。先确认一次复盘可以完成，
再选择一种周期性触发方式，并在实际运行环境中验证。

## 选择分析 Agent 和触发方式

安装 Agent 也可以担任每日分析器。
原生本地定时机制满足安装检查时，优先使用它。
没有时，请它用自身支持的无人值守执行接口编写一次性启动脚本，
再由操作系统定时器调用。接口不清楚时，查询本机帮助和官方文档。
不要猜测启动参数，也不要未经用户选择就替换分析 Agent。
按 [INSTALLATION.md](../../INSTALLATION.md) 确认实际执行主机和定时权限，
校验业务完成，并避免原生重跑、修复或向 Agent 投递结果时自动开始另一个 Agent 回合。

| 方式 | 启动边界 | 执行分析的 Agent |
| --- | --- | --- |
| 原生定时 Agent 任务 | 所选 Agent 的调度器 | 该 Agent |
| 本地启动脚本加系统定时器 | 为所选 Agent 编写的入口 | 该 Agent |
| 内置 Codex 入口加系统定时器 | `python -m my_big_brother.analyzers.codex` | 一次 Codex 调用 |

各入口都使用相同的[自动化任务](../../tasks/daily-review/AUTOMATION.md)
和通用准备、发布命令。Agent 调用 `analyze` 或 `due` 得到工作票据，
逐项分析，然后调用 `finish`。有后操作时，由它自己执行返回的任务，
再调用 `finish`。通用命令不会启动 Agent，
产品特有的命令、登录、沙箱和超时设置只留在外部启动入口。
启动入口只调用一次 Agent，传递必要的执行设置并保留日志。
日期规划、输入导入、纠错队列、发布和最终业务校验都由该 Agent 执行。
不得按日期循环启动 Agent，也不得自动再启动 Agent 来重试。
Agent 可以自行决定通过自身工具委派子任务。
`analyze` 和 `due` 现在返回工作票据，不再启动 Codex，
旧定时命令需要改为外部启动入口。

使用共享的[原生任务提示词](../../examples/scheduling/native-agent-task.md)，
替换安装路径和 Python 占位符。其他 Agent 执行时无需安装 Codex。
补跑时选择有限回看范围，明确重跑某天时使用日期参数。
保留分析标记，让支持的读取器能识别本项目自身的复盘记录。
输入读取器独立存在，使用某个 Agent 不会自动增加其历史格式支持。

如果使用 OpenClaw 或 Hermes，请检查已安装版本是否提供适合的本地任务，
以及它能否访问安装目录和个人数据路径。
可按需参考 [OpenClaw 定时说明](https://docs.openclaw.ai/cli/cron)
或 [Hermes 定时说明](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/)。
这些是安装 Agent 的参考资料，不是已经打包或验证的集成。
其他 Agent 也可以按相同原则接入。

## 为内置 Codex 启动器配置系统定时任务

当你的配置没有合适的原生调度器时，使用以下方式：

```sh
python -m my_big_brother.analyzers.codex --max-days 7
```

这会启动一次 Codex 会话。它遵循共享任务，从通用 `due` 得到最近七个
已闭合日期的票据，按最早日期优先完成复盘和待办后操作。
已经完成的日期会跳过。空日不生成虚构报告，也不会标为完成，
后续仍可重新准备以发现迟到记录。
Agent 自己调用 `begin-automation` 和 `complete-automation`。
入口返回的 `agent-exited` 仅表示进程退出，
应检查返回的 `launch_dir` 中由 Agent 写出的 `automation-result.json`，
确认经过校验的复盘完成状态。失败或 blocked 不能通过该校验。
回看范围可设为 1 至 31 天。修改输入后，可用外部入口的 `--date` 完整重跑，
也可以请执行 Agent 处理通用 `analyze --date` 返回的明确日期票据。

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
  `codex.timeout_seconds` 限制整个 Agent 会话，包括所选日期和后操作。

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
下次启动时，会处理回看范围内的遗漏。
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
| 添加参数 | `-m my_big_brother.analyzers.codex --max-days 7` |
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

通用流程和外部入口有隔离测试。Linux 上使用虚构记录及个人后操作任务，
真实启动一次 Codex，完成五份报告和后操作回执。
这不代表生产安装或真实定时触发已经验证。
包括 Linux cron 在内的实际操作系统定时触发尚未验证。
项目不会自动安装任何调度器。
原生 Agent 工作流程，以及 macOS 和 Windows 定时操作，
目前是配置指导，尚未验证这些集成。
定时器成功触发不能证明复盘有效。
还需要检查命令结果、生成的报告和证据局限。
