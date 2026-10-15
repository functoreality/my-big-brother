# Source this file from interactive Bash after other prompt integrations.
# Keep history and EXIT traps entirely under the user's control.
[[ $- == *i* ]] || return 0
[[ ${MBB_BASH_RECORDING:-1} != 0 ]] || return 0
[[ ${__mbb_attached:-0} != 1 ]] || return 0

if [[ $- == *T* || -n ${PS0-} ]]; then
    printf '%s\n' 'my-big-brother: recorder not attached (existing DEBUG trap, functrace, or PS0). Disable recording or use a shell without that integration.' >&2
    return 0
fi
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
if ! "$__mbb_python" "$__mbb_helper" check; then
    printf '%s\n' 'my-big-brother: recorder not attached. Fix the diagnostic above and source it again.' >&2
    return 0
fi
__mbb_shell_pid=${BASHPID:-$$}
__mbb_session=$("$__mbb_python" "$__mbb_helper" session "$__mbb_shell_pid") || return 0
__mbb_in_prompt=1
__mbb_pending=0
__mbb_busy=0

__mbb_debug() {
    [[ $__mbb_busy == 0 ]] || return 0
    case $1 in
        __mbb_saved_status=*|__mbb_prompt*) __mbb_in_prompt=1; return 0 ;;
        __mbb_ready*) return 0 ;;
    esac
    [[ $__mbb_in_prompt == 0 && $__mbb_pending == 0 ]] || return 0
    [[ ${MBB_BASH_RECORDING:-1} != 0 ]] || return 0
    __mbb_busy=1
    __mbb_command=$1
    __mbb_cwd=$PWD
    __mbb_started=$("$__mbb_python" "$__mbb_helper" time)
    __mbb_pending=1
    __mbb_busy=0
    return 0
}

__mbb_prompt() {
    local status=$1
    __mbb_in_prompt=1
    if [[ $__mbb_pending == 1 ]]; then
        if [[ ${MBB_BASH_RECORDING:-1} != 0 ]]; then
            printf '%s\0' "$__mbb_session" "$__mbb_started" "$__mbb_cwd" "$status" "$__mbb_command" |
                "$__mbb_python" "$__mbb_helper" record
        fi
        __mbb_pending=0
    fi
    return "$status"
}

__mbb_ready() {
    local status=$?
    __mbb_in_prompt=0
    return "$status"
}

# Bash hides a caller's DEBUG trap while sourcing a file. Probe it at the next
# top-level prompt instead, where the original trap is visible again.
__mbb_previous_prompt=("${PROMPT_COMMAND[@]}")
__mbb_prompt_prefix='__mbb_saved_status=$?; __mbb_prompt "$__mbb_saved_status"'
__mbb_first_prefix='__mbb_saved_status=$?; __mbb_existing_debug=$(trap -p DEBUG); if __mbb_bootstrap; then trap '\''__mbb_debug "$BASH_COMMAND"'\'' DEBUG; fi; __mbb_prompt "$__mbb_saved_status"'

__mbb_bootstrap() {
    if [[ -n $__mbb_existing_debug ]]; then
        printf '%s\n' 'my-big-brother: recorder not attached (existing DEBUG trap). Original hooks remain active.' >&2
        if [[ $__mbb_prompt_flags == *a* ]]; then
            PROMPT_COMMAND=("${__mbb_previous_prompt[@]}")
        else
            PROMPT_COMMAND=${__mbb_previous_prompt[0]-}
        fi
        __mbb_attached=0
        return 1
    fi
    if [[ $__mbb_prompt_flags == *a* ]]; then
        PROMPT_COMMAND=("$__mbb_prompt_prefix" "${__mbb_previous_prompt[@]}" __mbb_ready)
    else
        PROMPT_COMMAND="$__mbb_prompt_prefix"$'\n'"${__mbb_previous_prompt[0]}"$'\n''__mbb_ready'
    fi
    return 0
}

if [[ $__mbb_prompt_flags == *a* ]]; then
    PROMPT_COMMAND=("$__mbb_first_prefix" "${__mbb_previous_prompt[@]}" __mbb_ready)
else
    PROMPT_COMMAND="$__mbb_first_prefix"$'\n'"${__mbb_previous_prompt[0]}"$'\n''__mbb_ready'
fi
__mbb_attached=1
