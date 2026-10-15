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
      storage.json
      days/YYYY-MM-DD.json
      operations/
      locks/
```

只生成启用的产出和用过的来源目录。知识输出仍是可选功能。
个人 profile 可以将正式文件保留在既有外部位置。
profile 是配置规则，不是累计知识，仍放在 C 中。

## 初始化共享存储

```sh
python -m my_big_brother init --sources bash --day-start-hour 4
python -m my_big_brother paths
```

首次安装可用 `--data-root /绝对路径` 选择整个数据根。
`--results-root` 可选择其他长期结果位置，不能与 daily 重叠。
正式输出和 `daily` 须在同一文件系统。发布临时副本也放在日期目录，
再原子替换正式文件。跨文件系统时会在替换任何输出之前报错。

初始化生成 `C/storage.json`，包含版本 2、`data_root` 和 `day_start_hour`。
采集器和分析程序共用它，不必在 vimrc、bashrc 中重复设置。
日界线初始化后固定，不能只修改 `config.json` 中的值，
也不能只手工创建定位文件而不建立持久化登记。
不支持在线修改已初始化的根目录或日界线。
平台默认位置见 [INSTALLATION.md](../../INSTALLATION.md)。
v2 配置损坏时报告错误，不悄悄回退到旧目录。

## 工作日和删除

日界线为 4 时，`2026-10-14` 包含 14 日 04:00 至 15 日 04:00。
Bash 按命令完成时刻归档，截图按拍摄时刻归档。
独立 Vim 插件按工作日分段，未观察到边界附近活动时明确报告缺口。
Agent 原生历史仍由对应应用管理。

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
首次并发写入通过持久化锁协调，不让用户维护多份根目录或日界线。

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
目标日已放弃时，启动日志归当前工作日。
没有合法目录或登记不可读时，只返回标准错误和失败状态，不另建缓存根目录。
