#!/usr/bin/env bash
# yootheme-cases.sh — the ntdst-yootheme v2 behaviours are pinned as eval cases and the
# two plugins carry the new version everywhere a version is declared.
set -u
cd "$(dirname "$0")/../../.."   # repo root
fail=0
ids=$(python3 - <<'PY'
import json
d = json.load(open('plugins/netdust-wp/evals/behavioral-lessons.json'))
want = ['yoo-listing-binds-item','yoo-parent-at-template-root','yoo-binding-arguments-key','yoo-never-acf','yoo-module-not-custom-source','yoo-section-style-inverts','yoo-measure-not-grep','yoo-builder-page-no-content-binding']
have = {c['id'] for c in d['cases']}
missing = [w for w in want if w not in have]
for c in d['cases']:
    if c['id'] in want:
        for k in ('skill','lesson','prompt','baseline_ref','with_skill_assertion','must_contain','context_after'):
            if k not in c: missing.append(f"{c['id']}:{k}")
print(' '.join(missing))
PY
)
[ -z "$ids" ] && echo "ok    8 yoo- cases present with the runner's keys" || { echo "MISS  $ids"; fail=1; }
v() { python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['version'])" "$1"; }
mv() { python3 -c "import json,sys; print(next(p['version'] for p in json.load(open('.claude-plugin/marketplace.json'))['plugins'] if p['name']==sys.argv[1]))" "$1"; }
[ "$(v plugins/netdust-wp/.claude-plugin/plugin.json)" = "1.1.2" ] && [ "$(mv netdust-wp)" = "1.1.2" ] && echo "ok    netdust-wp 1.1.2 in plugin.json and marketplace.json" || { echo "MISS  netdust-wp version ($(v plugins/netdust-wp/.claude-plugin/plugin.json) / $(mv netdust-wp))"; fail=1; }
[ "$(v plugins/netdust-agent/.claude-plugin/plugin.json)" = "0.21.3" ] && [ "$(mv netdust-agent)" = "0.21.3" ] && echo "ok    netdust-agent 0.21.3 in plugin.json and marketplace.json" || { echo "MISS  netdust-agent version ($(v plugins/netdust-agent/.claude-plugin/plugin.json) / $(mv netdust-agent))"; fail=1; }
[ $fail -eq 0 ] && echo "yootheme-cases: green" || { echo "yootheme-cases: RED"; exit 1; }
