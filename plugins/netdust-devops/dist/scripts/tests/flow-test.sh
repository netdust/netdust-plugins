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
  "feature hotfix save promote unpromote gate ship" "$(flowverbs)"
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
isverb()  { case " feature hotfix save promote unpromote gate ship " in *" $1 "*) echo 1;; *) echo 0;; esac; }
git checkout -q -b feature/state origin/main
assert_eq "a feature is sent to promote, a verb that exists" "promote 1" "$(nextverb) $(isverb "$(nextverb)")"
git checkout -q -b hotfix/state origin/main
assert_eq "a hotfix is sent to gate, a verb that exists" "gate 1" "$(nextverb) $(isverb "$(nextverb)")"
assert_eq "…and to ship after it" "1" "$(M _flow-state | grep -c 'make ship')"
git checkout -q main && git branch -q -D feature/state hotfix/state

echo; echo "flow — promote"
# Staging stores nothing: what is on it is read back from its own `promote:`
# merges. Every claim here compares a TREE against a hand-merged reference,
# never the verb's own success line.
YF()       { YOUT=$(Y "$@"); YRC=$?; }
step()     { YF "make --no-print-directory $*"; if [ "$YRC" -eq 0 ]; then ok "setup: make $*"; else fail "setup: make $*" "$YOUT"; fi; }
exact()    { git ls-remote origin "$1" | awk -v r="$1" '$2 == r {print $1}'; }
treeof()   { git rev-parse "$1^{tree}"; }
handtree() { local b=$1; shift; git checkout -q -B hand "$b"; for m; do git merge -q --no-ff -m h "$m" >/dev/null; done
             treeof hand; git checkout -q main; git branch -q -D hand; }
onstg()    { git log --merges --first-parent --reverse --format='%s' origin/main..origin/staging | sed 's/^promote: //' | paste -sd' '; }
pinof()    { git log --merges --first-parent --format='%s %P' origin/main..origin/staging | awk -v n="$1" '$2 == n {print $4}'; }
nz()       { [ "$1" -ne 0 ] && echo 1 || echo 0; }
quiet()    { printf '%s\n' "$1" | strip | grep -ci 'dropped'; }
hasre()    { printf '%s\n' "$1" | grep -qE -- "$2" && echo 1 || echo 0; }
shim()     { mkdir -p "$1"; cat > "$1/git"; printf '#!/bin/sh\nPATH="%s:$PATH" exec make --no-print-directory "$@"\n' "$1" > "$1/mk"; chmod +x "$1/git" "$1/mk"; }
FEATS="a b c d r f t3 x"
ORIGIN0=$(git ls-remote origin); STG0=$(exact refs/heads/staging)
git push -qf origin "$(git rev-parse origin/main):refs/heads/staging"
for f in a b c d r f; do git checkout -q -b "feature/$f" origin/main; echo "$f" > "$f.txt"; git add "$f.txt"; git commit -q -m "$f"; done
git checkout -q -b feature/t3 origin/main
for n in 1 2 3; do echo "$n" > "t$n.txt" && git add "t$n.txt" && git commit -q -m "t$n"; done
git checkout -q -b feature/x origin/main && echo conflict > a.txt && git add a.txt && git commit -q -m x
git checkout -q main; for f in $FEATS; do git push -q origin "feature/$f"; done; git fetch -q --prune origin
assert_eq "setup: staging starts at production, and all 8 features are on origin" "$(git rev-parse origin/main) 8" \
  "$(exact refs/heads/staging) $(for f in $FEATS; do exact "refs/heads/feature/$f"; done | grep -c .)"
step promote name=a; step promote name=b; step promote name=c
git fetch -q origin
assert_eq "three promotes: staging is the tree of a hand-merged main+a+b+c (SC-2)" \
  "$(handtree origin/main origin/feature/a origin/feature/b origin/feature/c) a b c" \
  "$(treeof origin/staging) $(onstg)"
step unpromote name=c
git fetch -q origin
assert_eq "unpromote c: staging is main+a+b, and carries no commit of c" \
  "$(handtree origin/main origin/feature/a origin/feature/b) a b 0" \
  "$(treeof origin/staging) $(onstg) $(git merge-base --is-ancestor origin/feature/c origin/staging && echo 1 || echo 0)"
PA=$(git rev-parse origin/feature/a)
git checkout -q feature/a && echo more >> a.txt && git commit -qam "a again" && git push -q origin feature/a
git checkout -q main && git fetch -q origin; PA2=$(git rev-parse origin/feature/a)
assert_eq "setup: feature/a moved on origin" "1" "$([ "$PA" != "$PA2" ] && echo 1)"
step promote name=c
git fetch -q origin
assert_eq "a promoted feature stays at the commit it was promoted at (AF-2)" \
  "$PA $(handtree origin/main "$PA" origin/feature/b origin/feature/c)" "$(pinof a) $(treeof origin/staging)"
step promote name=a
git fetch -q origin
assert_eq "…and promoting it again moves it to the new tip, quietly (AF-2, SC-8)" \
  "$PA2 $(handtree origin/main "$PA2" origin/feature/b origin/feature/c) 0" \
  "$(pinof a) $(treeof origin/staging) $(quiet "$YOUT")"

# FR-16: a rebuild says what it drops, and says nothing when it drops nothing.
git checkout -q -b legacy origin/staging && echo legacy > legacy.txt && git add legacy.txt
git commit -q -m "a commit that only ever lived on staging"
OLDSTG=$(git rev-parse HEAD); OLDSHORT=$(printf %.7s "$OLDSTG")
git push -qf origin legacy:refs/heads/staging && git checkout -q main && git branch -q -D legacy && git fetch -q --prune origin
assert_eq "setup: origin/staging carries one commit no promote: merge explains" "$OLDSTG 0" \
  "$(exact refs/heads/staging) $(git merge-base --is-ancestor "$OLDSTG" origin/main && echo 1 || echo 0)"
step promote name=t3
DROPLINE=$(printf '%s\n' "$YOUT" | strip | grep -i dropped)
assert_eq "…the rebuild reports ONE dropped commit and the old staging sha — a report, not a refusal (SC-8)" "1 1 1" \
  "$(has "$DROPLINE" 'dropped') $(hasre "$DROPLINE" '(^|[^[:alnum:]])1([^[:alnum:]]|$)') $(has "$DROPLINE" "$OLDSHORT")"
assert_eq "…and that sha still names the commit that was dropped" "0 legacy.txt" \
  "$(git cat-file -e "$OLDSTG^{commit}" 2>/dev/null; echo $?) $(git diff-tree --no-commit-id --name-only -r "$OLDSTG" | paste -sd' ')"
step promote name=f
assert_eq "an everyday promote drops nothing, and stays quiet (SC-8)" "0" "$(quiet "$YOUT")"
step unpromote name=f
assert_eq "…and so does an unpromote" "0" "$(quiet "$YOUT")"
step unpromote name=t3
assert_eq "…and an unpromote of a 3-commit feature" "0" "$(quiet "$YOUT")"
git checkout -q -b legacy2 origin/staging && echo l2 > l2.txt && git add l2.txt && git commit -q -m l2
git push -qf origin legacy2:refs/heads/staging && git checkout -q main && git branch -q -D legacy2 && git fetch -q --prune origin
step unpromote name=c
DROPLINE=$(printf '%s\n' "$YOUT" | strip | grep -i dropped)
assert_eq "an unpromote beside an unexplained commit reports that one, never the feature it removed (SC-8)" "1 1" \
  "$(has "$DROPLINE" 'dropped') $(hasre "$DROPLINE" '(^|[^[:alnum:]])1([^[:alnum:]]|$)')"

echo; echo "flow — rebuild refuses cleanly"
# A refusal counts only if origin did not move: every case pins its reason AND
# `git ls-remote origin` byte-identical around it.
git fetch -q --prune origin; BEFORE=$(git ls-remote origin)
YF "make --no-print-directory promote name=x"
assert_eq "a feature conflicting with a: refused naming it, nothing pushed, no worktree left (SC-3)" "1 1 1 $BEFORE" \
  "$(nz "$YRC") $(has "$YOUT" 'conflict: x') $(git worktree list | wc -l | tr -d ' ') $(git ls-remote origin)"
assert_refuses "promote without a terminal is refused before anything else (C1)" "needs a terminal" \
  bash -c 'make --no-print-directory promote name=a < /dev/null'
assert_refuses "…and unpromote too" "needs a terminal" \
  bash -c 'make --no-print-directory unpromote name=a < /dev/null'
assert_refuses "promote of a feature that is not on origin, by name" "No such branch on origin: feature/nope" \
  Y "make --no-print-directory promote name=nope"
assert_refuses "…and a name that reads as a revision range, by name too" "No such branch on origin: feature/a..b" \
  Y "make --no-print-directory promote name=a..b"
assert_refuses "…and a name outside the charset, before anything is read" "Invalid name" \
  Y "make --no-print-directory promote name=a\\;b"
assert_refuses "unpromote of a feature that is not on staging, by name" "is not on staging" \
  Y "make --no-print-directory unpromote name=f"
cp site.yml "$TMP/site.keep" && sed -i '/^  staging:/d' site.yml
assert_refuses "a project with no staging environment: promote refuses by name" "No staging environment" \
  Y "make --no-print-directory promote name=a"
assert_refuses "…and so does unpromote" "No staging environment" \
  Y "make --no-print-directory unpromote name=a"
cp "$TMP/site.keep" site.yml
assert_eq "…and origin is byte-identical after all the refusals, with site.yml back" "$BEFORE " \
  "$(git ls-remote origin) $(git status --porcelain)"
# Another session rebuilt staging between this one's fetch and its push. The
# PATH shim makes that race deterministic — it lands the other rebuild on origin
# the first time this one pushes.
git checkout -q --detach origin/staging && git merge -q --no-ff -m "promote: r" origin/feature/r
RACED=$(git rev-parse HEAD); git checkout -q main
shim "$TMP/race" <<SH
#!/bin/sh
REAL="$(command -v git)"
if [ "\$1" = push ] && [ ! -e "$TMP/race/done" ]; then
  : > "$TMP/race/done"; "\$REAL" push -qf "$TMP/origin.git" "$RACED:refs/heads/staging"
fi
exec "\$REAL" "\$@"
SH
YF "$TMP/race/mk promote name=d"
git fetch -q origin
assert_eq "a lease lost to another session: refused, told to run it again, staging is what that session left (AF-3)" "1 1 $RACED" \
  "$(nz "$YRC") $(has "$YOUT" 'run it again') $(exact refs/heads/staging)"
step promote name=d
git fetch -q origin
assert_eq "…and the re-run carries both sessions' features" "a b d r" "$(onstg)"
# A Ctrl-C mid-rebuild: the trap takes the throwaway worktree with it.
shim "$TMP/intr" <<SH
#!/bin/sh
case " \$* " in *" merge "*) kill -INT "\$PPID"; exit 130;; esac
exec "$(command -v git)" "\$@"
SH
BEFORE=$(git ls-remote origin)
YF "$TMP/intr/mk promote name=f"
assert_eq "a rebuild interrupted mid-merge: non-zero, no worktree left behind, origin byte-identical (FR-5)" "1 1 $BEFORE" \
  "$(nz "$YRC") $(git worktree list | wc -l | tr -d ' ') $(git ls-remote origin)"
# An empty keep list — the last feature unpromoted, or everything already
# shipped — merges nothing, so a rebuild worktree that was never created goes
# unnoticed and an empty NEW turns the push into a DELETE refspec.
CASE0=$(git ls-remote origin); CSTG=$(exact refs/heads/staging)
git push -qf origin "$(git rev-parse origin/main):refs/heads/staging"; git fetch -q --prune origin
step promote name=f
git fetch -q origin
assert_eq "setup: f is the only feature on staging, and staging is on origin" "f 1" \
  "$(onstg) $(git ls-remote origin refs/heads/staging | grep -c .)"
shim "$TMP/nowt" <<SH
#!/bin/sh
case " \$* " in *" worktree add "*) echo 'fatal: could not create work tree dir' >&2; exit 128;; esac
exec "$(command -v git)" "\$@"
SH
BEFORE=$(git ls-remote origin)
YF "$TMP/nowt/mk unpromote name=f"
git fetch -q --prune origin
assert_eq "the rebuild worktree cannot be made and nothing is left to merge: refused, no success line, staging still on origin (FR-5)" "1 1 0 1 $BEFORE" \
  "$(nz "$YRC") $(has "$YOUT" 'rebuild worktree') $(has "$YOUT" 'is off staging') $(git ls-remote origin refs/heads/staging | grep -c .) $(git ls-remote origin)"
YF "$TMP/nowt/mk promote name=d"
assert_eq "…and with features left to merge it still names the worktree, never a conflict (FR-5)" "1 1 0 $BEFORE" \
  "$(nz "$YRC") $(has "$YOUT" 'rebuild worktree') $(has "$YOUT" 'conflict:') $(git ls-remote origin)"
shim "$TMP/nohead" <<SH
#!/bin/sh
case " \$* " in *" -C "*" rev-parse HEAD "*) exit 128;; esac
exec "$(command -v git)" "\$@"
SH
YF "$TMP/nohead/mk promote name=d"
assert_eq "…and a rebuild whose worktree HEAD cannot be read pushes no empty ref either (FR-5)" "1 1 0 $BEFORE" \
  "$(nz "$YRC") $(has "$YOUT" 'no commit') $(has "$YOUT" 'is on staging') $(git ls-remote origin)"
rm -rf "$TMP/nowt" "$TMP/nohead"
git push -qf origin "$CSTG:refs/heads/staging"; git fetch -q --prune origin
assert_eq "…and the case leaves no shim behind and origin as it found it" "0 0 $CASE0" \
  "$([ -e "$TMP/nowt/mk" ] && echo 1 || echo 0) $([ -e "$TMP/nohead/mk" ] && echo 1 || echo 0) $(git ls-remote origin)"
for f in $FEATS; do git push -q origin ":refs/heads/feature/$f"; git branch -q -D "feature/$f"; done
git push -qf origin "$STG0:refs/heads/staging"; git branch -q -f staging "$STG0"
git fetch -q --prune origin
assert_eq "…and the two rebuild sections leave origin byte-identical" "$ORIGIN0" "$(git ls-remote origin)"

echo; echo "flow — without origin every verb refuses by name"
git remote remove origin
for v in "feature name=two" "hotfix name=two"; do
  assert_refuses "no origin: make $v" "no 'origin' remote" M $v
done
for v in "promote name=one" "unpromote name=one"; do
  assert_refuses "no origin, no terminal: make $v refuses for the terminal first" "needs a terminal" \
    bash -c "make --no-print-directory $v < /dev/null"
  assert_refuses "no origin, with a terminal: make $v stops on the missing remote" "no 'origin' remote" \
    Y "make --no-print-directory $v"
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
