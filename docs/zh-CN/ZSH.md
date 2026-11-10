# 可选 Zsh 记录

[English](../ZSH.md) | 简体中文

内置 Zsh 采集器记录完整交互输入、命令完成和正常会话边界。
独立的 `zsh` 读取器把这些记录提供给每日复盘。
安装项目或启用读取器不会开始记录，添加 shell hooks 需要持续采集授权。
若已有授权覆盖这类记录，安装或更新 Agent 可直接配置、验证并告知，无需重复询问。
范围与排除规则见[来源维护](../../INSTALLATION.md#adding-sources-during-maintenance)。

## 安装

需要 Zsh 和 Python 3，推荐 Python 3.11+。
收到的 macOS arm64 试装报告记录了 Zsh 5.9、Python 3.9.6 和 Python 3.13 的隔离测试，
以及通过实际 `.zshrc` 启动的合成烟测。
该报告未验证其他 Zsh 版本和平台。
本项目的隔离测试也在 Linux Zsh 5.9 下通过。
这些检查不涵盖所有第三方提示符框架，仍需验证自己的集成。

备份实际加载的交互式 `.zshrc`，在靠近末尾、其他提示符集成之后添加：

```zsh
source "/absolute/path/to/my-big-brother/collectors/zsh/session-recorder.zsh"
```

若使用 `ZDOTDIR` 指定启动目录，修改该目录下的 `.zshrc`。
这个采集器只用于 Zsh，Bash 另见 [Bash 说明](BASH.md)。

默认使用 `python3`。需要指定已验证的解释器时，在加载前设置：

```zsh
export MBB_PYTHON="/absolute/path/to/python3"
source "/absolute/path/to/my-big-brother/collectors/zsh/session-recorder.zsh"
```

配置变动或升级后打开新的交互式 shell。
重复加载不会增加重复 hooks 或另建会话文件，非交互式 Zsh 不挂接采集器。
当前会话固定使用启用时选定的 Python 和辅助脚本路径。
辅助程序只用标准库，无需安装 Python 包，仓库须保留在 `.zshrc` 引用的位置。
hook 加载或注册失败时，记录器会明确报告未挂接。
修复环境后可重新 source 或打开新 shell，记录文件存在不证明 hooks 已成功挂接。

## 读取记录

新安装且只选择 Zsh 来源时：

```sh
python -m my_big_brother init --sources zsh --day-start-hour 4
python -m my_big_brother doctor
```

已有安装若尚无 `zsh` 项，在 `C/config.json` 的 `sources` 中添加
`"zsh": {"enabled": true}`，保留其他设置和来源选择。
若已有 `zsh` 项，保留其 `path`、`required` 和任何个人 `reader` 绑定。
新增官方支持不会替换个人读取器，须按[扩展指南](EXTENDING.md#添加输入)
比较，并由用户选择是否切换。不重新初始化覆盖配置。
读取器默认关闭，省略 `sources.zsh.path` 时使用共享原始日志根目录，
也可显式选择另一个根目录。选择读取器不会安装 shell hooks。
`doctor` 会报告匹配 JSONL 文件是否存在，但这不证明正在记录或记录完整。

采集器不要求先配置 My Big Brother。
它只在启动时读取 `C/raw-logs-path.txt`，缺失时使用平台数据目录下的 `raw-logs`。
位置文件只含一行 UTF-8 绝对路径，允许末尾一个 LF 或 CRLF，保留路径中的空格。
不支持引号、变量展开、相对路径或额外行，已有文件格式错误时报错。
采集器不读取 `config.json` 或 `storage.json`，不登记日期，也不启动分析 Agent。
平台默认位置见[存储说明](STORAGE.md)。

## 存储与事件

每个 shell 只使用一个 `raw-logs/YYYY-MM-DD/zsh/*.jsonl` 文件。
开始记录时固定自然日期和初始目录，跨午夜、持续数月、切换目录、
修改位置文件都不重选路径。已移除的记录文件或父目录不会因追加而重建。
文件名采用与 Bash 相同的
`HH-MM-SS_<initial-directory-name>_<pid>.jsonl` 规则，目录提示有长度限制，
名称冲突时增加数字后缀。新文件权限为 `0600`，不改变调用者的 umask。
时间戳始终使用真实本地时间并带时区偏移。

- `session_start` 含 `event`、`started_at` 和初始 `cwd`，挂接时立即写入。
- `command` 含 `event`、`started_at`、`completed_at`、`cwd`、`command`、
  `exit_status`。`preexec` 观察完整输入，包括复合、多行输入、前导空格与别名原文。
  开始时间是执行前观察到的系统时间，精度为秒。
  目录是整条输入执行前的 shell 目录，下一次提示符或正常退出时观察完成。
- `session_end` 含 `event`、`ended_at` 和最终 `cwd`。
  正常 `exit 7` 会先记录这条输入及状态 7，再写结束边界，EOF 也写正常结束边界。

文件本身标识会话，每条命令不重复会话 ID 或启动元数据。
读取器查找全部保留的启动日期，按真实事件时间筛选左闭右开的复盘窗口，
可把更早的 `session_start` 附为上下文。命令按 `completed_at` 筛选。
即使显式指定来源根目录，也只读取其下的日期/Zsh 结构。
不会导入原生 `.zsh_history` 或扫描其他布局，详见[输入来源](INPUT-SOURCES.md)。

## 原生历史、hooks 与覆盖范围

采集器通过 `add-zsh-hook` 添加 `preexec`、`precmd` 和 `zshexit` hooks，
保留原有同名函数、数组 hooks、原生命令历史及 shell 选项，不重放或重编号历史。
去重、前导空格过滤、`zshaddhistory` 排除、`HISTSIZE=0`、未设 `HISTFILE`
或 `SAVEHIST=0` 都不会把输入排除出 JSONL。
记录文本由原生 `preexec` 提供，`HIST_REDUCE_BLANKS` 等设置可能压缩空白，
因此这不是逐字节还原键盘输入的审计记录。

Zsh 在较早 hook 返回非零时停止调用后续 hooks，因此某些集成会阻止采集或完成记录。
只读 hook 数组会阻止挂接，挂接后动态替换 hooks 不受支持。
应验证自己的提示符集成，不能直接假定记录完整。

采集器记录已完成的前台输入，不记录终端输出、复合输入内的逐条执行、
后台任务完成情况或专注工作时长。
`exec` 替换不会触发 `zshexit`，这条尚未完成的输入不会留下完成事件或会话结束。
强制终止、崩溃和断电也可能缺少最后输入及结束边界，缺少事件不能证明没有活动。

## 暂停与隐私

暂停后续命令采集时，单独提交下面这一条，等待下一个提示符后再输入敏感内容：

```zsh
MBB_ZSH_RECORDING=0
```

用 `MBB_ZSH_RECORDING=1` 恢复。是否采集在整条输入执行前决定，
关闭记录的这条输入本身可能已被记录，包括同条输入中的其他操作。
暂停期间仍保留会话边界。在首次加载前设为 0 则完全不挂接。
卸载时移除 source 行并打开新 shell，已有记录不会删除。

原生命令历史排除规则不能提供采集器隐私保护。
有限的尽力脱敏规则会把含 token、secret、password、API-key 名称赋值、
`sshpass` 或 `Authorization:` 的整条输入替换为 `<redacted:possible-secret>`，
其他敏感内容仍可能被记录。脱敏也不会修改原生 history 中的副本。
文件名会显示初始目录提示，选中的证据可能发送给已配置的 Analyzer 提供方分析。
敏感输入前单独暂停，并管理记录保留周期。

## 测试

```sh
python3 -m unittest discover -s tests -p 'test_zsh*.py' -v
```

使用合成证据和隔离交互式 Zsh，包括真实伪终端，不修改用户 hooks、历史或调度。
覆盖多行与复合输入、别名原文、执行前目录、退出码与 EOF、原生历史对照、
已有 hooks、暂停恢复、脱敏、文件权限、固定日期、位置文件和复盘准备。
