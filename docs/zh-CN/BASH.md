# 可选的 Bash 活动记录

[English](../BASH.md) | 简体中文

Bash 采集器记录交互式 history 输入，以及会话开始、命令完成和正常结束事件。
复合输入保存完整内容，不再只记录第一条实际执行的简单命令。

这个采集器需要主动启用。仅使用 Agent 会话记录就可以使用 MVP。
未经本人同意，不要在他人的 shell 中安装它。

## 安装

需要 Bash 和 Python 3，推荐 Python 3.11 或更新版本。
旧 Python 版本未经验证，不保证兼容。
在交互式 `.bashrc` 的末尾附近添加以下一行，
放在其他提示符集成之后：

```bash
source "/absolute/path/to/my-big-brother/collectors/bash/session-recorder.sh"
```

在 macOS 上，应修改实际加载交互式 Bash 配置的启动文件。
登录 shell 可能读取 `.bash_profile`，而不是 `.bashrc`。
脚本使用 Bash 3.2 可用的语法，但本版本只在 Linux Bash 上执行过，
尚未验证 macOS 上的实际运行。
Windows 上的 WSL 使用 Linux 路径。
原生 Windows Python 与 Git Bash 的组合尚未测试。
这个采集器用于 Bash，不适用于 PowerShell 或 Zsh。

如果 `python3` 不是符合要求的 Python，在加载采集器之前配置其可执行文件：

```bash
export MBB_PYTHON="/absolute/path/to/python3"
source "/absolute/path/to/my-big-brother/collectors/bash/session-recorder.sh"
```

支持 Python 虚拟环境。辅助程序只使用标准库，不需要安装本项目的 Python 包。
克隆的项目应保持在 shell 配置所引用的位置。

## 保存位置与格式

每个开启记录的 Bash 进程只对应一个 JSONL，保存到
`raw-logs/YYYY-MM-DD/bash/`。日期取启用采集器时的本机自然日期。
启动时创建文件，Bash 只缓存这个文件的路径文本。
后续追加不重读路径配置，也不重新选择目录日期。
之后不因跨午夜、持续数月、执行 `cd`，
或共享位置配置改变而更换路径。命令起止时间始终记录真实时间。
文件或父目录被删除后停止追加，不重建它，也不改写到今天的目录。

采集器只需要 Python 标准库，可以独立使用，不要求安装主项目。
启动时读取一次 `C/raw-logs-path.txt`，缺失时使用平台数据目录下的 `raw-logs`。
TXT 只保存一行 UTF-8 绝对路径，不加引号、注释，不展开变量。
允许末尾一个 LF 或 CRLF，保留路径中的空格，已有文件格式错误时报告错误。
它不读取 `storage.json`，也不创建运行登记或用户配置。
主项目和 Vim 使用同一份路径文件。平台默认值与初始化见[存储说明](STORAGE.md)。

文件名为 `HH-MM-SS_<初始目录名>_<PID>.jsonl`，
例如 `09-30-12_my-project_12345.jsonl`。
时间取启用采集器的时刻，不是第一条命令的时间。
日期由父目录提供，文件名不附加时区或随机串。
若文件名已经存在，就追加 `_2`、`_3` 等数字，避免覆盖或混写其他会话。

目录提示只取初始工作目录的最后一级名称，不安全的文件名字符替换为 `_`。
超过 28 个字符时保留前 18 个和后 8 个，中间用 `..` 连接。
另外限制为 64 个 UTF-8 字节，保留头尾且不切断字符。
目录提示为空或路径过长时省略提示。
完整初始路径和带时区的启动时间只在 `session_start` 中写一次。
不为每条命令重复记录会话 ID、PID 或其他会话元数据。
新日志的 POSIX 权限为 `0600`，不修改调用者的 umask 或已有文件权限。

## 事件与时间

- `session_start`：`event`、`started_at` 和初始 `cwd`。
  开始采集时立即写入，不必等第一条长命令结束。
- `command`：`event`、`started_at`、`completed_at`、`cwd`、`command` 和 `exit_status`。
  开始时间来自秒级 Bash history 时间，完成时间在下一提示符或正常退出时观察。
  `cwd` 是整条输入开始执行前的 shell 目录。
  对 `cd child`，它表示从哪个目录发起切换。
  对 `cd child; run`，它只表示整条输入的初始目录，不代表每个内部命令的目录。
  不额外记录第二个目录字段。
- `session_end`：`event`、`ended_at` 和最终 `cwd`，正常退出时写入。
  `exit 7` 命令在结束事件前记录，并保留状态 7。

时间戳始终是真实本地时间，带 UTC 偏移，一个文件标识一场会话。
读取器查找全部保留的启动日期，按事件真实时间筛选。
更早的会话开始事件可以作为上下文，不把旧命令复制成当天活动。
进程被强制终止、崩溃或断电时，可能没有命令完成和会话结束事件。
这不是终端完整转录，也不实时写入每条命令的启动事件，不记录命令输出。

## history 兼容

重复输入、前导空格输入和匹配 `HISTIGNORE` 的命令都会写入 JSONL。
原生 history 仍按用户原有的 `HISTCONTROL`、`HISTIGNORE` 和容量设置处理。
`HISTSIZE=0`、未设置或清空 `HISTFILE`、`HISTFILESIZE=0` 都不阻止 JSONL 采集。
采集器不设置 `HISTFILE`，也不向它写入。

等待输入时暂时放宽 history 过滤，必要时预留一个位置。
命令执行前观察整条输入，恢复原过滤设置，再交给 Bash 自带的 history 机制处理。
原容量为零时，直接移除临时观察条目，不留在原生历史中。
之后恢复容量，用户命令与已有提示符钩子在原设置下执行。
不以 `BASH_COMMAND` 作为记录文本。

**已知缺口：** `set +o history` 关闭了获取输入所用的机制。
此时无法采集命令，只保留会话起止。采集器保留关闭状态，
用户重新开启该选项后恢复采集。这与禁止历史文件落盘不同，
是尚未解决的限制，不是有意设计的记录排除。

history 达到 `HISTSIZE` 上限时，为重复输入临时预留一个位置再恢复上限，
可能导致 Bash 重排历史编号。
历史内容和去重习惯保留，但 `!123` 等按编号展开可能指向不同条目。
若必须保持历史编号稳定，请不要安装此采集器。
这一取舍避免为观察重复命令而丢失最早的历史条目。
主动修改 history 的命令或扩展可能有额外交互，应先验证自己的集成。

## 钩子与停用

保留标量和数组 `PROMPT_COMMAND` 钩子的顺序及前一条命令的退出状态。
已有 DEBUG 和 EXIT 动作会串接执行，不直接覆盖丢弃。
Linux 隔离测试覆盖 `PS0`、functrace 和重复加载。
数组形式提示符钩子需要 Bash 5.1 或更新版本。
只读 `PROMPT_COMMAND` 无法安装。
不支持加载后动态替换提示符或 trap 集成，修改集成或升级采集器后请重开 shell。

临时观察完整输入要求 `HISTCONTROL`、`HISTIGNORE` 和有限的 `HISTSIZE` 可写。
持续记录仍需主动启用。
`MBB_BASH_RECORDING=0` 暂停命令记录，恢复为 `1` 后继续，正常结束仍写结束事件。
若要停用新会话，在加载前导出 `MBB_BASH_RECORDING=0`。
卸载时移除加载行并重开 shell，不会自动删除已有记录。

## 隐私

保留原有尽力而为的脱敏规则。
检测到 token、secret、password、API key 等名称的赋值、`sshpass` 或
`Authorization:` 时，整条命令替换为 `<redacted:possible-secret>`。
其他秘密和私密文本仍可能被记录。
history 排除不会停用采集。输入敏感内容前设 `MBB_BASH_RECORDING=0` 暂停，
之后设回 `1`。
选中的证据可能发送给已配置的分析器服务商，文件名也会显示目录提示。

## 为什么 Bash 记录器使用 Python

被加载的 Bash 脚本负责观察 shell 事件、完整 history 输入、退出状态和命令初始目录。
这些信息属于当前交互式 shell，必须由 Bash 钩子取得。
初始目录沿用已有的执行前钩子，仅保存一个 shell 变量，不新增 Python 调用。

Python 辅助程序负责 JSON 转义、Unicode 和多行文本、带 UTC 偏移的本地时间、
平台路径和文件追加。原个人脚本原本依赖 `/usr/bin/jq` 和 GNU 专有的 `date` 参数，
现在用 Python 标准库代替这些依赖，三平台使用同一套实现。

代价是需要 Python，在会话开始、命令完成和正常结束时启动辅助进程。
它不是常驻 Python 服务，也没有为记录初始目录额外启动 Python。
只有 Bash 钩子观察 shell 活动，辅助程序不执行采集到的命令，也不启动分析 Agent。
原生 macOS 和 Windows 的运行仍未经验证，具体范围见前文。

## 测试

```sh
python3 -m unittest discover -s tests -p test_bash_recorder.py -v
```

Linux 隔离测试覆盖原生 history 对照、重复策略、历史文件设置、过滤独立性、
复合和多行输入、
事件字段、已有钩子、退出状态、权限、固定启动日期和真实伪终端。
测试确认阻塞命令结束前已经存在会话开始事件。
不会修改真实 shell 配置、历史或定时任务。
