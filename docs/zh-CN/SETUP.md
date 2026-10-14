# 安装与设置

[English](../SETUP.md) | 简体中文

把 [INSTALLATION.md](../../INSTALLATION.md) 交给能操作你电脑的 Agent。
它是共享的英文安装指南。
告诉 Agent 你希望读取哪些历史、报告使用什么语言，
以及是否需要每日定时运行或可选 Bash 记录。

## 环境要求

- Python 3，推荐 3.11 或更新版本。旧版本未经验证，不保证兼容。
  核心程序没有第三方依赖。
- 将本仓库克隆到一个稳定的目录。
- 使用 Codex 或受支持的 OpenCode SQLite 历史作为输入。Bash 是可选的。
- 内置无人值守启动器需要可用且已认证的 Codex CLI。
  其他有相应能力的 Agent 也可以自己执行 prepare/task/finish 流程。

如果所选 Python 3 解释器对应的命令是 `python3`，请用它替代 `python`。
在克隆的仓库中运行：

```sh
python -m my_big_brother init --sources codex
python -m my_big_brother paths
python -m my_big_brother doctor
```

使用 `--sources codex,opencode` 可以读取两种原生历史。
初始化不会安装采集钩子或定时任务，并会保留已有设置。
`--sources` 仅用于首次初始化。
已有安装请编辑个人配置来修改输入源。
不带选项运行 `init` 可以补齐缺少的文件，不替换已有设置。
`doctor` 检查通用配置和路径，但不能证明 Agent 身份认证或输入格式一定兼容。
没有 Codex 可执行文件，也不妨碍其他 Agent 使用 `prepare` 和 `finish`。

## 配置个人安装

`paths` 显示 `config.json`、`raw-logs-path.txt`、结果和运行状态的位置。
它们都位于仓库之外。
编辑生成的 JSON 配置，可以选择输入源、输出类型、报告语言，
或自定义绝对路径 `results_root`。

需要中文报告时，把已有的语言字段改为：

```json
"language": "zh-CN"
```

这只是 `config.json` 中的一个字段，不是整个文件的替代内容。
默认语言仍是英文。
此设置影响生成的文字，不改变 JSON 字段名、命令或安装的任务指令语言。

采集器只共享 `raw-logs-path.txt` 中的原始日志绝对路径。
不要在这个文件中填写结果路径或 JSON 语法。
读取 Agent 原生历史不需要新的采集插件。

可选 Vim、截图适配器的记录格式与回看资产见[输入来源](INPUT-SOURCES.md)。

## 验证首次复盘

选择已启用历史中确实存在活动的日期：

```sh
python -m my_big_brother prepare --date 2026-01-15
```

检查返回的记录数和输入源缺口。
准备操作创建一个运行目录，不启动 Agent，也不发布报告。

使用内置 Codex 启动器时，运行：

```sh
python -m my_big_brother.analyzers.codex --date 2026-01-15
```

这会使用已安装的 Codex 账号，可能消耗额度。
选中的证据可能发送给该 Agent 配置的模型服务商。
没有可用证据时，由已经启动的 Agent 记录空结果。
入口返回的 `agent-exited` 只表示进程退出。
请检查返回的 `launch_dir` 中由 Agent 写出的 `automation-result.json`，
再查看生成文件及其中说明的限制。

也可以让当前 Agent 按准备好的运行上下文，遵循
[TASK.md](../../tasks/daily-review/TASK.md)。
它写好暂存报告和完成回执后，运行：

```sh
python -m my_big_brother finish --run-dir /absolute/path/to/the/run
```

省略 `--date` 时，复盘最近一个已结束的分析日。
自定义 `day_start_hour` 会改变分析日的边界。
输出可包括工作日志、Markdown 和 JSON 时间使用记录、每日洞察和耗时样本。
每种输出可以单独选择。

共享的[自动化任务](../../tasks/daily-review/AUTOMATION.md)也说明了待办后操作：
由同一个 Agent 读取操作提示词、完成任务、写好准确回执，再调用 `finish`。
通用 `analyze` 和 `due` 返回工作票据，不会启动 Agent。
Codex 使用上面的外部入口，其他 Agent 可以使用原生任务或本地启动脚本。
独立编辑器插件的接入见[Vim/Neovim 记录](VIM.md)。

## 启用周期性复盘

首次复盘正常完成后，与负责安装的 Agent 选择调度方式。
如果 Agent 提供原生的本地调度功能，优先使用它。
只有命令行工具时，可以使用 cron、launchd 或 Windows 任务计划程序。
两种方式及示例见[定时运行](SCHEDULING.md)。

本项目没有自动调度器安装程序，`init` 默认不启用定时运行。
项目提供复盘命令和补做逻辑，由你选择的调度器启动。
在依赖定时运行之前，请在对应的用户账号和环境中测试一次实际调度动作。

Bash 记录是另一项独立的可选功能。
修改 shell 启动文件前，先阅读 [BASH.md](BASH.md)。
应备份已发布结果和配置。
本版本不会自动清理原始日志和私有摘录。
