#!/usr/bin/env bash
# tests/yootheme/run.sh — the ntdst-yootheme scripts against hermetic fixtures.
#
# No WordPress, no network: the linter reads a fake parent theme under
# fixtures/theme whose element.php files carry the real 5.0.43 shapes (nested
# panels, child-prop fields, ${builder.*} references, render-only props).
set -u
cd "$(dirname "$0")"
SKILL=../../skills/ntdst-yootheme
LINT="php $SKILL/scripts/yoo-lint.php --theme=fixtures/theme"
fail=0
ok()   { echo "pass  $1"; }
bad()  { echo "FAIL  $1"; fail=1; }

# 1. the bad fixture is refused, naming every trap
out=$($LINT fixtures/bad.json 2>&1); rc=$?
[ $rc -eq 1 ] && ok "bad.json exits 1" || bad "bad.json exit $rc (want 1)"
for code in unknown-type unknown-prop no-version orphan-item layout-count lone-column \
            block-align-no-maxwidth bgcolor-needs-empty-style grid-over-6 parent-at-root \
            binding-args bare-featured-image row-in-column list-on-container unnamed-section; do
  grep -q " $code " <<<"$out" && ok "bad.json reports $code" || bad "bad.json misses $code"
done
grep -q "did you mean \`padding_top\`" <<<"$out" && ok "unknown-prop suggests the nearest prop" || bad "no suggestion for padding"
distinct=$(grep -oE '^(error|warn) +[a-z0-9-]+' <<<"$out" | awk '{print $2}' | sort -u | wc -l)
[ "$distinct" -ge 12 ] && ok "≥ 12 distinct codes ($distinct)" || bad "only $distinct distinct codes"

# 2. the good fixture passes clean
out=$($LINT fixtures/good.json 2>&1); rc=$?
[ $rc -eq 0 ] && ok "good.json exits 0" || bad "good.json exit $rc: $out"
grep -q "0 errors, 0 warnings" <<<"$out" && ok "good.json: 0 findings" || bad "good.json has findings: $out"

# 3. a helper-built section round-trips through the linter (T07)
if [ -f "$SKILL/scripts/yoo_layout.py" ]; then
  python3 - "$SKILL/scripts" <<'PY' > fixtures/.built.json
import sys, json; sys.path.insert(0, sys.argv[1])
import yoo_layout as y
sec = y.section("H1 · Hero — tekst", [y.row([y.column([y.headline("Hallo", element="h1", style="h1"), y.text("<p>Intro</p>"), y.button("Meer", "/meer/")], width_medium="1-2"), y.column([y.image("content/uploads/x.jpg", 628, 500)], width_medium="1-2")], layout="1-2,1-2", column_gap="large")])
print(json.dumps(y.wrap([sec], "5.0.43")))
PY
  out=$($LINT fixtures/.built.json 2>&1); rc=$?
  [ $rc -eq 0 ] && grep -q "0 errors, 0 warnings" <<<"$out" && ok "yoo_layout.py section lints clean" || bad "helper-built section: $out"
  for s in ../../skills/ntdst-yootheme/sections/*.json; do
    out=$($LINT "$s" 2>&1); rc=$?
    [ $rc -eq 0 ] && grep -q "0 errors, 0 warnings" <<<"$out" && ok "sections/$(basename $s) lints clean" || bad "sections/$(basename $s): $out"
  done
  rm -f fixtures/.built.json
fi

[ $fail -eq 0 ] && echo "yootheme tests: all green" || { echo "yootheme tests: FAILED"; exit 1; }
