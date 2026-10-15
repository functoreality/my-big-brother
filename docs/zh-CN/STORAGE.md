# 存储 v2

[English](../STORAGE.md)

个人数据根目录分为两个区域，与源代码仓库及平台配置目录 C 分离：

`raw-logs` 保存可清理的复盘工作材料，包括采集记录、预处理结果、索引、截图拼图、
Agent 草稿和执行日志，也可以包含 AI 生成的内容。
区分依据是“按日期保存的工作材料”与“长期保留的正式成果”，不以是否经过 AI 为界。
正式报告与积累的知识放在 `memory` 或明确配置的长期输出位置。
`paths` 命令通过 `raw_logs` 字段显示这个可清理根目录。

```text
data-root/
  raw-logs/
    YYYY-MM-DD/
      bash/
      vim/
      screenshots/
      _analysis/<运行ID>/
      _launches/<启动ID>/
      scheduler.log
  memory/
    USER-MODEL.md
    MACHINE-CONTEXT.md
    records/YYYY-MM-DD/
      worklog.md
      time-use.md
      time-use.json
      insights.md
      time-estimates.json
    _system/
      identity.json
      days/YYYY-MM-DD.json
      operations/
      locks/
```

只生成启用的产出和用过的来源目录。知识输出仍是可选功能。
个人 profile 可以将正式文件保留在既有外部位置。
profile 是配置规则，不是累计知识，仍放在 C 中。

## 主程序与独立采集器

```sh
python -m my_big_brother init --sources bash --day-start-hour 4
python -m my_big_brother paths
```

首次安装可用 `--data-root /绝对路径` 选择整个数据根。
`--results-root` 可选择其他长期结果位置，不能与 raw-logs 重叠。
正式输出和 `raw-logs` 须在同一文件系统。发布临时副本也放在日期目录，
再原子替换正式文件。跨文件系统时会在替换任何输出之前报错。

`C/raw-logs-path.txt` 是共享采集根路径，通常指向 D/raw-logs。
它只含一行 UTF-8 绝对路径，允许末尾一个 LF 或 CRLF，保留路径中的空格。
不加引号、注释，不展开变量。缺失时使用平台默认位置，已有文件格式错误时报错。
Bash、Vim，以及主项目的采集和分析目录使用同一路径。
有意读取其他来源时，仍可显式设置来源路径。

初始化会写入解析后的 TXT 路径，但不覆盖已有文件。
同时创建 `C/storage.json`，包含 `schema_version: 2` 和 `data_root`，
用于主项目的长期 `memory` 与系统身份。记录器不需要这个 JSON。
`day_start_hour` 等分析设置仅存在于 `C/config.json`。
改变采集根不会移动长期输出或系统事实，采集根不能与长期知识或结果目录重叠。

Bash 可独立使用，不要求安装或初始化主项目。
它启动时读取一次 TXT，缺失时使用平台默认值。
不读取 `storage.json`，不登记日期，也不创建用户配置。
每个会话创建一个文件，文件或父目录删除后停止追加。

独立 Vim 插件使用简单的三级路径规则：`record_dir`，
然后是 `C/raw-logs-path.txt` 中的一条绝对路径，最后是平台数据目录下的 `raw-logs`。
它只在启动时确定根目录，不读取 `storage.json`、不携带共享协议副本、不登记日期。
退出比较与 JSON 直接使用已经保存的会话目录。

平台默认位置见 [INSTALLATION.md](../../INSTALLATION.md)。
不支持在线移动已初始化的数据根。
修改协议前请先读公共[需求说明](REQUIREMENTS.md)。

## 原始记录自然日与分析窗口

原始记录归属取创建记录时的本机自然日期，等价于启动当下的 `date +%F`。
Bash 启动时创建一个 JSONL，整个 shell 生命周期都追加到这一文件。
14 日启动的 shell，在 15 日甚至数月后仍写入 `raw-logs/2026-10-14/bash/`。
自然日或逻辑日切换都不改变已有记录的位置，事件时间戳始终真实。
每张截图是独立记录，按自身拍摄自然日期归档。
Vim 整场会话按启动时的自然日期归档，跨午夜退出也不换目录。
一个编辑器进程对应一个会话，打开文件时保存原始快照，退出时生成 diff 和 JSON。
不进行午夜分段，也不增加定时或事件触发的检查点。
共享存储只管理路径和生命周期，不改变采集行为。

工作日只由分析层解释。14 日 04:00 至 15 日 04:00 的复盘，
在全部保留的启动日期目录中查找 Bash 和 Vim 会话。
Bash 按实际事件时间筛选，Vim 按真实会话区间与分析窗口的重叠筛选，
包括早于上述日期启动的会话。整场 diff 不能确定每项编辑属于哪一天。
退出前已有原始快照，但没有最终 `record.json` 可供索引。
一个自然日目录可能服务于多次复盘。分析中间材料仍使用被复盘日期下的 `_analysis/`。
Agent 原生历史由对应应用管理。

用户可以直接删除已无活动写入的旧日期，包括失败或未完成日期。
无需打开状态文件。删除表示放弃自动恢复，见[手动清理](CLEANUP.md)。
使用共享运行时协议的写入者在创建日期前登记。已登记目录消失后，持久化逐日记录将其标为放弃。
复盘、采集和导入不得自动重建。完成事实和工作区是否放弃分开记录，
因此删除输入不删除已完成日报，配置变化也不能覆盖放弃决定。

只有用户明确要求恢复时使用：

```sh
python -m my_big_brother analyze --date 2026-10-14 --recreate-deleted
```

它准备新一代运行，不启动 Agent，也不能恢复已删除的证据。
自动任务不得自行添加这个选项，普通 `--date` 不表示获准恢复。

## 采集器和扩展

主项目协议实现在 `my_big_brother/storage.py`，受管理的写入通过持久化锁协调。
独立 Bash 和 Vim 只读取前述纯路径 TXT，不登记或检查日期的放弃状态。
已有 Bash 会话不会重建被删除的文件或目录，新会话使用它自己的当前启动日期。
Bash 只携带很小的平台与路径辅助模块，原版为 `my_big_brother/collector_paths.py`。
活动会话目录被移除后，Vim 退出时不会重建它。
采集器不读取或共享分析日界线。

已有截图程序可调用 `capture-path --source screenshots` 取得登记后的目标目录，
调用 `record-screenshot --image /绝对路径/image.jpg` 保存已有图片并登记时间。
两者接受带 UTC 偏移的 `--timestamp`，旧日期已删除时返回 `discarded`。
这些命令不会拍摄屏幕，也不会启动周期截图。

推理、摘录、脚本、校验临时空间、完整收据及候选修改的备份均放在所属日期。
后操作从上下文取得 `operation_state_dir`，只存最小持久化操作事实。
副作用之前记录稳定标识，包括崩溃后尚不确定是否生效的操作。
不要把原始内容和完整日志搬到长期状态区。
删除日期会停止剩余步骤，不回滚已有修改。
自定义扩展必须自行支持可核验的幂等和放弃语义。

启动仍然只调用一次 Agent。启动器只定位日期日志，不规划复盘。
目标日已放弃时，启动日志归当前自然日期。
没有合法目录或登记不可读时，只返回标准错误和失败状态，不另建缓存根目录。
