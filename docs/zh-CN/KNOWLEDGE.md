# 可选的长期知识输出

[English](../KNOWLEDGE.md) | 简体中文

两类标准输出可在多次复盘间保留有用背景，任何执行 Agent 都可以使用，
无需私人任务或记忆服务。默认关闭，原有四类默认输出保持不变。

| `config.json` 输出名 | 输出类型 | `results_root` 下的默认位置 |
| --- | --- | --- |
| `user-model` | `user_model` | `USER-MODEL.md` |
| `machine-context` | `machine_context` | `MACHINE-CONTEXT.md` |

在已有 `outputs` 数组中增加一个或两个名称即可。
完整标准输出列表与重定向 JSON 示例见[英文版](../KNOWLEDGE.md)。
保留配置中的其他字段。

执行 Agent 读取共享的[知识契约](../../tasks/daily-review/KNOWLEDGE.md)，
沿用日报的证据分析。程序不会为此启动额外 Agent，也不会主动盘点本机。

补做多日复盘时，先用 `plan-due --max-days N` 取得日期列表，不预先准备证据。
按日期从旧到新执行 `analyze --date YYYY-MM-DD --skip-completed`，
完成该日复盘和 `finish` 后再准备下一天，确保新草案包含最新累积知识。
若用 `due` 一次准备全部日期，较早日期更新共享目标后，后续草案可能过期并触发冲突。

User Model 记录相关目标、约束与明确表达的偏好。
Machine Context 记录已知机器、文件、目录与资料来源位置。
两者均应区分用户明确陈述、观察和不确定推断，保留日期、依据与适用范围。
历史中提到某条路径，不能证明它现在存在，也不构成读取授权。

准备复盘时，程序将已有知识文件复制到暂存草案，包含人工补充。
Agent 合并有依据的更新，保留既有知识和用户纠正，避免重跑时重复追加。
没有可靠新事实时，可保持已有草案不变。
新文件可简短说明尚未建立有依据的知识。

`finish` 将知识草案与日报一起校验发布。
正式目标在准备后发生冲突修改时，会阻止过期内容发布。
应重新准备复盘，再合并最新版本。
运行草案保留该轮提交的版本。
默认保留已有文件权限，除非 profile 明确覆盖。
后续累积知识更新不会使先前已完成日期失效。

如需使用已有文件，在选定的[本地 profile](PROFILES.md) 中设置
`output_paths.user_model` 和 `output_paths.machine_context`。
这两类 Markdown 绝对路径不要求 `{date}`。
是否准备和发布仍由 `config.json` 的 `outputs` 控制。
无需 Codex 专属绑定或自定义日报后任务，其他私人参考资料仍由 profile 明确限定。
