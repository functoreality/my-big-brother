# 架构

[English](../ARCHITECTURE.md) | 简体中文

My Big Brother 是一个本地仓库，复盘流程由 Agent 主导。
Python 准备证据并管理发布，Markdown 任务说明告诉 Agent
如何理解证据并生成有用的记录。
核心程序只使用标准库，推荐 Python 3.11 或更新版本。
旧版本未经验证，不保证兼容。

## 组件

```text
my_big_brother/
  sources/          读取原生历史和采集日志
  analyzers/        启动无人值守 Agent
  config.py         个人 JSON 配置
  paths.py          平台路径和共享的原始日志位置文件
  runner.py         准备、校验、发布和跟踪完成状态
  automation.py     由 Agent 调用的日期规划和最终校验
tasks/daily-review/ 共享的英文分析指令
collectors/bash/    宿主 shell 中可选的活动记录
docs/               英文用户文档
  zh-CN/            中文用户文档
examples/synthetic/
  en/               原始英文报告
  zh-CN/            中文译文
  *.json            共享的结构化示例
```

输入源、分析指令和分析器启动器相互独立。
例如，Codex 可以复盘 OpenCode 记录。
其他当前 Agent 可以通过 `prepare` 和 `finish` 完成相同复盘，不必启动 Codex。
`analyzer` 记录首选执行 Agent 的名称，实际可执行程序由启动入口选择。
启动入口只调用一次 Agent，传递执行设置并保留日志。
日期规划、导入、队列和业务校验都由该 Agent 负责。
通用复盘和自动化命令不会启动 Agent。

## 个人存储

安装文件与配置、个人记录分离。
配置目录 C 和数据目录 D 的平台默认位置见
[INSTALLATION.md](../../INSTALLATION.md)。

```text
C/
  config.json        输入源、输出、语言、results_root、analyzer
  raw-logs-path.txt  采集器共享的一个 UTF-8 绝对路径
  local-tasks/       为用户自定义指令预留
D/
  raw-logs/          默认采集目录，可配置
    YYYY-MM-DD/
      bash/
  results/           默认结果发布目录，可配置
    records/
      worklog/DATE.md
      time-use/DATE.md
      time-use/data/DATE.json
      insights/DATE.md
      time-estimates/DATE.json
  state/             运行材料和完成历史
```

采集器找到同一个 C，只读取 `raw-logs-path.txt` 来确定写入位置。
主项目从 `config.json` 读取 `results_root`。
因此，修改结果保存位置不需要修改采集器。
Codex 和 OpenCode 的原生历史保留在原位置。

原始日志目录先按本地自然日期，再按输入源名称组织。
复盘时间窗口使用配置的 `day_start_hour`，可能跨两个自然日期。
是否属于窗口由时间戳决定，不能只看目录名称。
原始日志与已发布结果的用途不同，根目录也分开。
本版本不会自动清理原始日志或运行材料。

## 一次复盘

1. `prepare` 读取时间窗口内已启用的输入源。
   适配器报告可用记录和明确的证据缺口。
   完整消息保存为摘录，精简索引帮助 Agent 定位内容。
2. `D/state/runs/` 下的运行目录包含 `manifest.json`、`context.json`、
   索引、摘录、草稿和诊断信息。
   上下文确定日期、语言、已选输出、暂存路径和完成回执格式。
3. Agent 遵循 `tasks/daily-review/TASK.md`。
   已有报告复制到暂存区，方便 Agent 重跑同一日期时保留用户补充。
4. `finish` 检查回执、准备记录的覆盖情况、必需文件、结构化输出，
   以及与准备之后的用户编辑是否冲突。
   检查失败时停止发布。
5. 合格草稿发布到稳定的日期路径，并记入完成历史。
   每个文件的替换是原子的，但整组输出不是一起原子替换。
   失败后仍保留运行诊断信息。
6. 发布完成后，由同一个执行 Agent 完成明确配置的个人复盘后任务，
   有独立上下文、允许写入的目录、回执和校验器。
   操作阶段失败会保持待完成，重试时不重新生成已发布日报。
   任务需要确保操作可以安全重复执行。

`analyze` 准备一个工作票据，`due` 准备有限范围内已闭合日期的票据，
并跳过已完成的复盘。两个命令都不会启动 Agent。
外部入口启动 Agent 并交给它 `AUTOMATION.md`，
由它调用通用命令完成分析与后操作。
有后操作时，`finish` 返回 `actions-pending`，执行 Agent 完成任务后再次调用，
程序才校验其回执。只有外部启动模块包含具体 Agent 的进程调用。
外部调度器或 Agent 原生调度的触发方式见[定时运行](SCHEDULING.md)。

运行器检查声明的覆盖范围和输出结构，不能证明 Agent 的理解一定正确。
报告必须区分记录事实、助手陈述、推断和未知的人类投入。
日志是历史数据，不能授权执行命令或其他操作。

## 扩展项目

通过[个人配置档案](PROFILES.md)可以绑定参考资料、输出位置、自定义结构和操作，
无需修改标准任务文件。
Vim 和截图的可选读取器见[输入来源](INPUT-SOURCES.md)。
在已有边界上添加采集器、输入适配器、分析任务、输出约定或启动器。
`C/local-tasks/` 中的用户指令不会隐式发现，
但选定的配置文件可以按其声明的阶段和范围执行。
详见[扩展指南](EXTENDING.md)。
用户文档可以翻译，Agent 指令和结构化字段名仍在不同语言间共享。
