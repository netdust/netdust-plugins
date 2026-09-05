#!/usr/bin/env bash
# Repo hygiene: marketplace.json must agree with every plugin's own manifest.
#
# A plugin's version is declared TWICE — in its .claude-plugin/plugin.json and
# in the marketplace entry that installs it. Bumping only the manifest leaves
# the marketplace advertising the old version, so `/plugin` sees no update and
# the change never reaches a machine. That happened to netdust-core (0.4.1 vs
# 0.5.0) and netdust-agent (0.21.3 vs 0.25.0) and would have silently withheld
# a day of work at install time.

set -uo pipefail
cd "$(dirname "$0")/../../.."
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n       %s\n' "$1" "${2:-}"; }

[ -f .claude-plugin/marketplace.json ] || { echo "  skip: not the marketplace repo"; echo "0 passed, 0 failed"; exit 0; }

python3 -c "import json" 2>/dev/null || { echo "  skip: no python3"; echo "0 passed, 0 failed"; exit 0; }

out=$(python3 - <<'PY'
import json, pathlib
d = json.load(open('.claude-plugin/marketplace.json'))
for e in d['plugins']:
    src = e.get('source', '')
    if not isinstance(src, str) or not src.startswith('./'):
        print(f"REMOTE\t{e['name']}\t{e['version']}\t-")
        continue
    pj = pathlib.Path(src[2:]) / '.claude-plugin' / 'plugin.json'
    if not pj.exists():
        print(f"MISSING\t{e['name']}\t{e['version']}\t{pj}")
        continue
    own = json.load(pj.open()).get('version', '?')
    print(f"{'OK' if own == e['version'] else 'DRIFT'}\t{e['name']}\t{e['version']}\t{own}")
PY
)

while IFS=$'\t' read -r status name mk own; do
    [ -z "$status" ] && continue
    case "$status" in
        OK)      ok "$name $mk matches its manifest" ;;
        DRIFT)   bad "$name versions agree" "marketplace says $mk, plugin.json says $own — a refresh would not install $own" ;;
        MISSING) bad "$name has a manifest" "no plugin.json at $own" ;;
        REMOTE)  ok "$name is a remote source (not version-checked here)" ;;
    esac
done <<<"$out"

# Every local source directory must exist, or the entry installs nothing.
while read -r src; do
    [ -z "$src" ] && continue
    [ -d "$src" ] && ok "source exists: $src" || bad "source exists: $src" "directory missing"
done < <(python3 -c "
import json
for e in json.load(open('.claude-plugin/marketplace.json'))['plugins']:
    s = e.get('source','')
    if isinstance(s,str) and s.startswith('./'): print(s)")

echo
printf '%s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
