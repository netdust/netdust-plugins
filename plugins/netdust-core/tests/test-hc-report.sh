#!/usr/bin/env bash
# The report mechanism the roles rely on: parent → child → hc send → hc wait (hc-flow R4).
# Plain programs stand in for agents; tags and notes need a status-reporting agent (the live check).
set -uo pipefail
cd "$(dirname "$0")"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n       %s\n' "$1" "${2:-}"; }
check() { if eval "$2"; then ok "$1"; else bad "$1" "${3:-}"; fi; }

. ./scratch-hc.sh
scratch_hc_start

parent=$(hc run --bg --name parent --json bash -c \
    'hc run --bg --name child sh -c "hc send $HC_TERMINAL_ID review-done-42"; hc wait --children any; echo "wait-rc=$?"' |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["address"])')
hc wait parent --timeout 30 >/dev/null 2>&1
screen=$(hc read parent)
check "the parent received the child's report" 'grep -q review-done-42 <<<"$screen"' "$screen"
check "hc wait --children any saw the child exit" 'grep -q "exited (exit 0" <<<"$screen"' "$screen"
check "the wait returned 0" 'grep -q "wait-rc=0" <<<"$screen"' "$screen"

child_parent=$(hc ls --all --json | python3 -c 'import json,sys; print(next((t.get("parent","") for t in json.load(sys.stdin)["terminals"] if t["name"]=="child"), ""))')
check "hc ls --all shows the child under the parent" '[ -n "$parent" ] && [ "$child_parent" = "$parent" ]' "parent=$parent child.parent=$child_parent"

echo "$PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
