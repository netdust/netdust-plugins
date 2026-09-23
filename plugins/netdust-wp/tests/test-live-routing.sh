#!/usr/bin/env bash
# tests/test-live-routing.sh — the files a session reads name only what exists.
# Lessons, evals and memory are history and may keep the old names.
set -u
cd "$(dirname "$0")/.." || exit 1
fail=0
ok()  { printf 'pass\t%s\n' "$1"; }
bad() { printf 'FAIL\t%s\n' "$1"; fail=1; }

LIVE="CLAUDE.md README.md templates/*.tmpl commands/*.md skills/*/SKILL.md"

[ ! -e skills/wp-plan-requirements ] && ok "wp-plan-requirements is retired" \
    || bad "skills/wp-plan-requirements still exists — the plan requirements live in netdust-gates' WordPress pack"

for name in netdust-agent harnessed-development wp-plan-requirements; do
    # shellcheck disable=SC2086
    hits=$(grep -lF "$name" $LIVE 2>/dev/null)
    [ -z "$hits" ] && ok "no live file names $name" || bad "$name named in: $(echo $hits)"
done

exit $fail
