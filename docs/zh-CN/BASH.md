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
`daily/YYYY-MM-DD/bash/`。日期取启用采集器时的本机自然日期。
启动时登记该日期并创建文件，之后不因跨午夜、持续数月、执行 `cd`，
或共享位置配置改变而更换路径。命令起止时间始终记录真实时间。
启动日期被删除或被新一代目录替换后，该会话停止写入，
既不重建旧目录，也不改写到今天的目录。
附带的标准库协议不要求安装 Python 包。
无需先安装或初始化主项目。可选的 `C/storage.json` 指定自定义数据根，
缺失时使用平台默认值，运行状态自动建立。已有配置无效或登记损坏时报告错误。
初始化说明见[存储 v2](STORAGE.md)。

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
  与原记录器一致，`cwd` 是执行后的目录，包括执行 `cd` 的情况。
- `session_end`：`event`、`ended_at` 和最终 `cwd`，正常退出时写入。
  `exit 7` 命令在结束事件前记录，并保留状态 7。

时间戳始终是真实本地时间，带 UTC 偏移，一个文件标识一场会话。
读取器查找全部保留的启动日期，按事件真实时间筛选。
更早的会话开始事件可以作为上下文，不把旧命令复制成当天活动。
进程被强制终止、崩溃或断电时，可能没有命令完成和会话结束事件。
这不是终端完整转录，也不实时写入每条命令的启动事件，不记录命令输出。

## history 兼容

`ignoredups`、`ignoreboth`、`erasedups`，以及 `HISTIGNORE` 的重复过滤项 `&`
都不影响 JSONL 记录每次重复执行，原生 history 仍按用户原规则去重。
其他 `HISTIGNORE` 模式和 `ignorespace`、`ignoreboth` 的前导空格排除继续有效。
关闭 history 或设置 `HISTSIZE=0` 时不记录命令，但仍保留会话起止事件。
采集器不会自行开启 history。

等待输入时，钩子暂时放宽重复过滤。
命令执行前恢复原设置，再将完整输入交给 Bash 自带的 history 机制处理。
不以 `BASH_COMMAND` 作为记录文本，已有提示符钩子也在原设置下执行。
JSONL 格式不随用户的 history 策略改变。

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

临时观察重复输入要求 `HISTCONTROL`、`HISTIGNORE` 和有限的 `HISTSIZE` 可写。
持续记录仍需主动启用。
`MBB_BASH_RECORDING=0` 暂停命令记录，恢复为 `1` 后继续，正常结束仍写结束事件。
若要停用新会话，在加载前导出 `MBB_BASH_RECORDING=0`。
卸载时移除加载行并重开 shell，不会自动删除已有记录。

## 隐私

保留原有尽力而为的脱敏规则。
检测到 token、secret、password、API key 等名称的赋值、`sshpass` 或
`Authorization:` 时，整条命令替换为 `<redacted:possible-secret>`。
其他秘密和私密文本仍可能被记录。
输入敏感内容前使用 history 排除或暂停记录。
选中的证据可能发送给已配置的分析器服务商，文件名也会显示目录提示。

## 测试

```sh
python3 -m unittest discover -s tests -p test_bash_recorder.py -v
```

Linux 隔离测试覆盖原生 history 对照、重复策略、隐私过滤、复合和多行输入、
事件字段、已有钩子、退出状态、权限、固定启动日期和真实伪终端。
测试确认阻塞命令结束前已经存在会话开始事件。
不会修改真实 shell 配置、历史或定时任务。
