# Sourced by the hc tests: a throwaway hc core that can never be Stefan's.
# hc refuses a socket path over 107 bytes, hence the short /tmp dir.
scratch_hc_start() {
    HC_SCRATCH=$(mktemp -d /tmp/hcXXXX)
    export HC_SESSION=t
    export XDG_CONFIG_HOME=$HC_SCRATCH/config XDG_STATE_HOME=$HC_SCRATCH/state
    export XDG_RUNTIME_DIR=$HC_SCRATCH/run XDG_DATA_HOME=$HC_SCRATCH/data
    unset HC_TERMINAL_ID
    mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"
    trap scratch_hc_stop EXIT
}

scratch_hc_stop() {
    hc server stop >/dev/null 2>&1
    rm -rf "$HC_SCRATCH"
}

hc() {
    case "${HC_SESSION:-}:${XDG_RUNTIME_DIR:-}" in
        t:"${HC_SCRATCH:-/nonexistent}"/run) command hc "$@" ;;
        *) echo "refused: hc outside this test's scratch core" >&2; return 97 ;;
    esac
}

command -v hc >/dev/null || { echo "FAIL hc is not on PATH; these tests need herdr-core" >&2; exit 1; }
