# 架构

[English](../ARCHITECTURE.md) | 简体中文

日期与采集器约束见[需求说明](REQUIREMENTS.md)。

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
日期规划、导入和业务校验都由该 Agent 负责。
通用复盘和自动化命令不会启动 Agent。

## 个人存储

安装文件与配置、个人记录分离。
配置目录 C 和数据目录 D 的平台默认位置见
[INSTALLATION.md](../../INSTALLATION.md)。

```text
C/
  config.json
  readers/<source>/reader.py
  raw-logs-path.txt  可选的单路径原始日志位置文件
  local-tasks/
D/
  raw-logs/YYYY-MM-DD/
    bash/
    vim/
    screenshots/
    review.json
    _analysis/<run-id>/
      publication.json
      actions/
    _launches/<invocation-id>/
  memory/
    USER-MODEL.md
    MACHINE-CONTEXT.md
    records/YYYY-MM-DD/
```

采集器在创建记录时按本机自然日期归档，等价于 `date +%F`。
Bash 和 Vim 会话固定使用启动日期下的位置，不因跨午夜而轮转。
读取器查找全部保留的启动日期。
`C/raw-logs-path.txt` 选择原始日志位置，`results_root` 选择长期输出，默认为 D/memory。
所有应用都不要求 `storage.json`。
逐日完成状态、发布和后操作日志均在 `raw-logs/日期`，
旧日期无活动写入时可以直接删除，无需查看状态。
只有选中的正式输出和知识长期保留在 memory 或 profile 指定的位置。
固定大小的 `raw-logs/.publish.lock` 协调共享输出发布，不保留日期历史。
完整约定见[存储说明](STORAGE.md)。

## 一次复盘

1. `prepare` 读取时间窗口内已启用的输入源。
   适配器报告可用记录和明确的证据缺口。
   完整消息保存为摘录，精简索引帮助 Agent 定位内容。
2. `D/raw-logs/DATE/_analysis/` 下的运行目录包含 `manifest.json`、`context.json`、
   索引、摘录、草稿和诊断信息。
   上下文确定日期、语言、已选输出、暂存路径和完成回执格式。
3. Agent 遵循 `tasks/daily-review/TASK.md`。
   已有报告复制到暂存区，方便 Agent 重跑同一日期时保留用户补充。
4. `finish` 检查回执、准备记录的覆盖情况、必需文件、结构化输出，
   以及与准备之后的用户编辑是否冲突。
   检查失败时停止发布。
5. 合格草稿发布到稳定的日期路径，并写入日期目录的 `review.json`。
   发布通过普通文件写入完成，可跨具备写权限的文件系统或挂载点。
   失败可能留下部分正式内容，完整草稿保留供人工恢复，详见[存储](STORAGE.md)。
6. 发布完成后，同一个执行 Agent 先处理已启用的公开本地主动提醒，
   再执行可能配置的私人后操作，各自有独立上下文、写入目录、回执和校验器。
   新安装默认启用本地提醒，详见[本地主动提醒](NOTIFICATIONS.md)。
   操作阶段失败会保持待完成，重试时不重新生成已发布日报。
   任务需要确保操作可以安全重复执行。

`analyze` 准备一个工作票据。`plan-due` 和 `due` 只考虑最近一个已闭合逻辑日，
`due` 跳过仍保留完成标记的复盘。这些命令都不会启动 Agent。
更早日期须由用户明确指定 `--date` 重跑，不自动排队处理或补做历史日期。
外部入口启动 Agent 并交给它 `AUTOMATION.md`，
由它调用通用命令完成分析与后操作。
有后操作时，`finish` 返回 `actions-pending`，执行 Agent 完成任务后再次调用，
程序才校验其回执。只有外部启动模块包含具体 Agent 的进程调用。
外部调度器或 Agent 原生调度的触发方式见[定时运行](SCHEDULING.md)。

运行器检查声明的覆盖范围和输出结构，不能证明 Agent 的理解一定正确。
报告必须区分记录事实、助手陈述、推断和未知的人类投入。
日志是历史数据，不能授权执行命令或其他操作。

没有启用来源或全部来源不可用时返回 `blocked`，`--allow-empty` 不绕过此检查。
来源可读但窗口内零条记录时可返回 `empty`，不发布日报，也不证明用户没有工作。
`doctor` 检查配置与路径，不证明采集器已安装或 Agent 已通过身份认证。
应检查其警告和准备后的 manifest。

## 扩展项目

通过[个人配置档案](PROFILES.md)可以绑定参考资料、输出位置、自定义结构和操作，
无需修改标准任务文件。
Vim 和截图的可选读取器见[输入来源](INPUT-SOURCES.md)。
在已有边界上添加采集器、输入适配器、分析任务、输出约定或启动器。
`C/local-tasks/` 中的用户指令不会隐式发现，
但选定的配置文件可以按其声明的阶段和范围执行。
详见[扩展指南](EXTENDING.md)。
用户文档可以翻译，Agent 指令和结构化字段名仍在不同语言间共享。

个人来源实现可在源码目录外显式绑定，优先于同名官方实现且不静默回退。
所选文件摘要纳入日期内运行身份，详见[扩展说明](EXTENDING.md#添加输入)。
