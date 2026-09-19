#!/usr/bin/env bash
# The branch flow, exercised for real in a throwaway repo with a bare origin
# (netdust-agent harness-inversion FR-23). Never contacts a server: no ddev, no
# ssh, no rsync — only git and the Makefile's flow targets. The vendored core
# and scripts/site under test are the ones of the calling project.
#
# Asserts on RULES, never on this project's names: the temp site.yml declares
# its own staging and production, and pins STACK := generic — a stack layer
# would drag ddev into a test that must never need it.
set -uo pipefail
cd "$(dirname "$0")/../.."
PROJECT_CORE="$PWD/Makefile.netdust"
PROJECT_MK="$PWD/mk"
PROJECT_SITE="$PWD/scripts/site"
for f in "$PROJECT_CORE" "$PROJECT_SITE"; do
    [ -e "$f" ] || { echo "flow-test: missing $f — run 'make devops-update' first" >&2; exit 2; }
done
command -v script >/dev/null || { echo "flow-test: needs script(1) from util-linux" >&2; exit 2; }

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); printf '  FAIL %s\n       %s\n' "$1" "${2:-}"; }
assert_ok()      { local l="$1"; shift; if out=$("$@" 2>&1); then ok "$l"; else fail "$l" "$out"; fi; }
assert_refuses() { local l="$1" pat="$2"; shift 2; local out; out=$("$@" 2>&1); local rc=$?
  if [ $rc -eq 0 ]; then fail "$l" "succeeded, expected refusal"
  elif printf '%s' "$out" | grep -q -- "$pat"; then ok "$l"
  else fail "$l" "refused, but not with \"$pat\": $out"; fi; }
assert_eq() { if [ "$2" = "$3" ]; then ok "$1"; else fail "$1" "expected [$2] got [$3]"; fi; }
has()   { printf '%s' "$1" | grep -qF -- "$2" && echo 1 || echo 0; }
strip() { sed 's/\x1b\[[0-9;]*m//g'; }

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
# The server-touching leaves become no-ops here, in the project's own Makefile.
# Each records its call, so a case can count the backups and deploys it caused.
LEAVES="$TMP/leaves.log"; : > "$LEAVES"
cat > "$W/Makefile" <<MK
STACK := generic
include Makefile.netdust
_deploy-transport _deploy-ledger _deploy-opcache _backup-data _backup-payload:
	@echo '\$@ \$(env)' >> $LEAVES
MK
cat > "$W/site.yml" <<'YAML'
site: {name: flowtest, domain: flowtest.test, risk: low}
structure: {type: bedrock, stack: generic, webroot: web}
deploy: {method: rsync, ssh_host: nowhere, wp_path: web/wp, content_dir: web/app, state_dir: /tmp/flowtest-state, payload: [app/mu-plugins]}
environments:
  staging:    {branch: staging, url: https://stg.flowtest.test, path: /srv/stg, role: review, confirm: false}
  production: {branch: main,    url: https://flowtest.test,     path: /srv/prod, role: live, confirm: true}
YAML
cd "$W"
git init -q && git add -A && git commit -q -m "scaffold"
git branch -q staging
git remote add origin "$TMP/origin.git"
git push -q -u origin main staging 2>/dev/null
# make warns on every run that the leaves above override the core's recipes.
M() { make --no-print-directory "$@" 2>&1 | grep -v 'recipe for target'; return "${PIPESTATUS[0]}"; }
Y() { script -qec "$*" /dev/null <<< yes; }
N() { script -qec "$*" /dev/null <<< no; }

echo "flow — feature branches from production (FR-1)"
# Staging has to carry something production does not, or branching off the
# wrong rung is indistinguishable from branching off the right one.
git checkout -q -b ahead origin/main && echo ahead > ahead.txt && git add ahead.txt
git commit -q -m ahead && git push -q origin HEAD:refs/heads/staging
git checkout -q main && git branch -q -D ahead && git fetch -q origin
assert_eq "setup: origin/staging carries a commit production does not" "1" \
  "$([ "$(git rev-parse origin/staging)" != "$(git rev-parse origin/main)" ] && echo 1)"
BEFORE=$(git ls-remote origin)
assert_ok "make feature name=one" M feature name=one
assert_eq "…on feature/one, at origin/main's tip, carrying nothing off staging" \
  "feature/one $(git rev-parse origin/main) 0" \
  "$(git branch --show-current) $(git merge-base feature/one origin/main) $(git merge-base --is-ancestor origin/staging feature/one && echo 1 || echo 0)"
assert_eq "…and says so, naming no other rung" "1 0" \
  "$(has "$out" 'branched from origin/main') $(has "$out" 'origin/staging')"
assert_eq "…and origin is unchanged — starting work pushes nothing" "$BEFORE" "$(git ls-remote origin)"
git push -q origin feature/one

echo; echo "flow — hotfix branches from production"
git checkout -q main
assert_ok "make hotfix name=fix" M hotfix name=fix
assert_eq "…on hotfix/fix, at origin/main's tip" "hotfix/fix $(git rev-parse origin/main)" \
  "$(git branch --show-current) $(git rev-parse HEAD)"
assert_eq "…and names a route the flow still has" "1 0" \
  "$(has "$out" 'make ship') $(has "$out" 'make finish')"
git checkout -q main && git branch -q -D hotfix/fix

echo; echo "flow — the vocabulary is the verbs of FR-2"
flowverbs() { M help | strip | awk '/^FLOW/ {f=1; next} f && /^$/ {exit} f {print $1}' | paste -sd' '; }
pathverbs() { M help | strip | sed -n 's/^Path: //p' | sed 's/ → /\n/g' | awk '{print $1}' | paste -sd' '; }
assert_eq "help's flow block lists the verbs that exist, in flow order, and nothing else" \
  "feature hotfix save promote gate ship" "$(flowverbs)"
assert_eq "…and the path it closes with names only verbs that exist" \
  "feature promote deploy ship" "$(pathverbs)"
assert_refuses "the verb that merged one rung into the next is gone" "No rule to make target" M finish
GONE="rele""ase"
assert_refuses "the verb that merged the review rung into production is gone" "No rule to make target" M "$GONE"
INTEG="BR_""INTEG"
assert_eq "the core names no integration rung" "0" "$(grep -c "$INTEG" "$PROJECT_CORE" || true)"

echo; echo "flow — refusals on a rung"
git checkout -q staging
assert_refuses "save refuses on a rung branch, naming make feature" "make feature name=" M save
git checkout -q main
assert_refuses "save refuses on the production branch too" "deploy-only" M save
assert_eq "…and did not move you off it" "main" "$(git branch --show-current)"

echo; echo "flow — the deploy gate"
git checkout -q -B staging origin/staging
echo dirty > dirty.txt
assert_refuses "deploy gate refuses a dirty tree" "Uncommitted" M _deploy-gate env=staging
rm dirty.txt
assert_refuses "deploy gate refuses the wrong branch" "deploys from" M _deploy-gate env=production
git checkout -q -b feature/unpushed origin/staging && echo u > u.txt && git add u.txt && git commit -q -m u
git checkout -q staging && git merge -q --no-ff feature/unpushed -m "local only"
assert_refuses "deploy gate refuses an unpushed HEAD" "push before deploying" M _deploy-gate env=staging
git push -q origin staging
assert_ok "deploy gate passes clean + right branch + pushed" M _deploy-gate env=staging
git branch -q -D feature/unpushed

echo; echo "flow — a confirming verb needs a terminal (C1)"
git checkout -q main
assert_refuses "echo yes | make ship is refused" "needs a terminal" bash -c 'echo yes | make --no-print-directory ship'
assert_refuses "make ship < file is refused" "needs a terminal" \
  bash -c "echo yes > $TMP/yes; make --no-print-directory ship < $TMP/yes; rc=\$?; rm -f $TMP/yes; exit \$rc"
assert_eq "…and main did not move" "$(git rev-parse origin/main)" "$(git rev-parse main)"
BEFORE=$(git ls-remote origin)
assert_refuses "a typed 'no' cancels and pushes nothing" "Cancelled" N "make --no-print-directory promote name=one"
assert_eq "…origin is byte-identical after the cancelled promote" "$BEFORE" "$(git ls-remote origin)"

echo; echo "flow — a stale staging is re-pointed, production is not (I3)"
# A rebuilt staging is stale on every machine that did not run the verb;
# refusing there stopped the whole flow. The same commits on the production
# branch are somebody's work, and are never discarded to unblock a verb.
git checkout -q -B staging origin/staging && echo stray > stray.txt
git add stray.txt && git commit -q -m "stray on staging"
STRAY=$(git rev-parse staging); git checkout -q main
assert_ok "make feature runs while a stale local staging carries a local-only commit" M feature name=three
assert_eq "…and the flow re-pointed staging at origin/staging" "$(git rev-parse origin/staging) 1" \
  "$(git rev-parse staging) $([ "$STRAY" != "$(git rev-parse staging)" ] && echo 1)"
git checkout -q main && git branch -q -D feature/three
git checkout -q -B staging origin/staging && echo stray > stray.txt
git add stray.txt && git commit -q -m "stray again" && git checkout -q main
git worktree add -q "$TMP/held" staging
assert_refuses "…but a stale staging another worktree holds is refused by name" "checked out elsewhere" M feature name=three
HELD=$(M feature name=three 2>&1 || true)
assert_eq "…and that refusal is all it prints — no raw git error, no branch made" "0 0" \
  "$(printf '%s' "$HELD" | grep -c 'fatal:') $(git branch --list feature/three | wc -l | tr -d ' ')"
git worktree remove --force "$TMP/held" && git branch -q -f staging origin/staging
git checkout -q -b feature/park origin/main && echo stray > stray.txt
git add stray.txt && git commit -q -m "stray on production"
PARK=$(git rev-parse HEAD); git branch -q -f main "$PARK"
assert_refuses "make feature refuses while main carries a local-only commit" "not on origin" M feature name=three
assert_eq "…and left the commit where it was — nothing is discarded to unblock a verb" "$PARK 0" \
  "$(git rev-parse main) $(git branch --list feature/three | wc -l | tr -d ' ')"
git branch -q -f main origin/main && git checkout -q main && git branch -q -D feature/park

echo; echo "flow — doctor/status say where you are"
git checkout -q staging
assert_eq "flow state names the role" "1" "$(M _flow-state | strip | grep -c 'rung:staging')"
assert_eq "flow state names the next verb" "1" "$(M _flow-state | grep -c 'make feature name=')"
# The next verb a feature or a hotfix is sent to must be one the flow still has.
nextverb() { M _flow-state | strip | sed -n 's/^  next: *//p' \
  | awk '{for (i=1;i<=NF;i++) if ($i == "make") {v=$(i+1); gsub(/[^a-z-]/,"",v); print v; exit}}'; }
isverb()  { case " feature hotfix save promote gate ship " in *" $1 "*) echo 1;; *) echo 0;; esac; }
git checkout -q -b feature/state origin/main
assert_eq "a feature is sent to promote, a verb that exists" "promote 1" "$(nextverb) $(isverb "$(nextverb)")"
git checkout -q -b hotfix/state origin/main
assert_eq "a hotfix is sent to gate, a verb that exists" "gate 1" "$(nextverb) $(isverb "$(nextverb)")"
assert_eq "…and to ship after it" "1" "$(M _flow-state | grep -c 'make ship')"
git checkout -q main && git branch -q -D feature/state hotfix/state

echo; echo "flow — without origin every verb refuses by name"
git remote remove origin
for v in "feature name=two" "hotfix name=two" "promote name=one"; do
  assert_refuses "no origin: make $v" "no 'origin' remote" M $v
done
assert_refuses "no origin, no terminal: make ship refuses for the terminal first" "needs a terminal" \
  bash -c "make --no-print-directory ship < /dev/null"
assert_refuses "no origin, with a terminal: make ship stops at the deploy gate" "no 'origin' remote" \
  Y "make --no-print-directory ship"
assert_eq "…and it reached no backup and no transport" "" "$(cat "$LEAVES")"
assert_refuses "no origin: the deploy gate" "no 'origin' remote" M _deploy-gate env=production
assert_eq "flow state shows origin MISSING" "1" "$(M _flow-state | grep -c 'MISSING')"

echo
printf 'flow-test: %d ok, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
