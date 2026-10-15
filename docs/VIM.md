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

The plugin resolves its recording root once at startup:

1. Vim `record_dir`, if explicitly configured.
2. `C/raw-logs-path.txt`, containing one UTF-8 absolute path.
3. The platform data directory followed by `daily`.

All roots use `YYYY-MM-DD/vim/<session>/`. The TXT file names the root before
the date, so sharing a custom main-application data root means putting its
`daily` path in the locator. Keep `sources.vim.path` pointed at that same root
if it differs from the main application's daily directory.
The plugin does not read `storage.json` or participate in date registration.
It creates the session folder at startup and uses that exact folder at exit,
without reloading configuration, rotating or recreating a removed folder.
There is no managed/standalone split, migration or legacy-layout discovery.
Update the whole plugin. Preserve exclusions and existing records, and ask
before changing the user's editor configuration or recording destination.
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

Both shared and standalone recording snapshot existing files when opened and
publish the final diff and `record.json` at editor exit. There is no periodic,
read/write, or focus checkpoint and no midnight segmentation. Before exit,
the original snapshots already exist for recovery, but the reader has no
final manifest to index. Missing records do not prove an absence of editor
work. A whole-session diff cannot establish the exact time or day of each
edit. Readers search all retained dates for overlapping sessions rather than
only the review window's date folders. See [Input sources](INPUT-SOURCES.md).
