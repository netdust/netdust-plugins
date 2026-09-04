#!/usr/bin/env bash
# The branch flow, exercised for real in a throwaway repo with a bare origin
# (netdust-agent harness-inversion FR-23). Never contacts a server: no ddev, no
# ssh, no rsync — only git and the Makefile's flow targets.
#
# Asserts on RULES, never on this project's names: the temp site.yml declares
# its own three rungs. Runs from any project that carries this script; the
# vendored core and scripts/site under test are the ones of the calling project.
#
# The temp project pins STACK := generic on purpose. The flow verbs are
# stack-agnostic, and a stack layer would drag ddev into a test that must never
# need it.
set -uo pipefail
cd "$(dirname "$0")/../.."
PROJECT_CORE="$PWD/Makefile.netdust"
PROJECT_MK="$PWD/mk"
PROJECT_SITE="$PWD/scripts/site"
for f in "$PROJECT_CORE" "$PROJECT_SITE"; do
    [ -e "$f" ] || { echo "flow-test: missing $f — run 'make devops-update' first" >&2; exit 2; }
done

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); printf '  FAIL %s\n       %s\n' "$1" "${2:-}"; }
assert_ok()      { local l="$1"; shift; if out=$("$@" 2>&1); then ok "$l"; else fail "$l" "$out"; fi; }
assert_refuses() { local l="$1" pat="$2"; shift 2; local out; out=$("$@" 2>&1); local rc=$?
  if [ $rc -eq 0 ]; then fail "$l" "succeeded, expected refusal"
  elif printf '%s' "$out" | grep -q -- "$pat"; then ok "$l"
  else fail "$l" "refused, but not with \"$pat\": $out"; fi; }
assert_eq() { if [ "$2" = "$3" ]; then ok "$1"; else fail "$1" "expected [$2] got [$3]"; fi; }

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
export GIT_AUTHOR_NAME=flow GIT_AUTHOR_EMAIL=flow@test GIT_COMMITTER_NAME=flow GIT_COMMITTER_EMAIL=flow@test
export HOME="$TMP/home"; mkdir -p "$HOME"   # no user git config leaks in (hooks, signing, default branch)
git config --global init.defaultBranch main

# ── the repo under test ─────────────────────────────────────────────────────
git init -q --bare "$TMP/origin.git"
W="$TMP/work"; mkdir -p "$W/scripts" "$W/web" "$W/mk"
cp "$PROJECT_CORE" "$W/Makefile.netdust"
cp "$PROJECT_MK"/*.mk "$W/mk/"
cp "$PROJECT_SITE" "$W/scripts/site"; chmod +x "$W/scripts/site"
printf 'STACK := generic\ninclude Makefile.netdust\n' > "$W/Makefile"
cat > "$W/site.yml" <<'YAML'
site: {name: flowtest, domain: flowtest.test, risk: low}
structure: {type: bedrock, stack: generic, webroot: web}
deploy: {method: rsync, ssh_host: nowhere, wp_path: web/wp, content_dir: web/app, state_dir: /tmp/flowtest-state, payload: [app/mu-plugins]}
environments:
  development: {branch: development, url: https://dev.flowtest.test, path: /srv/dev, role: sandbox, confirm: false}
  staging:     {branch: staging,     url: https://stg.flowtest.test, path: /srv/stg, role: review,  confirm: false}
  production:  {branch: main,        url: https://flowtest.test,     path: /srv/prod, role: live,   confirm: true}
YAML
cd "$W"
git init -q && git add -A && git commit -q -m "scaffold"
git branch -q staging && git branch -q development
git remote add origin "$TMP/origin.git"
git push -q -u origin main staging development 2>/dev/null
M() { make --no-print-directory "$@"; }

echo "flow — feature"
assert_ok "make feature branches off origin/development" M feature name=one
assert_eq "…and lands on feature/one" "feature/one" "$(git branch --show-current)"
echo one > one.txt && git add one.txt && git commit -q -m "one"
assert_ok "make finish merges the feature up" M finish
assert_eq "…finish leaves you on development" "development" "$(git branch --show-current)"
assert_eq "…the commit is on development" "1" "$(git log --oneline origin/development | grep -c '^[0-9a-f]* one$')"
assert_eq "…and NOT on staging" "0" "$(git log --oneline origin/staging | grep -c '^[0-9a-f]* one$')"
assert_eq "…and NOT on main" "0" "$(git log --oneline origin/main | grep -c '^[0-9a-f]* one$')"

echo
echo "flow — hotfix"
git checkout -q main
assert_ok "make hotfix branches off origin/main" M hotfix name=fix
echo fix > fix.txt && git add fix.txt && git commit -q -m "fix"
assert_ok "make finish on a hotfix" M finish
assert_eq "…the fix is on main" "1" "$(git log --oneline origin/main | grep -c '^[0-9a-f]* fix$')"
assert_eq "…and merged back down into staging" "1" "$(git log --oneline origin/staging | grep -c '^[0-9a-f]* fix$')"
assert_eq "…and into development" "1" "$(git log --oneline origin/development | grep -c '^[0-9a-f]* fix$')"

echo
echo "flow — refusals on a rung"
git checkout -q development
assert_refuses "finish refuses on a rung branch" "finish works on feature" M finish
assert_refuses "save refuses on a rung branch, naming make feature" "make feature name=" M save
git checkout -q main
assert_refuses "save refuses on the production branch too" "deploy-only" M save
assert_eq "…and did not move you off it" "main" "$(git branch --show-current)"
assert_eq "…and created no branch" "0" "$(git branch --list develop | wc -l | tr -d ' ')"

echo
echo "flow — the deploy gate"
git checkout -q development
echo dirty > dirty.txt
assert_refuses "deploy gate refuses a dirty tree" "Uncommitted" M _deploy-gate env=development
rm dirty.txt
assert_refuses "deploy gate refuses the wrong branch" "deploys from" M _deploy-gate env=staging
git checkout -q -b feature/unpushed && echo u > u.txt && git add u.txt && git commit -q -m u
git checkout -q development && git merge -q --no-ff feature/unpushed -m "local only"
assert_refuses "deploy gate refuses an unpushed HEAD" "push before deploying" M _deploy-gate env=development
git push -q origin development
assert_ok "deploy gate passes clean + right branch + pushed" M _deploy-gate env=development

echo
echo "flow — a confirming verb needs a terminal (C1)"
assert_refuses "echo yes | make release is refused" "needs a terminal" bash -c 'echo yes | make --no-print-directory release'
assert_refuses "make release < file is refused" "needs a terminal" bash -c 'echo yes > /tmp/flow-yes.$$; make --no-print-directory release < /tmp/flow-yes.$$; rc=$?; rm -f /tmp/flow-yes.$$; exit $rc'
assert_eq "…and main did not move" "$(git rev-parse origin/main)" "$(git rev-parse main)"

echo
echo "flow — a rung with local-only commits refuses the flow (I3)"
git checkout -q development && echo stray > stray.txt && git add stray.txt && git commit -q -m "stray on a rung"
assert_refuses "make feature refuses while development carries an unpushed commit" "not on origin" M feature name=three
git checkout -q main && git branch -f development origin/development && git checkout -q development
assert_ok "…after resetting the rung to origin the flow runs again" M feature name=three
git checkout -q development && git branch -D feature/three >/dev/null 2>&1

echo
echo "flow — doctor/status say where you are"
assert_eq "flow state names the role" "1" "$(M _flow-state | grep -c 'rung:development')"
assert_eq "flow state names the next verb" "1" "$(M _flow-state | grep -c 'make feature name=')"

echo
echo "flow — without origin every verb refuses by name"
git remote remove origin
for v in "feature name=two" "hotfix name=two" "finish" "promote name=one" "release"; do
  assert_refuses "no origin: make $v" "no 'origin' remote" M $v
done
assert_refuses "no origin: the deploy gate" "no 'origin' remote" M _deploy-gate env=development
assert_eq "flow state shows origin MISSING" "1" "$(M _flow-state | grep -c 'MISSING')"

echo
printf 'flow-test: %d ok, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
