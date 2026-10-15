# 可选的 Bash 活动记录

[English](../BASH.md) | 简体中文

Bash 采集器记录交互式命令活动，不读取或修改 Bash history。
它不依赖 `HISTCONTROL`、`HISTIGNORE`，也不依赖 history 是否开启。
重复执行的命令会产生重复记录。

这个采集器需要主动启用。仅使用 Agent 会话记录就可以使用 MVP。
未经本人同意，不要在他人的 shell 中安装它。

## 安装

需要 Bash 和 Python 3，推荐 Python 3.11 或更新版本。
旧 Python 版本未经验证，不保证兼容。
初始化 my-big-brother 后，在交互式 `.bashrc` 的末尾附近添加以下一行，
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

v2 模式读取 `C/storage.json`，共用工作日边界，登记后写入
`daily/YYYY-MM-DD/bash/`。命令按完成时刻归档，保留开始时间。
已放弃的日期直接跳过，不会重建。
附带的标准库协议不要求安装 Python 包。
没有 v2 配置时仍支持旧原始日志定位方式。
初始化及迁移见[存储 v2](STORAGE.md)。

新日志使用随机会话标识，POSIX 权限为 `0600`。
采集器不修改调用者的 umask 或已有文件权限。

每条 JSONL 记录包含 `event: "command"`、`session_id`、`started_at`、
`completed_at`、`cwd`、`command`、`exit_status`、`capture_scope` 和 `redacted`。
时间戳包含本地 UTC 偏移。`cwd` 是命令执行前的目录。
采集器不记录命令输出或终端截图。

## 捕获范围

这是轻量的活动线索，不是终端的完整记录。
DEBUG 钩子捕获提示符之后遇到的第一条简单命令。
下一个提示符出现时，采集器记录其开始时间，以及整条提交命令行的最终退出状态。
每条记录都明确标注 `capture_scope: "first-simple-command"`。

例如，一行输入执行两次 `printf` 时，`command` 字段只记录第一条简单命令，
而退出状态描述整行执行结果，包括第二次 `printf`。
管道、条件表达式、函数、别名、循环和多行输入也可能产生不完整或展开后的命令文本。
不要把这个字段当作用户原始输入的完整命令行，
也不要假定退出状态一定属于捕获的第一条命令。
函数体和子进程活动不会得到完整追踪。
分析器应在相关结论中说明这些证据限制。

如果命令使 shell 退出或被终止，导致下一个提示符没有出现，记录就不会写入。
会话结束事件也没有保证。因此，Bash 的 `exit` 命令通常不会出现在记录中。
采集器不修改 EXIT trap。

DEBUG 钩子在命令执行前取得时间戳。
这需要在命令开始时启动一个小型 Python 子进程，
并在下一个提示符出现时再启动一个。
对于耗时很短的命令，这可能带来可察觉的开销。

## 钩子兼容性

已有的标量或数组形式 `PROMPT_COMMAND` 钩子保持原有顺序，
并接收前一条命令的退出状态。
采集器不修改 history 选项、history 条目、EXIT trap 或 shell 的 umask。
重复加载采集器不会添加第二个钩子。
数组形式的提示符钩子需要 Bash 5.1 或更新版本，
旧版 Bash 可以使用标量钩子。

遇到以下情况时，采集器会拒绝挂接：

- 已有 DEBUG trap，包括基于 bash-preexec 的集成。
- 开启 `functrace`（`set -T`），因为它会改变 DEBUG 的继承方式。
- 非空的 `PS0` 命令执行前集成。
- 只读的 `PROMPT_COMMAND`。

采集器会显示可处理的诊断信息，并保留已有集成。
Bash 在加载脚本期间会暂时隐藏调用方的 DEBUG trap。
为了避免覆盖这种 trap，检查和挂接会推迟到下一个顶层提示符。
因此，诊断信息可能在加载脚本结束后才出现。

在这个采集器之后安装其他提示符或 DEBUG 集成，可能使记录失效或产生冲突。
请最后加载采集器。
不支持在会话期间动态修改 `functrace`、`PS0` 或提示符钩子。
修改集成后，请启动新的 shell。

## 隐私与停用

命令可能包含私有路径、项目名称、凭据或个人文本。
文件保存在本地，但选中的原始证据可能随后发送给已配置的分析器服务商。
请只在适合的环境中启用这个采集器。

辅助程序检测到常见的密码、token、secret、API key、Authorization、
sshpass 或 URL 密码模式时，会用脱敏标记替换整条命令。
这只是尽力而为的过滤。
任意位置参数中的秘密、特殊格式、编码后的值和其他私人文本仍可能被记录。
因为采集器不使用 history，所以 history 的隐私过滤选项对它不起作用。

输入敏感命令前，先停用记录：

```bash
MBB_BASH_RECORDING=0
# 在这里输入敏感命令。
MBB_BASH_RECORDING=1
```

如果希望在新 shell 中停用它，请在加载前导出 `MBB_BASH_RECORDING=0`。
卸载时，移除加载脚本的那一行，并启动新的 shell。
MVP 不会自动删除原始日志。

## 测试

在项目根目录运行隔离的兼容性测试：

```bash
python3 -m unittest discover -s tests -p test_bash_recorder.py -v
```

Linux 测试使用临时的 home、配置和数据目录，
交互式 Bash 子进程，以及一个伪终端会话。
覆盖重复命令、history 过滤与停用、标量与数组提示符钩子、退出状态保留、
已有 DEBUG 和 EXIT trap、umask 保留、脱敏、停用、路径文件校验和重复挂接。
测试使用隔离的子进程，不会在你的 shell 中安装采集器。
