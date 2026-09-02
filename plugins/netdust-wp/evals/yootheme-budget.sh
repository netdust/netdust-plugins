#!/usr/bin/env bash
# yootheme-budget.sh — the ntdst-yootheme skill stays small enough to read.
#
# A page-build session loads SKILL.md, workflow.md, lessons.md, the builder-json
# and content-binding references. On 2026-09-02 that was 88,000 bytes (≈28k tokens)
# before any work started. This gate holds the load at ≤ 55,000 (the references keep their prop tables) and each router
# file at its own ceiling, and checks that every `yoo-lint: <code>` lessons.md
# points at exists in the linter — a lesson naming a check nobody wrote is prose.
set -u
cd "$(dirname "$0")/../skills/ntdst-yootheme"
fail=0
size() { wc -c < "$1" 2>/dev/null || echo 999999; }
check() { local n=$(size "$1"); if [ "$n" -le "$2" ]; then echo "ok    $1 = $n B (≤ $2)"; else echo "OVER  $1 = $n B (> $2)"; fail=1; fi; }

[ -f references/workflow.md ] && echo "ok    references/workflow.md exists" || { echo "MISS  references/workflow.md"; fail=1; }
check SKILL.md 7000
check lessons.md 18000
check references/workflow.md 9000
load=0; for f in SKILL.md references/workflow.md lessons.md references/yootheme-builder-json.md references/yootheme-content-binding.md; do load=$((load + $(size "$f"))); done
if [ "$load" -le 55000 ]; then echo "ok    page-build load = $load B (≤ 55000)"; else echo "OVER  page-build load = $load B (> 55000)"; fail=1; fi

for code in $(grep -oE 'yoo-lint: *`?[a-z0-9-]+' lessons.md | sed -E 's/yoo-lint: *`?//' | sort -u); do
  grep -q "'$code'" scripts/yoo-lint.php && echo "ok    lessons cites lint code $code" || { echo "MISS  lessons cites unknown lint code $code"; fail=1; }
done
[ $fail -eq 0 ] && echo "yootheme-budget: within budget" || { echo "yootheme-budget: OVER"; exit 1; }
