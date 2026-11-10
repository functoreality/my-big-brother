# Source from interactive .zshrc after other prompt integrations.
[[ -o interactive && ${MBB_ZSH_RECORDING:-1} != 0 ]] || return 0
[[ ${__mbbz_attached:-0} != 1 ]] || return 0

__mbbz_emit() {
    emulate -L zsh
    builtin printf '%s\0' "$__mbbz_record_file" "$1" "$2" "$3" "$4" "$5" |
        "$__mbbz_python" "$__mbbz_helper" record
}

__mbbz_finish_command() {
    emulate -L zsh
    if [[ $__mbbz_pending == 1 ]]; then
        __mbbz_pending=0
        __mbbz_emit command "$__mbbz_command_cwd" "$__mbbz_command" "$1" "$__mbbz_started"
    fi
    return 0
}

__mbbz_preexec() {
    emulate -L zsh
    # Observe the complete submitted input without modifying native history.
    __mbbz_pending=0
    if [[ ${MBB_ZSH_RECORDING:-1} != 0 ]]; then
        __mbbz_command=$1
        __mbbz_command_cwd=$PWD
        __mbbz_started=$EPOCHSECONDS
        __mbbz_pending=1
    fi
    return 0
}

__mbbz_precmd() {
    local __mbbz_status=$?
    emulate -L zsh
    __mbbz_finish_command "$__mbbz_status"
    return 0
}

__mbbz_zshexit() {
    local __mbbz_status=$?
    emulate -L zsh
    __mbbz_finish_command "$__mbbz_status"
    __mbbz_emit session_end "$PWD" '' '' ''
    return 0
}

__mbbz_attach() {
    emulate -L zsh
    local __mbbz_hook
    for __mbbz_hook in preexec_functions precmd_functions zshexit_functions; do
        if [[ ${(tP)__mbbz_hook} == *readonly* ]]; then
            builtin print -u2 -r -- "my-big-brother: readonly Zsh hook array: $__mbbz_hook"
            return 1
        fi
    done
    zmodload zsh/datetime || return 1
    autoload -Uz add-zsh-hook || return 1
    typeset -g __mbbz_python=${MBB_PYTHON:-python3}
    typeset -g __mbbz_helper=$1
    typeset -g __mbbz_record_file
    __mbbz_record_file=$("$__mbbz_python" "$__mbbz_helper" session "$$" "$PWD") || return 1
    typeset -g __mbbz_pending=0
    add-zsh-hook preexec __mbbz_preexec || return 1
    add-zsh-hook precmd __mbbz_precmd || return 1
    add-zsh-hook zshexit __mbbz_zshexit || return 1
    typeset -g __mbbz_attached=1
}

__mbbz_attach "${${(%):-%x}:A:h}/recorder.py" ||
    builtin print -u2 -r -- 'my-big-brother: Zsh recorder not attached.'
return 0
