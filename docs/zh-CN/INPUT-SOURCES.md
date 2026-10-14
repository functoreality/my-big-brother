# 输入来源

[English](../INPUT-SOURCES.md) | 简体中文

输入适配器准备事实证据，任务说明和 Agent 负责解释证据。
适配器不会执行历史记录中的命令。

Vim 与截图都是可选来源，需要在个人配置中明确启用。
适配器读取配置的 `path`，省略该字段时使用共享原始日志根目录。
启用适配器不会安装采集器或启动持续采集。

## Bash 会话上下文

Bash 适配器读取按日期存储的 `YYYY-MM-DD/bash/*.jsonl`，
也支持明确配置的平面旧会话根目录。
活动条目始终限定在复盘窗口内。
如果命令或会话结束事件的起始记录位于更早时间，
适配器会把最近一次先前起始记录放入 `session_context`，
包括 `outside_window: true`、实际起始时间、原始字段和来源位置。
这份上下文不会新增活动条目。

历史查询只读取与窗口内事件相关的会话文件。
此前的命令和其他会话的命令不会复制到索引中。
命令时间戳、目录以及原记录的采集范围或时间戳范围保持不变。
缺少采集范围时，会明确注明旧历史无法支持覆盖范围推断。
现代采集器的命令 `started_at` 不会被当成 shell 会话起始时间。
采集器本身的限制见 [Bash 记录](BASH.md)。

## Vim 会话

共享存储结构如下：

```text
raw/YYYY-MM-DD/vim/session/record.json
raw/YYYY-MM-DD/vim/session/<snapshot artifacts>
raw/YYYY-MM-DD/vim/session/<modification diff artifacts>
```

适配器递归扫描每个 Vim 子目录，包括开始于更早日期的会话。
会话在复盘窗口之前开始、在窗口内结束时仍会纳入索引。
明确配置的旧 Vim 根目录可以保留原有会话布局，包括 `viewed/`。
共享根目录还可以在 `legacy/vim/` 下保留导入的旧会话。

每条 manifest 都需要 `vim_start`。
旧记录中的开放会话可以没有 `vim_close`。
新记录应使用带时区偏移的 ISO 8601 时间戳。
不带偏移的旧时间按当前机器的本地时区解释。
适配器会明确报告这一假设，因为夏令时切换和跨时区迁移可能造成歧义。

适配器支持会话采集器的版本 1 格式，以及没有版本字段的旧格式。
不支持的 `schema_version` 会被排除并报告缺口。
版本 1 使用 `source: vim`、32 位十六进制 `session_id`，
以及逐文件的 ID、路径、打开时间和快照、比较状态。
字段格式错误、快照失败和比较失败都会产生明确缺口。

索引在 `record_metadata` 中保留完整 manifest，
包括未知字段、执行标记、聚焦行和标识符。
`files` 保留各打开文件对象的字段，并补充文件名和修改状态。
`record_sha256` 标识原始 manifest。
`artifacts`、`diff_paths` 和 `snapshot_paths` 定位会话内的采集文件，
但适配器不读取这些文件的内容，也不读取当前工作文件的原文。

版本 1 的 `original_file` 和 `diff_file` 指定同目录中的原始快照与 diff。
适配器按需在逐文件记录中补充 `original_artifact` 和 `diff_artifact`，
包括缺失或非法引用的状态。
未修改的文件可以完成比较，而不生成 diff 文件。
比较失败后没有修改行数，意味着修改情况未知。
此时使用 `modified: null`，不能把缺少行数当成零修改。

`last_focus_line` 可能包含编辑器缓冲区中尚未保存的文字。
这些内容不能证明文件已经保存。
`executed: true` 记录的是用户映射所作的执行标记，
不能独立证明命令已执行或执行成功。

`timestamp` 是会话与复盘窗口首次重叠的时刻，
便于在普通证据时间线中找到跨窗口会话。
`actual_session_start` 与 `actual_session_end` 保留实际会话区间。
整场会话的 diff 不能确定每项编辑发生在裁剪区间中的哪一刻。
`diff_scope` 明确说明这一限制。

如果完整记录的关闭时间晚于本次快照结束时间，适配器会排除该记录，
因为最终 diff 可能包含快照之后的修改，并在来源缺口中记录这一限制。
已有 manifest 的开放会话保留可用元数据，
并标为 `session_status: open` 和 `diff_status: incomplete_session`。
适配器不会声称它已有完整的最终 diff。

当前版本 1 采集器只在编辑器退出时写入最终 manifest，没有定期检查点。
尚在运行或写入失败、没有 `record.json` 的会话无法被适配器发现。
已识别的 Vim 子目录存在且可读、却没有匹配记录时，会返回成功的空索引。
这只表示未找到记录，不代表采集正在运行或记录完整。
共享原始日志根目录没有 Vim 子目录、来源根目录不存在，
或所有记录都无法读取或不受支持时，返回 `unavailable`。
有效记录与损坏记录并存时返回 `partial`。
快照之后关闭的记录只产生限制说明，不会因此把来源标为不可用。

## 截图帧

共享存储结构如下：

```text
raw/YYYY-MM-DD/screenshots/capture.png
raw/YYYY-MM-DD/screenshots/manifest.json
```

支持 JPEG、PNG 和 WebP。
明确配置的旧截图根目录可以直接包含平面的图片文件。
共享根目录中还可将导入的平面文件存放在 `legacy/screenshots/`、
`legacy/screen/` 或 `legacy/screen_record/`。
采集器迁移期间，已有的 `YYYY-MM-DD/screen_record/` 目录也会被读取。
新采集器应使用 `screenshots/`。
适配器不会去无关输入源目录寻找图片。

没有 manifest 时，使用文件修改时间作为采集时间。
导入旧图片时应保留修改时间。
JSON manifest 可以是帧对象列表，也可以是包含 `frames` 列表的对象。
`manifest.jsonl` 可以每行记录一个帧对象。
每个对象使用 `path` 或 `filename` 指定截图目录内的图片，
使用 `timestamp` 或 `captured_at` 指定带偏移的 ISO 8601 时间。
共享格式示例见[英文文档](../INPUT-SOURCES.md#screenshot-frames)。

有效的 manifest 采集时间优先于文件修改时间。
`capture_metadata` 保留完整帧对象。
无效的采集时间会退回文件修改时间，同时报告缺口。
日期目录只是组织方式，不能代替可靠的采集时间戳。

每帧索引包括来源路径、SHA-256、尺寸、采集时间、修改时间及时间语义。
历史字段 `perceptual_hash` 使用 16 × 16 灰度平均哈希，
由 `hash_algorithm: average_hash_16x16` 标识。
相邻哈希相差超过 16 位时，开始新的 `segment`。
`representative` 标记分段首帧，但索引和联系表仍保留全部帧。

`previous_capture_timestamp` 和 `seconds_since_previous_capture`
描述观察到的采样间隔。
它们不能直接证明注意力投入、离开电脑或工作时长。
把截图之前的一段时间归入工作时间的解释规则，应放在用户分析 profile 中。

截图索引和图像转换需要可选依赖 Pillow。
未安装时，该来源返回 `unavailable` 并报告明确缺口，其他来源仍可准备。
个别损坏图片会产生缺口，其余可读帧仍然保留。

## 可回看资产

运行器为每帧分配 `evidence_id` 后，
调用 `screenshots.prepare_assets(rows, run_target)`。
`run_target` 是本次运行内的来源目录。
返回的元数据保存在该来源的 `assets` 字段中。

资产由 JPEG 联系表和对应的 JSON 单元格映射组成。
每帧都获得一个位置，包括与相邻帧相似的画面。
完整画面缩小到 640 × 352 图像区域内，保持宽高比，不裁剪或放大。
每张联系表容纳六帧。

映射保留证据 ID、来源路径、时间戳、SHA-256、分段、原始尺寸、
渲染尺寸、图像位置和转换状态。
转换前会检查来源 SHA-256。
图片发生变化或丢失时，仍保留其映射位置，并明确标为转换失败。
`coverage` 汇总已索引、已映射和成功转换的帧数。
资产路径相对于本次运行的来源目录。
