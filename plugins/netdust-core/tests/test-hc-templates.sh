#!/usr/bin/env bash
# bin/hc-templates installs the role templates hc runs by name (hc-flow R3).
set -uo pipefail
cd "$(dirname "$0")"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n       %s\n' "$1" "${2:-}"; }
check() { if eval "$2"; then ok "$1"; else bad "$1" "${3:-}"; fi; }

REAL=$HOME/.config/herdr-core/templates
real_state() { ls -l --time-style=full-iso "$REAL" 2>&1; }
before=$(real_state)

. ./scratch-hc.sh
scratch_hc_start
BIN=../bin/hc-templates
TPL=../hc-templates

installed=$("$BIN" 2>&1); rc=$?
check "the installer exits 0" '[ $rc -eq 0 ]' "$installed"
check "it prints one line per installed name" '[ "$(sort <<<"$installed" | tr "\n" " ")" = "coder reviewer sparring " ]' "$installed"

json=$(hc templates --json)
field() { python3 -c 'import json,sys; t={x["name"]:x for x in json.load(sys.stdin)["templates"]}; print(t[sys.argv[1]][sys.argv[2]] if sys.argv[1] in t else "")' "$1" "$2" <<<"$json"; }
names=$(python3 -c 'import json,sys; print(" ".join(sorted(t["name"] for t in json.load(sys.stdin)["templates"])))' <<<"$json")
check "hc templates lists exactly coder, reviewer, sparring" '[ "$names" = "coder reviewer sparring" ]' "$names"
for n in coder reviewer sparring; do
    cmd=$(field $n command)
    check "$n: its command starts an interactive claude" '[[ "$cmd" == claude\ * ]]' "$cmd"
    check "$n: it carries a description" '[ -n "$(field $n description)" ]'
    check "$n: its body reports to the parent with hc send" 'grep -q "hc send" "$TPL/$n.md"'
    check "$n: its body says where the parent's address is (no \$parent exists in a child)" 'grep -qF "hc get \$HC_TERMINAL_ID" "$TPL/$n.md" && ! grep -qF "\$parent" "$TPL/$n.md"'
done
check "coder: it runs in auto mode, as the pair always does" '[[ "$(field coder command)" == *"--permission-mode auto"* ]]'
check "coder: it reports at the first working version" 'grep -q "first working version" "$TPL/coder.md"'
for n in reviewer sparring; do
    check "$n: read-only by tool list" '[[ "$(field $n command)" == *"--disallowedTools Edit Write NotebookEdit"* ]]' "$(field $n command)"
done

out=$("$BIN" --on nosuchmachine 2>&1); rc=$?
check "--on an unknown machine exits non-zero" '[ $rc -ne 0 ]' "$out"

refused() { (export "$1"="$2"; hc ls >/dev/null 2>&1); [ $? -eq 97 ]; }
check "hc refuses a session that is not the scratch one" 'refused HC_SESSION default'
check "hc refuses a runtime dir that is not the scratch one" 'refused XDG_RUNTIME_DIR "$HC_SCRATCH/elsewhere"'

check "the real templates dir is untouched" '[ "$(real_state)" = "$before" ]' "$(real_state)"

echo "$PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
