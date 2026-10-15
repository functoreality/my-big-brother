# Vim and Neovim recording

English | [简体中文](zh-CN/VIM.md)

My Big Brother reads editor sessions from the independently released
[session-recorder.vim](https://github.com/functoreality/session-recorder.vim)
plugin. Install that whole repository through your editor's plugin manager.
The reader is included here, but the plugin is not bundled.

## Choose recording explicitly

The installing Agent should check for Vim/Neovim executables, an existing
editor configuration or plugin installation, or user-confirmed regular use.
These are reasons to offer the plugin, not permission to enable recording.
Ask whether the user wants editor records included. If they decline, leave
both the editor setup and the `vim` source unchanged or disabled as requested.

Explain that the plugin stores original text, saved diffs, file paths and
cursor-line context, which can include unsaved text. Let the user choose
exclusions or disable recording before opening private files.

## Install the separate plugin

Read the plugin's current [README](https://github.com/functoreality/session-recorder.vim#readme)
for requirements and options. Preserve the user's existing editor settings,
make a backup before editing, and use their existing plugin manager.
For vim-plug, add inside its existing plugin block:

```vim
Plug 'functoreality/session-recorder.vim'
```

Run that manager's installation command. With native packages, clone the
whole repository under a `pack/*/start/` directory on the active `packpath`.
Do not copy only `plugin/`, replace the user's vimrc, install a second plugin
manager, or assume the same configuration path on every system.
Neovim can use Vimscript or Lua configuration. Inspect which file is actually
loaded and adapt the manager declaration to that setup.

If the editor cannot find the intended Python, configure its native executable
before plugin loading, preserving any existing recorder options:

```vim
let g:vim_session_recorder#config = {
    \ 'python_executable': '/absolute/path/to/python3',
    \}
```

## Share the shared storage

The plugin uses the same `C/storage.json`, data root and fixed logical-day
boundary. V2-capable plugin versions register and write independent segments
under `daily/YYYY-MM-DD/vim/`. No extra Vim path variable is needed.
`record_dir` is an explicit standalone override and opts out of this lifecycle.
Ask before removing it or changing editor configuration. Preserve old records.
Update the complete plugin, including `python/storage.py`, before enabling v2.
See [Storage v2](STORAGE.md). Never use permanent results as a capture target.
Ensure GUI editors, shells and schedulers use the same account and location
settings. WSL and remote editors have their own environments.

## Verify before enabling the source

Ask the user to restart the editor after installation or configuration changes.
Do not close an editor with unsaved work. In the restarted editor,
`:RecorderStatus` reports the resolved location and recording errors.

Use a disposable file: open it, change and save one line, and exit normally.
Check for the new `record.json`, original snapshot and modification diff.
Then set `sources.vim.enabled` to `true` in the personal configuration and
run `prepare` for a date containing that closed session. Inspect the Vim
manifest count, excerpt and artifact references before claiming success.

Shared recording publishes periodic checkpoints and independent logical-day
segments. Standalone recording publishes at editor exit. Missing records do
not prove an absence of editor work. Checkpoint diffs and boundary gaps do not
establish the exact time of each edit. See [Input sources](INPUT-SOURCES.md).
