# 存储 v2

[English](../STORAGE.md)

个人数据根目录分为两个区域，与源代码仓库及平台配置目录 C 分离：

```text
data-root/
  daily/
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
`--results-root` 可选择其他长期结果位置，不能与 daily 重叠。
正式输出和 `daily` 须在同一文件系统。发布临时副本也放在日期目录，
再原子替换正式文件。跨文件系统时会在替换任何输出之前报错。

主项目初始化会生成 `C/storage.json`，只含 `schema_version: 2` 和 `data_root`。
`day_start_hour` 等分析设置仅存在于主项目的 `C/config.json` 中。

采集器也可以不安装主项目、不准备用户配置文件而独立运行。
`C/storage.json` 缺失时使用平台默认位置，运行登记状态自动建立。
可选的共享配置用于选择其他数据根。已有配置格式错误或运行登记损坏时报告错误。
`memory/_system/identity.json` 是自动维护的数据位置身份，不含复盘日界线。
采集器不会替用户创建配置文件。

平台默认位置见 [INSTALLATION.md](../../INSTALLATION.md)。
不支持在线移动已初始化的数据根。
修改协议前请先读公共[需求说明](REQUIREMENTS.md)。

## 原始记录自然日与分析窗口

原始记录目录始终取本机自然日期，等价于 `date +%F`。
15 日凌晨 02:30 的 Bash 记录放进 `daily/2026-10-15/bash/`，
即使分析设置了 04:00 分界也不会改放前一天，原始时间戳同样保持真实。
截图按拍摄自然日期归档。Vim 在自然午夜分段，未观察到跨日时明确报告缺口。

工作日只由分析层解释。14 日 04:00 至 15 日 04:00 的复盘，
读取两个自然日期目录，并按真实时间戳筛选。
一个自然日目录可能服务于两次复盘。分析中间材料仍使用被复盘日期下的 `_analysis/`。
Agent 原生历史由对应应用管理。

用户可以直接删除已无活动写入的旧日期，包括失败或未完成日期。
无需打开状态文件。删除表示放弃自动恢复，见[手动清理](CLEANUP.md)。
所有写入者在创建日期前登记。已登记目录消失后，持久化逐日记录将其标为放弃。
复盘、采集和导入不得自动重建。完成事实和工作区是否放弃分开记录，
因此删除输入不删除已完成日报，配置变化也不能覆盖放弃决定。

只有用户明确要求恢复时使用：

```sh
python -m my_big_brother analyze --date 2026-10-14 --recreate-deleted
```

它准备新一代运行，不启动 Agent，也不能恢复已删除的证据。
自动任务不得自行添加这个选项，普通 `--date` 不表示获准恢复。

## 采集器和扩展

标准库协议实现在 `my_big_brother/storage.py`。
Bash 采集器及独立 Vim 插件附带同一协议，使插件仍能独立安装。
首次并发写入通过持久化锁协调，不让用户维护多份根目录。
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
