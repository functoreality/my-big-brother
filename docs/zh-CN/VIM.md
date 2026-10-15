# Vim 和 Neovim 记录

[English](../VIM.md) | 简体中文

My Big Brother 读取独立发布的
[session-recorder.vim](https://github.com/functoreality/session-recorder.vim)
插件生成的编辑器会话。用你的插件管理器安装完整仓库。
主项目包含读取器，不内置这个插件。

## 明确选择是否记录

安装 Agent 应检查 Vim/Neovim 可执行文件、已有编辑器配置或插件安装，
也可以询问用户是否经常使用。这些线索用于推荐插件，不能当作记录授权。
询问用户是否愿意把编辑器记录纳入分析。
如果拒绝，按用户选择保留原配置或禁用 `vim` 输入，不修改编辑器设置。

说明插件会保存原始文本、已保存的 diff、路径和光标行信息，
光标行可能含有未保存文本。让用户在打开私人文件前选择排除规则或关闭记录。

## 安装独立插件

先读插件当前的 [README](https://github.com/functoreality/session-recorder.vim#readme)，
确认要求和选项。保留已有配置，修改前备份，沿用用户的插件管理器。
如果使用 vim-plug，在已有插件声明块内加入：

```vim
Plug 'functoreality/session-recorder.vim'
```

执行该管理器的安装命令。
原生 packages 方式则把完整仓库克隆到有效 `packpath` 下的 `pack/*/start/` 目录。
不要只复制 `plugin/`、覆盖整个 vimrc、另装一套插件管理器，
也不要假定所有系统使用相同配置路径。
Neovim 可以使用 Vimscript 或 Lua 配置，应检查实际加载的文件并适配声明方式。

如果编辑器找不到所需 Python，可在插件加载前指定本系统的解释器，
同时保留其他已有选项：

```vim
let g:vim_session_recorder#config = {
    \ 'python_executable': '/absolute/path/to/python3',
    \}
```

## 共用原始日志位置

插件仅在启动时按三级优先级选择记录根目录：

1. Vim 配置中的 `record_dir`。
2. `C/raw-logs-path.txt` 中的一条 UTF-8 绝对路径。
3. 平台默认数据目录下的 `daily`。

三者都使用 `YYYY-MM-DD/vim/<会话>/` 结构，TXT 指定日期层之前的根目录。
要共用主项目的自定义数据根，将其 `daily` 路径写入 TXT。
若根目录不同于主项目的 `daily`，同时显式设置 `sources.vim.path` 指向同一位置。
插件不读取 `storage.json`，也不参与日期登记。
仅在启动时建立会话目录，退出时仍写该目录，不重载路径配置、不轮转，
也不重建被移除的会话目录。不区分共享或独立模式，不迁移或搜索旧布局。
更新完整插件。修改用户的编辑器配置或记录位置前先询问，保留排除规则和已有记录。
确保 GUI 编辑器、终端和调度器使用相同账号与位置配置。
WSL 和远程编辑器各有自己的运行环境。

## 验证后启用输入

安装或改配置后，请用户自行重开编辑器，不要关闭有未保存工作的编辑器。
在重开的编辑器中执行 `:RecorderStatus`，检查解析位置和记录错误。

用一个临时文件测试：打开，修改并保存一行，正常退出。
检查新会话中的 `record.json`、原始快照和修改 diff。
再在个人配置中设置 `sources.vim.enabled` 为 `true`，
对包含这个已关闭会话的日期运行 `prepare`，检查 Vim 条数、摘录和附件引用。
这些检查完成后，才能声称接入成功。

共享模式和独立模式都在打开已有文件时保存原始快照，
在编辑器退出时统一生成最终 diff 和 `record.json`。
不增加定时、读写或焦点检查点，也不按午夜分段。
退出前原始快照已可用于恢复，但读取器还没有最终 manifest 可供索引。
没有记录不意味着没有使用编辑器，整场 diff 也不能确定每项编辑的时刻或日期。
读取器查找全部保留日期中的相交会话，不能只查分析窗口覆盖的日期目录。
细节见[输入来源](INPUT-SOURCES.md)。
