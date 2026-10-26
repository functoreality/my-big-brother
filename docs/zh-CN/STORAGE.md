# 存储

[English](../STORAGE.md)

个人存储与源代码仓库、平台配置目录 C 分离。
`raw-logs` 保存按日期组织、可以清理的工作材料。
`memory` 或明确配置的长期位置只保留选中的正式报告和累计知识。
`paths` 命令通过 `raw_logs` 字段显示可清理根目录。

```text
data-root/
  raw-logs/
    .publish.lock
    YYYY-MM-DD/
      bash/
      vim/
      screenshots/
      review.json
      _analysis/<run-id>/
        publication.json
        notifications/
        actions/
      _launches/<invocation-id>/
      scheduler.log
  memory/
    inbox/DATE--STABLE-ID.md
    USER-MODEL.md
    MACHINE-CONTEXT.md
    records/YYYY-MM-DD/
      worklog.md
      time-use.md
      time-use.json
      insights.md
      time-estimates.json
```

只创建选中的输出和用过的目录，新安装默认选择包含知识在内的六类输出，各项可关闭。
个人 profile 可以把正式成果放在已有外部位置，其指令属于配置，仍保存在 C。
本地收件箱默认是 `results_root/inbox/`，可通过 `notifications.inbox` 更改。
消息属于长期产物，不放在原始日志内，详见[本地主动提醒](NOTIFICATIONS.md)。
完成标记、发布日志、后操作日志、回执和执行日志都属于 `raw-logs/日期`，
随日期目录一起删除。`memory` 中不保留永久逐日台账或系统状态目录。
日期目录之外唯一的技术例外是固定大小的 `raw-logs/.publish.lock`，
用于协调共享输出发布，不记录日期历史，也不随复盘增长。

个人来源代码和合成测试可放在 `C/readers/<source>/`，由 `config.json` 显式选择。
它们属于配置，不是可清理的日期材料，源码升级时保留。
读取器身份摘要只保存在日期内运行上下文，不另设永久登记表。

## 路径与初始化

```sh
python -m my_big_brother init --sources bash --day-start-hour 4
python -m my_big_brother paths
```

`C/raw-logs-path.txt` 是共享原始日志根位置文件，通常指向 D/raw-logs。
它只含一行 UTF-8 绝对路径，允许末尾一个 LF 或 CRLF，保留路径中的空格。
不加引号、注释，不展开变量。缺失时使用平台默认位置，已有文件格式错误时报错。
Bash、Vim 和主程序使用同一位置文件，有意读取其他来源时仍可显式设置来源路径。

初始化创建普通配置和必要目录，默认路径无需 TXT 文件。
使用 --data-root 快捷选项时，才在 TXT 缺失时写入，已有路径文件保持原样。
主程序和独立记录器都不要求 `storage.json` 或存储身份。
`day_start_hour` 等复盘设置保存在 `C/config.json`。
`results_root` 选择长期输出位置，默认为 D/memory。

首次安装时，`--data-root /绝对路径` 是快捷选项，
通过位置文件与 `results_root` 选择其下的 `raw-logs` 和 `memory`，
不另外持久化数据根设置，已有设置会保留。
`--results-root` 可单独选择长期结果根，不能与原始日志存储重叠。
正式输出可以使用其他文件系统或挂载点，执行 Agent 仍须具备该位置的写权限。
修改采集位置文件不会移动已有输出。
平台 C、D 默认位置见 [INSTALLATION.md](../../INSTALLATION.md)。

## 发布与中断写入

`finish` 先校验暂存输出，再检查正式目标的摘要。
发布锁串行化遵循同一协议的发布者。
合格草稿直接读取并写入正式位置，不另建发布临时副本，也不做跨目录重命名。
POSIX 下保留已有文件的权限，新文件默认为 `0600`，除非 profile 明确选择其他模式。

发布不保证单文件或整组输出的原子性。
读取者可能短暂看到不完整内容，写入中断也可能留下空的或部分写入的正式文件。
完整草稿仍在 `raw-logs/日期/_analysis/运行/drafts/` 内。
没有自动回滚，也不额外备份此前的正式内容。

本轮 `publication.json` 记录已写完的文件。
剩余目标仍与准备时内容或完整草稿一致时，可用同一运行目录重试 `finish`。
部分写入或较新的人工编辑会触发摘要冲突并停止发布。
此时先核对目标，再人工从完整草稿恢复或合并修改。
通过 `context.json` 的 `output_mapping` 对照每一组 `staged` 与 `final` 路径。
恢复为完整草稿后可重试 `finish`，若合并后内容不同则重新准备复盘。
不要丢弃较新的编辑，也不要提前删除日期内的恢复材料。

## 原始记录自然日与分析窗口

原始记录归属取创建记录时的本机自然日期，等价于启动时的 `date +%F`。
Bash 启动时创建一个 JSONL，整个 shell 生命周期都追加到这一文件。
14 日启动的 shell，在 15 日甚至数月后仍写入 `raw-logs/2026-10-14/bash/`。
自然日或逻辑日切换不改变已有记录的位置，事件时间戳始终真实。
每张截图是独立记录，按自身拍摄自然日期归档。

Vim 仅在启动时依次选择 `record_dir`、`C/raw-logs-path.txt`、
平台数据目录下的 `raw-logs`。
一个编辑器进程对应一个会话，始终使用启动自然日期，包括跨午夜退出。
打开已有文件时保存原始快照，退出时生成 diff 和 JSON。
不进行午夜轮转，也不增加定时或事件触发的检查点。
Bash、Vim 不要求初始化主程序，已有会话不会重建被移除的文件或会话目录。
新会话使用它自己的当前启动日期。

工作日只由分析层解释。14 日 04:00 至 15 日 04:00 的复盘，
在全部保留的启动日期目录中查找 Bash 和 Vim 会话。
Bash 按实际事件时间筛选，Vim 按会话区间与分析窗口的重叠筛选，
包括早于上述日期启动的会话。整场 diff 不能确定每项编辑属于哪一天。
退出前已有原始快照，但没有最终 `record.json` 可供索引。
一个自然日可能服务于多次复盘，分析材料仍在被复盘日期下的 `_analysis/`。
Agent 原生历史由对应应用管理。

## 清理与重跑

可以直接删除已无活动写入的旧日期，包括失败运行，不用查看状态文件。
证据、完成标记、恢复日志随目录一起删除，正式报告、知识和已生效修改仍保留。
不要删除仍有 shell、编辑器或复盘正在使用的日期，详见[手动清理](CLEANUP.md)。

无人值守复盘只处理最近一个已闭合的逻辑日。
不排队处理更早日期，不扫描历史缺口，也不自动补做停机期间的日期。
需要重跑更早日期时，明确指定：

```sh
python -m my_big_brother analyze --date 2026-10-14
```

明确日期可以创建对应工作区，但不能恢复已删除的证据。
完成标记删除后，该日不再有运行状态记录。
已有正式输出仍可复制到暂存区，以便复盘时保留人工补充。

## 采集器与扩展

采集器和采集辅助命令直接写入自然日期路径，不需要登记日期。
Bash 只携带简单的平台与位置辅助模块，原版为 `my_big_brother/collector_paths.py`。
Bash、Vim 和截图即使明确指定路径，也必须采用来源根下的日期/来源结构。
不要增加平铺目录探测或迁移回退。

已有截图程序可调用 `capture-path --source screenshots` 获取目标目录，
调用 `record-screenshot --image /绝对路径/image.jpg` 保存已有图片并记录拍摄时间。
两者接受带 UTC 偏移的 `--timestamp`，不会拍摄屏幕或启动周期截图。

推理、摘录、脚本、校验临时空间、完整回执、后操作日志和候选备份均放在所属日期的分析运行中。
副作用前，在后操作目录记录稳定操作标识和待核验结果。
重试仍保留的运行时，须检查这些日志并验证幂等性。
日期删除后，不再有隐藏操作历史，明确重跑时扩展须先核验外部效果。

启动只调用一次 Agent。日志使用明确请求的日期，默认使用前一个自然日期，
与逻辑日分析独立。所有启动诊断均可清理。
无法分配日志目录时，返回标准错误和失败状态，不另建缓存根目录。
