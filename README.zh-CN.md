# My Big Brother

[English](README.md) | 简体中文

**老大哥在看着你！**

**就在你的电脑上！**

**每天！**

顺便……为你的下次周报记点笔记。

认识一下你的 AI 老大哥：它每天回看你留下的工作记录，
串起证据，为明天留下有用的报告和背景信息。

理念很简单：本地活动记录形成每日复盘，每日复盘逐渐积累成关于你工作的记忆。
先让 Agent 每天无人值守地回顾工作，
再把这些产出用于判断、反思、计划和其他 Agent 会话，
让每份日报都能成为后续工作的材料。

由你选择输入、输出和分析 Agent。My Big Brother 准备证据并管理校验后的发布，
Agent 负责理解记录，也可以通过显式个人配置维护长期背景信息。
采集器按本机自然日期记录，工作日分界只由分析层使用。
这一职责边界见公共[需求说明](docs/zh-CN/REQUIREMENTS.md)。
采集器独立记录活动。安装本项目不会自动启动截图或记录所有软件。

可以先看看一次真实 Agent 运行生成的
[合成示例](examples/synthetic/README.zh-CN.md)。
本项目是普通的本地仓库，不包含常驻服务、Skill 或 MCP server。

## 输入

状态标记：**已支持**表示当前已提供，**计划中**表示拟继续推进的方向，
不承诺交付日期。读取器和采集器是不同的功能，下面分别说明。

- **Agent 对话记录：已支持** Codex 原生会话文件、受支持的 OpenCode SQLite 历史，
  以及 [WorkBuddy 项目会话](docs/zh-CN/WORKBUDDY.md)。
  **计划中**：更多 Agent 的历史读取器。
- **软件使用记录：已支持** Bash 记录及可选的内置采集器，
  以及由独立插件
  [session-recorder.vim](https://github.com/functoreality/session-recorder.vim)
  采集的 Vim/Neovim 会话。**计划中**：VS Code 和更多软件的采集器、读取器。
- **周期性屏幕截图：计划中**。尚未提供官方周期截图采集器与跨平台采集配置，
  因此不能直接开始持续采集。如果你已用自己的程序定期截图，
  当前读取器**已支持**处理这些已有截图，并通过可选依赖 Pillow 生成联系表。
  安装本项目或启用读取器都不会启动截图循环。
- **浏览器使用记录：计划中**采集和读取浏览活动记录。

欢迎通过 [issue](https://github.com/functoreality/my-big-brother/issues)
或 [PR](https://github.com/functoreality/my-big-brother/pulls) 增加更多输入。
支持的格式和覆盖边界见[输入来源](docs/zh-CN/INPUT-SOURCES.md)。

## 输出

**需个人配置**表示已有机制支持，但需要明确配置任务和目标位置，
不是默认给所有用户启用的标准输出。

- **每日记录：已支持**工作日志，以及 Markdown 和 JSON 格式的时间使用记录。
  保留成果、证据缺口和未知的人类投入。
- **反思与计划：已支持**每日洞察和保守的耗时样本。
  每种标准输出都可以单独启用。
- **长期理解：已支持**可选的用户模型和机器背景输出，
  默认直接保存在 `memory/`。同一个每日分析 Agent 维护有依据的用户偏好，
  以及已知的文件、目录和来源位置。个人配置可以重定向到已有文件。
  见[长期知识输出](docs/zh-CN/KNOWLEDGE.md)。
  **需个人配置**：额外的项目知识和操作。
- **后续操作：需个人配置**维护指定本地文件和累计记录。
  通知任务可以配合自己的发送辅助程序和校验器实现。
  **计划中**：可复用的操作预设。

欢迎通过 [issue](https://github.com/functoreality/my-big-brother/issues)
或 [PR](https://github.com/functoreality/my-big-brother/pulls) 提议更多输出。
[个人配置档案](docs/zh-CN/PROFILES.md)定义参考资料、输出位置、校验、写入范围和重试行为。

### 使用积累下来的产出

每日复盘积累的记录，还可以通过两种交互方式使用：

1. **总结工作：**在本项目目录启动 Agent，
   请它读取已发布的每日记录，生成周报或项目回顾。
   这是当前 Agent 对已有产出的总结，不是内置周报命令。
2. **在其他会话中调用背景信息：**告诉其他项目中的 Agent，
   My Big Brother 安装在哪里，让它用 `paths` 找到相关报告，
   以及你明确配置的用户或机器背景笔记。
   安装本项目不会自动向所有 Agent 共享文件，标准日报也不会生成完整的机器目录清单。

这两种方式都以保留的产出为基础，不替代每日复盘，也不必重新处理所有原始日志。

## 让你的 Agent 帮你安装

把下面这段消息复制给能够操作你电脑的 Agent：

```text
请帮我安装 https://github.com/functoreality/my-big-brother/blob/main/INSTALLATION.md
```

共享的 [INSTALLATION.md](INSTALLATION.md) 为安装 Agent 提供操作说明。
安装 Agent 也可以担任每日分析器。
仓库已提供 Codex 无人值守启动器、cron/launchd 示例和 Windows 任务计划配置说明。
其他 Agent 可以使用原生定时复盘，或由安装 Agent 准备自动化运行脚本。
分析 Agent 不限于内置启动器，但尚未打包的后端需要安装时完成接入与验证。
输入历史与分析 Agent 是两个独立选择。

Codex 入口可选 `exec` 或可接入的 `tmux` 交互会话，安装时由 Agent 说明并询问偏好。
tmux 模式需在 Linux、macOS 或 WSL 中安装 tmux，接入与完成检查见[定时运行](docs/zh-CN/SCHEDULING.md)。

推荐 Python 3.11 或更新版本，旧版本未经验证，不保证兼容。
核心只使用标准库，截图功能需要可选依赖 Pillow。
在个人 JSON 配置中将 `language` 设为 `"zh-CN"`，即可请求生成中文报告。

手动配置、命令和调度选项见[安装与设置](docs/zh-CN/SETUP.md)、
[定时运行](docs/zh-CN/SCHEDULING.md)和[Vim/Neovim 记录](docs/zh-CN/VIM.md)。
定时运行可选，初始化不会自动启用。

## 个人文件

运行 `python -m my_big_brother paths`，查看配置、原始日志、结果和运行状态的位置。
安装目录可以移动或更新，个人历史无需存入 Git。

- `config.json` 选择输入源、输出、语言和分析器。
- 可选的 `local_profile` 指定个人规则、允许读取的资料、输出路径、
  校验器和复盘后操作。
- 可选的 `raw-logs-path.txt` 跨应用共享一条采集根路径，采集器默认可独立运行。
  所有应用都不要求 `storage.json`，长期输出由 `results_root` 指定。采集按系统自然日期归档。
- `raw-logs/日期/` 保存记录、草稿、拼图、运行日志及全部逐日完成和恢复状态。
  旧日期无活动写入时可以直接删除，无需查看状态。
  日期目录之外只保留固定大小的 `raw-logs/.publish.lock` 协调锁。
- `memory/` 只保留选中的正式报告、第一层可见的用户和机器知识。
  无人值守复盘只处理最近一个已闭合逻辑日，更早日期须明确指定 `--date`，可以重建对应工作区。
- 日期与采集器约束见[需求](docs/zh-CN/REQUIREMENTS.md)和[存储说明](docs/zh-CN/STORAGE.md)。

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
Linux 已通过虚构记录的隔离端到端测试，包括同一 Agent 完成后操作。
macOS 和 Windows 上的完整运行及定时动作仍需在对应系统上验证。
Bash 支持适用于 Bash 环境，包括作为独立环境的 WSL，不记录 PowerShell。

目前没有内置周报生成器。可选的标准知识输出复用每日分析，
不额外启动 Agent，也不扫描整台机器。
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
- [手动清理与需要保留的状态](docs/zh-CN/CLEANUP.md)。
- [中英文示例](examples/synthetic/README.zh-CN.md)。

面向用户的文档和示例提供英文及简体中文版本。
`INSTALLATION.md`、`AGENTS.md` 和 `tasks/` 保持英文，作为 Agent 共享的指令。
JSON 字段名和命令名在所有语言中相同。

在仓库目录运行隔离测试：

```sh
python -m unittest discover -s tests -v
```

`python tests/smoke.py` 使用各平台配置路径准备隔离的虚构工作日。
原生 Windows 和 macOS 上的运行仍待验证。
添加 `--run-analyzer` 会执行真实 Codex 分析，并把输出发布到隔离的测试目录。
这一步是可选的，使用已安装的账号并消耗额度。
它不使用个人历史，也不安装调度器。
