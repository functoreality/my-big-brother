# My Big Brother

[English](README.md) | 简体中文

**老大哥在看着你！**

**就在你的电脑上！**

**每天！**

顺便……为你的下次周报记点笔记。

认识一下你的 AI 老大哥：他回顾你留下的工作记录，
帮你想起做过什么、发生了什么变化，还有哪些事情需要留意。

My Big Brother 是一本 AI 工作日记，
把本地活动日志变成每日复盘和可以复用的背景信息。
由你选择允许它读取哪些历史记录。
在这个版本里，“看着你”指的是回顾这些记录，也可以选择启用 Bash 日志。
它也可以读取你明确启用的编辑器记录和截图。
安装本项目不会自动启动截图，也不会观察所有应用。

安装之前，可以先看看一次真实 Agent 运行生成的
[合成示例](examples/synthetic/README.zh-CN.md)。

My Big Brother 准备本地证据，由 Agent 主导复盘。
保存的记录可用于之后的周报、项目总结，或作为其他 Agent 的背景信息。
首个版本是普通的本地仓库，不包含常驻服务、Skill 或 MCP server。

## 支持的功能

- 输入：Codex 原生会话文件和受支持的 OpenCode SQLite 历史记录。
  仓库提供可选 Bash 采集器，也提供 Vim/Neovim 记录和截图的可选读取器。
  编辑器和截图采集器需单独安装，截图联系表需要可选依赖 Pillow。
- 无人值守分析：使用 Codex，默认沿用你已安装的登录身份和默认模型，
  也可以明确配置模型。
- 交互式分析：当前 Agent 可以准备输入，遵循相同的 Markdown 任务说明，
  并提交结果，不必再启动另一个 Agent。
- 输出：工作日志、Markdown 和 JSON 格式的时间使用记录、每日洞察，
  以及保守的耗时样本。每种输出都可以单独启用。
- 个人配置档案：明确指定方法笔记和参考资料、自定义输出位置与校验结构，
  以及单独限定权限的复盘后任务。

输入源和无人值守分析器是两个独立选择。
你可以读取 OpenCode 历史，由 Codex 做每日复盘。
`analyzer` 配置不会限制你用哪个 Agent 查询已有结果。

零散的 AI 会话无法重建你在电脑前做过的全部事情。
报告会说明证据覆盖范围，区分已记录的工作、推断的活动和未知的人类投入。
任务经过的时间不会直接视为专注工作时间。
不支持 OpenCode 较早的目录式 JSON 存储。
输入格式错误会报告为证据缺口，不会悄悄当作当天没有工作。

## 开始使用

把 [INSTALLATION.md](INSTALLATION.md) 交给能操作你电脑的 Agent。
其中说明了安装、检查、首次复盘和可选的定时运行。
需要 Python 3.11 或更新版本，核心程序只使用标准库。
内置无人值守启动器还需要可用的 Codex CLI。
面向用户的操作说明见[安装与设置](docs/zh-CN/SETUP.md)。
文档语言和报告语言是独立的：在个人 `config.json` 中把 `language`
设置为 `zh-CN`，即可请求生成中文报告。

在本仓库目录中运行：

```sh
python -m my_big_brother init --sources codex
python -m my_big_brother doctor
python -m my_big_brother analyze --date 2026-01-15
```

`--sources` 用于首次初始化。
已有安装请编辑个人配置来修改输入源，
或不带选项运行 `init`，在保留设置的同时补齐缺少的文件。

选择实际存在记录的日期。
分析器使用你的 Agent 账号，可能消耗额度。
个人数据写在安装目录之外。
执行任务的 Agent 可能根据自身设置，把选中的证据发送给配置的模型服务商。
使用 `--sources codex,opencode` 可以同时读取两种历史，
也可以编辑生成的个人配置，启用需要的输入源。

如果希望在当前 Agent 会话中复盘，运行：

```sh
python -m my_big_brother prepare --date 2026-01-15
```

把返回的运行目录和
[daily-review/TASK.md](tasks/daily-review/TASK.md) 交给当前 Agent。
它写好暂存输出和完成回执后，校验并发布：

```sh
python -m my_big_brother finish --run-dir /absolute/path/to/the/run
```

对于 Codex CLI，定时补做使用同样的复盘流程：

```sh
python -m my_big_brother due --max-days 7
```

它检查指定回看范围内已经结束的分析日，从最早的一天开始，
跳过成功的复盘，失败的日期可在之后再次调用时重试。
没有可用记录的日期会跳过，不会标记为已分析。
这个命令运行一次就退出，需要调度器周期性调用。
定时运行是可选功能，默认不安装。

如果 Agent 提供原生的本地调度功能，优先使用它。
它可以自己执行 prepare/task/finish 流程，
也可以调用 `due`，继续让 Codex 担任分析器。
如果只使用命令行工具，可以在 Linux 上用 cron，macOS 上用 launchd，
Windows 上用任务计划程序。
选择方式、配置示例和当前集成限制见[定时运行](docs/zh-CN/SCHEDULING.md)。

## 个人文件

运行 `python -m my_big_brother paths`，查看配置、原始日志、结果和运行状态的位置。
安装目录可以移动或更新，个人历史无需存入 Git。

- `config.json` 选择输入源、输出、语言和分析器。
- 可选的 `local_profile` 指定个人规则、允许读取的资料、输出路径、
  校验器和复盘后操作。
- `raw-logs-path.txt` 保存采集器共享的唯一绝对路径。
- 结果保存在 `records/` 下稳定的按日期命名的路径中。
- 运行状态在仓库之外保存索引、摘录、草稿、诊断信息和完成历史。

Agent 原生历史仍保存在原来的位置。
MVP 不会自动删除原始日志或运行材料，请单独查看和管理磁盘占用。
摘录可能包含私有会话文本。
可选 Bash 采集器的说明见 [BASH.md](docs/zh-CN/BASH.md)。

其他 Agent 可以通过 `paths` 找到结果，只读取相关日期的报告。
可以添加一条全局指令：
“需要查询我的工作记录时，请查看安装在 <安装路径> 的 My Big Brother，
并用它的 paths 命令查找文件。”
安装这个仓库不会自动把它提供给所有 Agent。

## 范围与扩展

可移植核心面向 Linux、macOS 和 Windows。
端到端运行已在 Linux 验证。
macOS 和 Windows 上的完整运行及定时动作仍需在对应系统上验证。
Bash 支持适用于 Bash 环境，包括作为独立环境的 WSL，不记录 PowerShell。

目前没有内置周报生成器或标准知识更新器。
你的 Agent 可以总结已有的每日文件。
明确配置的复盘后任务可以维护选定的本地知识或累计记录，
在日报通过校验并发布后执行，并有独立的完成与重试状态。
配置方式和边界见[个人配置档案](docs/zh-CN/PROFILES.md)。
采集器、输入适配器、分析任务和分析器启动器之间的边界见
[扩展指南](docs/zh-CN/EXTENDING.md)。

## 文档与测试

- [安装与设置](docs/zh-CN/SETUP.md)和[提供给 Agent 的安装说明](INSTALLATION.md)。
- [定时运行](docs/zh-CN/SCHEDULING.md)和[可选 Bash 记录](docs/zh-CN/BASH.md)。
- [架构](docs/zh-CN/ARCHITECTURE.md)和[扩展指南](docs/zh-CN/EXTENDING.md)。
- [输入来源](docs/zh-CN/INPUT-SOURCES.md)和[个人配置档案](docs/zh-CN/PROFILES.md)。
- [中英文示例](examples/synthetic/README.zh-CN.md)。

面向用户的文档和示例提供英文及简体中文版本。
`INSTALLATION.md`、`AGENTS.md` 和 `tasks/` 保持英文，作为 Agent 共享的指令。
JSON 字段名和命令名在所有语言中相同。

在仓库目录运行隔离测试：

```sh
python -m unittest discover -s tests -v
```

在 Linux 上，`python3 tests/smoke.py` 会准备一个隔离的虚构工作日。
添加 `--run-analyzer` 会执行真实 Codex 分析，并把输出发布到隔离的测试目录。
这一步是可选的，使用已安装的账号并消耗额度。
它不使用个人历史，也不安装调度器。
