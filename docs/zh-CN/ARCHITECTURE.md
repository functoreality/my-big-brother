# 技术架构与方案总览

[English](../ARCHITECTURE.md) | 简体中文

本文解释[PRD](REQUIREMENTS.md)的技术实现，先概括当前方案与边界，再指向细节约定。
它不授权增加产品行为。包括用户表面用途不变的技术调整，也遵守[协作流程](CONTRIBUTING.md)。

## T1. 职责与实现选择

My Big Brother 是本地仓库。少量 Python 模块负责准备证据、校验与发布文件，
共享 Markdown 任务指导 Agent 解释。核心只用标准库，截图处理可选依赖 Pillow，
没有服务端或通用插件框架。

| 边界 | 职责 | 需要保持的分离 |
| --- | --- | --- |
| 采集器 | 在宿主应用记录活动 | 不处理复盘分界、模型调用或报告生成 |
| 输入适配器 | 读取选定记录，生成事实索引与素材 | 不生成语义报告，也不执行日志命令 |
| 分析任务 | 指导证据阅读、任务归属与输出 | 不依赖某个 harness 的进程接口 |
| 通用运行程序 | 路径、准备、校验、发布、按日状态 | 不启动 Agent，不暗中接管语义流程 |
| 启动适配 | 带执行设置和日志启动一个 Agent | 不负责业务规划、导入、发布或模型重试循环 |
| 私人 profile | 绑定参考、格式、目标与后操作 | 不让标准产品依赖作者的机器与文件 |

原生日志读取器与启动适配相互独立，读取 Codex 历史不等于选择 Codex 执行。
目前附带 Codex 启动入口，其他 Agent 使用相同命令与任务约定。
有原生定时机制的 Agent 可以直接调度，不必使用项目专门的启动器。

这对应 PRD P1–P5、P9：多输出复用一次解释，安装可移植，应用与 harness 接入隔离。
采用显式适配器和明确配置的 profile，避免自动插件加载器或每个分析阶段另起模型。

## T2. 调用与运行生命周期

定时器位于外部，启动适配只启动一个 Agent。
日期选择、准备、解释、发布和完成检查都由这个执行 Agent 调用通用命令完成。
它可以使用自身宿主支持的委派能力。

```text
定时器或用户请求
  → 启动一个 Agent
  → 选择一个日期并准备证据
  → 阅读索引，写暂存产物
  → finish 校验与发布
  → 如有已配置后操作，由同一 Agent 执行
  → finish 校验操作回执，完成
```

1. 未明确日期时，`begin-automation`、`plan-due`、`due` 只选择最近已闭合逻辑日，
   尚保留有效完成状态的日期会跳过，没有历史补跑队列。
2. 新复盘由 `prepare` 或 `analyze` 建立独立运行、来源 manifest、索引、摘录、可选素材和
   已解析路径的 `context.json`。
   `due` 或 `analyze` 恢复尚保留的待处理后操作，不重新生成已经发布的报告。
3. 已有正式产物复制到暂存区，Agent 按共享任务和明确的私人说明合并。
4. `finish` 检查身份、条目覆盖、输出结构与所选校验器后发布，必需来源阻断时不能完成。
5. 已配置后操作返回 `actions-pending`，同一 Agent 在其范围内执行，
   提交操作回执后再次 `finish`。
6. 使用启动上下文时，再校验本次调用的票据与回执。
   `agent-exited` 只表示进程退出，不表示复盘完成。

没有可用证据时可返回 `empty`，不声称分析完成。
明确请求 `--allow-empty` 时，可基于保留产物和已声明参考进行复盘，
但仍不免除必需来源检查。准确顺序见
[AUTOMATION](../../tasks/daily-review/AUTOMATION.md)、
[WORKFLOW](../../tasks/daily-review/WORKFLOW.md)和[定时执行](SCHEDULING.md)。

## T3. 路径、时间与生命周期

源码安装与平台配置目录 C、数据父目录 D 分离。
普通配置缺失与可选路径文件缺失是两回事：`config.json` 保存复盘设置，
`raw-logs-path.txt` 只保存一个绝对采集根路径。没有显式覆盖且 TXT 缺失时，
各应用采用平台默认值。Vim 的显式 `record_dir` 优先于 TXT。
所有应用都不依赖 `storage.json` 或登记表。

```text
C/
  config.json
  raw-logs-path.txt                   可选的共享路径文件
  profile.json, local-tasks/          明确选定时使用
D/
  raw-logs/                          默认可清理根
    .publish.lock                    唯一固定大小的全局锁
    YYYY-MM-DD/
      bash/ vim/ screenshots/
      .review.lock
      review.json
      _analysis/RUN/
        context.json, manifest.json
        publication.json
        indexes/ excerpts/ drafts/ logs/ actions/
      _launches/INVOCATION/
  memory/                            默认 results_root
    USER-MODEL.md, MACHINE-CONTEXT.md  选中时使用
    records/YYYY-MM-DD/
```

`results_root` 和 profile 可指定 D/memory 外的长期目标，
这些是正式输出位置，不是另一套永久运行状态区。
逐日完成、发布和后操作状态都留在原始日志的日期下，删除无活动的日期就放弃其恢复。
不保留永久身份文件、已删日期墓碑或逐日操作台账。
唯一全局发布锁不记录历史，也不按日期增长。

采集使用真实本机自然日期，Bash/Vim 在会话启动时固定位置，截图使用各自拍摄日期。
分析单独应用 `day_start_hour`，窗口包含开始、不包含结束。
Bash/Vim 查找全部保留启动日期，再按事件时间或会话重叠筛选。
截图读取窗口相交的采集日期。整场 Vim 最终 diff 不能准确定位窗口内每项编辑。

这对应 PRD P4、P6、P8，不把复盘日界或主项目初始化引入独立记录器。
平台默认、路径校验、文件名与生命周期详见[存储](STORAGE.md)、
[输入](INPUT-SOURCES.md)、[Bash](BASH.md)、[Vim](VIM.md)。

## T4. 并发、冲突与恢复

| 问题 | 当前策略 | 边界或失败行为 |
| --- | --- | --- |
| 同日命令并发 | 非阻塞的日期内 `.review.lock` | 竞争命令失败，不悄悄并发执行 |
| 不同日期发布共享产物 | 固定大小的 `raw-logs/.publish.lock` 串行发布和完成更新 | 不承诺锁住任意外部写入者或整个模型会话 |
| 准备后目标被修改 | 保存原始摘要，替换前检查全部待发布目标 | 保留较新/人工修改并阻止发布 |
| 发布只完成一部分 | 逐文件原子替换，日志在本轮 `publication.json` | 不承诺多文件整体事务或自动回滚 |
| 保留材料内重试 | 检查日志、稳定身份、当前目标与回执 | 草稿或配置改变、回执无效时需诊断或重新准备 |
| 后操作 | 任务自行保证幂等，使用校验器和日期内操作日志/回执 | 核心阶段完成不是任意副作用的通用事务系统 |
| 手动删除日期 | 完成与恢复记录一起删除 | 无法自动恢复被删历史，明确重跑前核对外部现状 |

发布临时载荷仍在本轮日期内，因此当前正式目标和原始日志必须同文件系统。
跨文件系统时在替换前停止。这是已知实现限制，不是要求用户采用作者的路径。

锁策略、原子性、冲突处理和恢复保证的变化都是技术约定变更，
即使用户看到的报告名称没变，也不能直接作为局部优化实施。
准确发布与扩展约束见[存储](STORAGE.md)、[Profiles](PROFILES.md)，清理见[CLEANUP](CLEANUP.md)。

## T5. 任务约定、个人扩展与接口

适配器保留来源特有事实及缺口，通用准备程序分配证据标识，分开精简索引与可读摘录。
任务阅读完整索引，维护一致的时间线和任务图，结构回执不能证明解释正确。

标准输出 schema 与个人已有格式相互独立。
选定 profile 可以覆盖绑定，使用配有校验器的自定义 schema。
参考按需读取，用户授权可覆盖整机，读取范围独立于启动目录。
写目标仍分为暂存发布和后操作两部分。历史证据不能授权访问或覆盖可信指令。

| 细节约定 | 负责内容 |
| --- | --- |
| [输入](INPUT-SOURCES.md)、[Bash](BASH.md)、[Vim](VIM.md) | 格式、时间与 cwd、支持变体和覆盖限制 |
| [输出约定](../../tasks/daily-review/OUTPUTS.md)、[知识任务](../../tasks/daily-review/KNOWLEDGE.md) | 标准内容、schema 与累计知识合并 |
| [Profiles](PROFILES.md) | 私人说明与参考、目标、校验器和操作范围 |
| [定时执行](SCHEDULING.md)、[AUTOMATION](../../tasks/daily-review/AUTOMATION.md) | 启动环境、单 Agent 和命令/回执顺序 |
| [扩展](EXTENDING.md) | 新增采集、读取、任务、输出和启动适配的接口 |

细节改其所属文档，影响 PRD 或总览时一并修改。
不能在实现报告中再建一份相互竞争的完整规范。
较长的技术替代方案可以单独提出，但现行结论和代价仍须在本文概括。

## T6. 代码位置与验证边界

```text
my_big_brother/
  sources/          原生/采集来源适配器
  analyzers/        Agent 专属启动边界
  collector_paths.py, paths.py, config.py
                    平台发现、路径文件和复盘配置
  storage.py        日期目录辅助与文件锁
  runner.py         准备证据、校验、发布
  automation.py     执行 Agent 调用的规划与调用校验
tasks/daily-review/ 共享英文任务约定
collectors/bash/    可独立使用的可选 Bash 记录器
docs/              公开产品、技术和用户文档
examples/          合成产物与定时模板
```

测试使用隔离输入和临时目标，覆盖 history 保留、日期、覆盖声明、冲突和重试等机制。
真实 Agent 解释、原生平台运行和定时器实际触发是不同验证层次，
Linux 夹具通过不证明原生 macOS/Windows 正确。
开发基线与变更验证记录见[协作流程](CONTRIBUTING.md)。
