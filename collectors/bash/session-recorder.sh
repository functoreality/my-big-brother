# Source from interactive .bashrc after other prompt integrations.
[[ $- == *i* && ${MBB_BASH_RECORDING:-1} != 0 ]] || return 0
[[ ${__mbb_attached:-0} != 1 ]] || return 0

__mbb_prompt_declaration=$(declare -p PROMPT_COMMAND 2>/dev/null) || __mbb_prompt_declaration=
__mbb_prompt_flags=${__mbb_prompt_declaration#declare -}
__mbb_prompt_flags=${__mbb_prompt_flags%% *}
if [[ $__mbb_prompt_flags == *r* ]]; then
    printf '%s\n' 'my-big-brother: recorder not attached (PROMPT_COMMAND is readonly).' >&2
    return 0
fi
if [[ $__mbb_prompt_flags == *a* ]] &&
   (( BASH_VERSINFO[0] < 5 || (BASH_VERSINFO[0] == 5 && BASH_VERSINFO[1] < 1) )); then
    printf '%s\n' 'my-big-brother: recorder not attached (array PROMPT_COMMAND requires Bash 5.1+).' >&2
    return 0
fi
__mbb_python=${MBB_PYTHON:-python3}
__mbb_helper=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/recorder.py
__mbb_shell_pid=${BASHPID:-$$}
__mbb_session=$("$__mbb_python" "$__mbb_helper" session "$__mbb_shell_pid" "$PWD") || return 0

__mbb_read_history() {
    local line HISTTIMEFORMAT='%s '
    [[ -o history ]] || return 1
    line=$(builtin history 1)
    [[ $line =~ ^[[:space:]]*([0-9]+)[*]?[[:space:]]+([0-9]+)[[:space:]](.*)$ ]] || return 1
    __mbb_history_id=${BASH_REMATCH[1]}
    __mbb_history_epoch=${BASH_REMATCH[2]}
    __mbb_history_command=${BASH_REMATCH[3]}
}

# Keep duplicate input visible until the next command starts. Replay that input
# through Bash's own history builtin with the original settings before executing.
__mbb_ready() {
    local status=$? flag
    local -a flags
    __mbb_history_id=
    __mbb_read_history
    __mbb_last_history_id=$__mbb_history_id
    __mbb_control=${HISTCONTROL-}
    __mbb_control_set=${HISTCONTROL+x}
    __mbb_ignore=${HISTIGNORE-}
    __mbb_ignore_set=${HISTIGNORE+x}
    __mbb_size=${HISTSIZE-}
    __mbb_filtered_control=
    IFS=: read -r -a flags <<< "$__mbb_control"
    for flag in "${flags[@]}"; do
        case $flag in
            ignoredups|erasedups) continue ;;
            ignoreboth) flag=ignorespace ;;
        esac
        __mbb_filtered_control+=${__mbb_filtered_control:+:}$flag
    done
    __mbb_filtered_ignore=
    IFS=: read -r -a flags <<< "$__mbb_ignore"
    for flag in "${flags[@]}"; do
        [[ $flag == '&' ]] && continue
        __mbb_filtered_ignore+=${__mbb_filtered_ignore:+:}$flag
    done
    __mbb_temporary_history=0
    if [[ $__mbb_filtered_control != "$__mbb_control" || $__mbb_filtered_ignore != "$__mbb_ignore" ]]; then
        HISTCONTROL=$__mbb_filtered_control
        HISTIGNORE=$__mbb_filtered_ignore
        # A duplicate must not evict the oldest entry before native filtering.
        if [[ $__mbb_size =~ ^[0-9]+$ && $__mbb_size != 0 ]]; then
            HISTSIZE=$((10#$__mbb_size + 1))
        fi
        __mbb_temporary_history=1
    fi
    __mbb_pending=0
    __mbb_in_prompt=0
    return "$status"
}

__mbb_preexec() {
    local status=$?
    case ${FUNCNAME[1]-} in __mbb_*) return "$status" ;; esac
    case $1 in
        __mbb_saved_status=*|__mbb_prompt*) __mbb_in_prompt=1 ;;
    esac
    [[ $__mbb_in_prompt == 0 ]] || return "$status"
    __mbb_in_prompt=1
    if [[ $__mbb_temporary_history == 1 ]]; then
        if [[ $__mbb_control_set ]]; then HISTCONTROL=$__mbb_control; else unset HISTCONTROL; fi
        if [[ $__mbb_ignore_set ]]; then HISTIGNORE=$__mbb_ignore; else unset HISTIGNORE; fi
    fi
    if __mbb_read_history && [[ $__mbb_history_id != "$__mbb_last_history_id" ]]; then
        __mbb_pending=1
        if [[ $__mbb_temporary_history == 1 ]]; then
            builtin history -d "$__mbb_history_id"
            builtin history -s -- "$__mbb_history_command"
        fi
    fi
    if [[ $__mbb_temporary_history == 1 && $__mbb_size =~ ^[0-9]+$ && $__mbb_size != 0 ]]; then
        HISTSIZE=$__mbb_size
    fi
    return "$status"
}

__mbb_write() {
    printf '%s\0' "$__mbb_session" "$1" "$PWD" "${2-}" "${3-}" "${4-}" |
        "$__mbb_python" "$__mbb_helper" record
}

__mbb_in_prompt=1
__mbb_pending=0

__mbb_flush_history() {
    if [[ $__mbb_pending == 1 && ${MBB_BASH_RECORDING:-1} != 0 ]]; then
        __mbb_write command "$__mbb_history_command" "$1" "$__mbb_history_epoch"
    fi
    __mbb_pending=0
}

__mbb_prompt() {
    local status=$1
    __mbb_in_prompt=1
    __mbb_flush_history "$status"
    return "$status"
}

__mbb_on_exit() {
    local status=$?
    __mbb_flush_history "$status"
    __mbb_write session_end
    return "$status"
}

# trap -p supplies shell-quoted configuration, not recorded command data.
__mbb_previous_exit=$(trap -p EXIT)
if [[ -n $__mbb_previous_exit ]]; then
    __mbb_previous_exit=${__mbb_previous_exit#trap -- }
    eval "__mbb_previous_exit=${__mbb_previous_exit% EXIT}"
fi
trap '__mbb_on_exit'"${__mbb_previous_exit:+; $__mbb_previous_exit}" EXIT

__mbb_prompt_prefix='__mbb_saved_status=$?; __mbb_prompt "$__mbb_saved_status"'
__mbb_first_prefix='__mbb_saved_status=$?; __mbb_existing_debug=$(trap -p DEBUG); __mbb_bootstrap; __mbb_prompt "$__mbb_saved_status"'

__mbb_bootstrap() {
    if [[ -n $__mbb_existing_debug ]]; then
        __mbb_existing_debug=${__mbb_existing_debug#trap -- }
        eval "__mbb_existing_debug=${__mbb_existing_debug% DEBUG}"
    fi
    trap '__mbb_preexec "$BASH_COMMAND"'"${__mbb_existing_debug:+; $__mbb_existing_debug}" DEBUG
    if [[ $__mbb_prompt_flags == *a* ]]; then
        PROMPT_COMMAND=("$__mbb_prompt_prefix" "${__mbb_previous_prompt[@]}" __mbb_ready)
    else
        PROMPT_COMMAND="$__mbb_prompt_prefix"$'\n'"${__mbb_previous_prompt[0]-}"$'\n''__mbb_ready'
    fi
}

__mbb_previous_prompt=("${PROMPT_COMMAND[@]}")
if [[ $__mbb_prompt_flags == *a* ]]; then
    PROMPT_COMMAND=("$__mbb_first_prefix" "${__mbb_previous_prompt[@]}" __mbb_ready)
else
    PROMPT_COMMAND="$__mbb_first_prefix"$'\n'"${__mbb_previous_prompt[0]-}"$'\n''__mbb_ready'
fi
__mbb_attached=1
