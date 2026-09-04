#!/usr/bin/env bash
# RED-first test for work-audit.sh — builds a repo carrying every drift shape this
# session actually found, then asserts the audit names each one.
set -uo pipefail

# Defaults to the sibling script. Resolved ABSOLUTE — the fixture cd's away, so a
# relative path silently becomes "no such file" and every assertion fails as RED.
AUDIT="${1:-$(dirname "$0")/../dist/scripts/work-audit.sh}"
AUDIT="$(cd "$(dirname "$AUDIT")" && pwd)/$(basename "$AUDIT")"
[ -f "$AUDIT" ] || { echo "no such script: $AUDIT" >&2; exit 2; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# A bare repo standing in for origin, and a clone that drifts away from it.
git init -q --bare "$TMP/origin.git"
git clone -q "$TMP/origin.git" "$TMP/work" 2>/dev/null
cd "$TMP/work" || exit 2
git config user.email t@t.t; git config user.name T

echo base > README.md && git add README.md && git commit -qm "base"
git push -q origin HEAD:main 2>/dev/null
git branch -q -M main
git branch --set-upstream-to=origin/main main 2>/dev/null

# 3. a remote branch fully merged into main — pushed from the BASE commit, BEFORE
#    main moves, so it is genuinely an ancestor. (Pushing it after the unpushed
#    commit would put that commit on a remote and unplant drifts 1 and 2.)
git push -q origin main:chore/already-merged 2>/dev/null
# 1. an unpushed commit on main
echo more >> README.md && git commit -qam "unpushed work"
# 2. a local branch that never reached the remote, carrying that commit
git branch feature/never-pushed
# 4. an untracked file (the ntdst-baseline spec shape)
echo "a 35KB spec nobody committed" > unsaved-spec.md
# 5. a staged-but-never-committed file (the dangling-blob shape)
echo "staged, never committed" > staged-only.md && git add staged-only.md

out="$("$AUDIT" 2>&1)"; rc=$?

fail=0
check() { # $1 = grep pattern, $2 = what it proves
  if printf '%s' "$out" | grep -qiE "$1"; then
    echo "  PASS  $2"
  else
    echo "  FAIL  $2  (no match for /$1/)"; fail=$((fail + 1))
  fi
}

echo "--- work-audit against a repo with five planted drifts:"
check 'unpushed|ahead'                    "reports the unpushed commit"
check 'feature/never-pushed'              "names the branch with no upstream"
check 'chore/already-merged'              "names the merged remote branch"
check 'unsaved-spec\.md|untracked'        "reports uncommitted work"
check 'staged-only\.md|staged'            "reports the staged-never-committed file"
[ "$rc" -ne 0 ] && echo "  PASS  exits non-zero when drift is found" \
                || { echo "  FAIL  exited 0 despite drift"; fail=$((fail + 1)); }

echo
if [ "$fail" -gt 0 ]; then echo "RED: $fail assertion(s) failing"; exit 1; fi
echo "GREEN: all assertions pass"; exit 0
