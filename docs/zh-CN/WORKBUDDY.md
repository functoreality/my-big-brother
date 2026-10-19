# WorkBuddy 对话

[English](../WORKBUDDY.md)

可选读取器支持 Windows WorkBuddy 安装反馈中观察到的项目会话 JSONL 格式。
只读取已有历史，不启动 WorkBuddy、不修改记录，也不安装持续采集。

## 启用来源

预期默认位置为 `~/.workbuddy/projects`，
文件布局为 `<projects>/<project>/<session>.jsonl`。
安装 Agent 应在目标账号核实实际位置和格式。
来源发现、输入选择和每日执行 Agent 相互独立。

首次安装且选择 WorkBuddy 作为来源时：

```sh
python -m my_big_brother init --sources workbuddy
python -m my_big_brother analyze --date YYYY-MM-DD
```

通用默认配置中 WorkBuddy 为关闭状态。
已有配置应添加或更新 `sources.workbuddy`，设 `enabled: true`，
将 `path` 配置为项目历史根目录的绝对路径，保留其他来源选择。
新增读取器不会在已有配置中自动启用来源，JSON 路径不展开 `~` 或环境变量。

## 证据与限制

- 读取项目下直接存放的 `.jsonl`，不递归子会话目录，
  不读取 `.file-rollback.ndjson` 回滚快照。
- 按消息内毫秒时间戳筛选半开窗口，支持 UTF-8 及文件开头的 BOM。
- 从用户消息剥离已知 `<system-reminder>` 块，有 `<user_query>` 时只取其中内容。
  已知包装不完整时记录缺口，不能声称识别了所有可能的宿主注入格式。
- 保留用户请求、助手文本、来源文件及实际行号。
  目录使用该事件当时可得的上下文，不取会话最后的目录。自动标题只是会话元数据。
- 助手文本标为 `assistant`。token 用量不证明最终答复或任务成功，
  其进展和完成说法仍是声明。
- 忽略工具调用、参数、结果、思考及文件快照。
  调用工具不证明修改成功，不把推断的工具汇总附到后续消息上。
- 会话任意位置出现复盘标记时排除整场，包括此前已收集或标记出现在窗口外的情况。
- 根目录缺失时返回 `unavailable`，读取与解析错误记录为缺口。
  位置可读但没有匹配消息，不能说明用户没有工作。

反馈包含一次原生 Windows 安装报告。
本仓库读取器检查使用合成夹具，覆盖准备与发布。
实际 WorkBuddy 版本及原生 macOS/Windows 执行仍需持续验证，
相同目录布局不等于已证明平台运行一致。
