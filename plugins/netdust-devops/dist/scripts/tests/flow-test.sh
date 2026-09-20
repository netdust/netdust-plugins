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
_deploy-transport _deploy-ledger _deploy-opcache _backup-data _backup-payload _deploy-stamp:
	@echo '\$@ \$(env)' >> $LEAVES; [ "\$\$FAILLEAF" != "\$@" ] || exit 1
MK
cat > "$W/site.yml" <<'YAML'
site: {name: flowtest, domain: flowtest.test, risk: low}
structure: {type: bedrock, stack: generic, webroot: web}
deploy: {method: rsync, ssh_host: nowhere, wp_path: web/wp, content_dir: web/app, state_dir: /tmp/flowtest-state, payload: [app/mu-plugins]}
environments:
  staging:    {branch: staging, url: https://stg.flowtest.test, path: /srv/stg, role: review, confirm: false}
  production: {branch: main,    url: https://flowtest.test,     path: /srv/prod, role: live, confirm: true}
YAML
# ship runs the project's gate itself; the script lives outside the repo, where it cannot dirty the tree.
cat >> "$W/site.yml" <<YAML
commands: {gate: sh $TMP/gate.sh}
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

echo; echo "flow — ship"
# FR-6, FR-9: production receives the exact staging commit that was deployed and gated.
# Every refusal pins its reason AND what it did not do — origin byte-identical,
# production unmoved, 0 leaves, and the prompt never reached.
SHIP0=$(git ls-remote origin); SMAIN=$(exact refs/heads/main); SSTG=$(exact refs/heads/staging)
SHIPPED="_backup-data production|_backup-payload production|_deploy-transport production|_deploy-ledger production|_deploy-opcache production"
leaves()     { sed 's/ *$//' "$LEAVES" | paste -sd'|'; }; prodsha() { exact refs/heads/main; }
gatescript() { printf '#!/bin/sh\necho "suite ran"\nexit %s\n' "$1" > "$TMP/gate.sh"; }
deploytag()  { git tag -f deployed/staging "$1" >/dev/null && git push -qf origin deployed/staging; }
E()          { script -qec "$*" /dev/null < /dev/null; }   # a real pty, with nothing typed
# shiprefused <label> <reason>: ship stops there, before the prompt, having moved nothing.
shiprefused() { local l="$1" why="$2" here before was; here=$(git branch --show-current)
  before=$(git ls-remote origin); was=$(prodsha); : > "$LEAVES"; YF "make --no-print-directory ship"
  assert_eq "$l" "1 1 0" "$(nz "$YRC") $(has "$YOUT" "$why") $(has "$YOUT" "Type 'yes'")"
  assert_eq "…and nothing moved: origin byte-identical, production unmoved, 0 leaves" "$before|$was|" "$(git ls-remote origin)|$(prodsha)|$(leaves)"
  git checkout -q "$here"; }
for f in sa sb sc; do git checkout -q -b "feature/$f" origin/main; echo "$f" > "$f.txt"; git add "$f.txt"; git commit -q -m "$f"; git push -q origin "feature/$f"; done
git checkout -q main && git fetch -q origin; step promote name=sa; step promote name=sb; step promote name=sc
git fetch -q origin; deploytag origin/staging; step unpromote name=sc
git fetch -q origin; ABTREE=$(handtree "$SMAIN" origin/feature/sa origin/feature/sb); STGC=$(exact refs/heads/staging)
git checkout -q -B staging origin/staging; gatescript 0; BEFORE=$(git ls-remote origin); : > "$LEAVES"
assert_eq "setup: staging is main+sa+sb, and deployed/staging still names the rebuild before it" "$ABTREE sa sb 1" "$(treeof origin/staging) $(onstg) $([ "$(exact refs/tags/deployed/staging)" != "$STGC" ] && echo 1)"
assert_refuses "(h) echo yes | make ship: refused for the terminal, before any git or server action" "needs a terminal" bash -c 'echo yes | make --no-print-directory ship'
assert_eq "…(h) origin is byte-identical and 0 leaves ran" "$BEFORE|" "$(git ls-remote origin)|$(leaves)"
for d in 1 --dry-run; do
  BEFORE=$(git ls-remote origin); : > "$LEAVES"; YF "make --no-print-directory ship dryrun=$d"; git checkout -q staging
  assert_eq "(i) make ship dryrun=$d: refused by name, before the prompt, 0 backups, origin byte-identical" "1 1 0 $BEFORE|" "$(nz "$YRC") $(has "$YOUT" 'dryrun') $(has "$YOUT" "Type 'yes'") $(git ls-remote origin)|$(leaves)"
done
: > shipdirt.txt
shiprefused "(d) an untracked file: refused naming the uncommitted change" "uncommitted changes"
assert_eq "…(d) naming the file, and the gate never ran" "1 0" "$(has "$YOUT" 'shipdirt.txt') $(has "$YOUT" 'suite ran')"
rm -f shipdirt.txt; printf '\n# dirt\n' >> site.yml
shiprefused "(d) a modified tracked file: the same refusal, still before the gate" "uncommitted changes"
git checkout -q -- site.yml; git worktree add -q "$TMP/heldprod" main
shiprefused "(e) the production branch held by another worktree: refused in the worktree guard's words" "checked out in another worktree"
git worktree remove --force "$TMP/heldprod"; git checkout -q -b feature/sj origin/main
shiprefused "(j) ship from a feature branch: refused naming the staging branch" "staging"
assert_eq "…(j) and the hotfix route too" "1" "$(has "$YOUT" 'hotfix')"
git checkout -q staging && git branch -q -D feature/sj
shiprefused "(b) staging rebuilt since its last deploy: refused naming the tag" "deployed/staging"
deploytag origin/staging; gatescript 1
shiprefused "(c) a red gate: refused, 0 backups" "gate is red"
assert_eq "…(c) and the gate really ran" "1" "$(has "$YOUT" 'suite ran')"
# commands.gate is the project's own shell: a suite that commits (auto-fix lint, codegen) must not slip that commit into production.
printf '#!/bin/sh\necho "suite ran"\n: > gated.txt; git add gated.txt; git commit -qm "the gate committed"\n' > "$TMP/gate.sh"
shiprefused "(n) a gate that commits: refused, and the gate's commit never ships" "changed while the gate ran"
git reset -q --hard "$STGC"; gatescript 0
assert_eq "…(n) and the gate's commit is off staging again" "$STGC " "$(git rev-parse HEAD) $(git status --porcelain)"
gatescript 0; BEFORE=$(git ls-remote origin); : > "$LEAVES"; NOUT=$(N "make --no-print-directory ship"); NRC=$?; git checkout -q staging
assert_eq "(f) a typed no: Cancelled, nothing moved, 0 leaves" "1 1 $BEFORE|" "$(nz "$NRC") $(has "$NOUT" 'Cancelled') $(git ls-remote origin)|$(leaves)"
: > "$LEAVES"; YF "make --no-print-directory ship"; git fetch -q --prune origin
assert_eq "(a) Y make ship from the staging checkout: exit 0, production is the deployed staging commit (SC-2)" "0 $STGC" "$YRC $(prodsha)"
assert_eq "…(a) its tree is a hand-merged main+sa+sb, with 0 commits of sc in production" "$ABTREE 0" "$(treeof origin/main) $(git merge-base --is-ancestor origin/feature/sc origin/main && echo 1 || echo 0)"
assert_eq "…(a) both backups, then one production deploy, ledger and opcache — nothing on staging" "$SHIPPED" "$(leaves)"
assert_eq "…(a) and staging is the new production tip: sa and sb are off it, shipped (FR-8)" "$STGC " "$(exact refs/heads/staging) $(onstg)"
step promote name=sc; git fetch -q origin
assert_eq "…(a) promoting sc after the ship puts it on the NEW production tip (AF-1)" "$(handtree origin/main origin/feature/sc) sc" "$(treeof origin/staging) $(onstg)"
git checkout -q -f -B main "$SMAIN"; git branch -q -f staging "$SSTG"; git push -qf origin "$SMAIN:refs/heads/main" "$SSTG:refs/heads/staging"
for f in sa sb sc; do git push -q origin ":refs/heads/feature/$f"; git branch -q -D "feature/$f"; done; for t in staging production; do git push -q origin ":refs/tags/deployed/$t" 2>/dev/null; git tag -d "deployed/$t" >/dev/null 2>&1; done; git fetch -q --prune origin; : > "$LEAVES"
assert_eq "…and the ship section leaves origin, the checkout, the tree and the leaf log as it found them" "$SHIP0 main " "$(git ls-remote origin) $(git branch --show-current) $(git status --porcelain)"

echo; echo "flow — hotfix"
# FR-7: a hotfix ships from its own branch with no staging round, and FR-8 still rebuilds staging over it.
HORIG=$(git ls-remote origin); HMAIN=$(exact refs/heads/main); HSTG=$(exact refs/heads/staging)
git checkout -q -b feature/sh origin/main && echo sh > sh.txt && git add sh.txt && git commit -q -m sh && git push -q origin feature/sh
git checkout -q main; step promote name=sh; git fetch -q origin; PSH=$(git rev-parse origin/feature/sh)
M hotfix name=h >/dev/null; echo h > h.txt && git add h.txt && git commit -q -m "the fix"; HFIX=$(git rev-parse HEAD); gatescript 1
shiprefused "(k) a hotfix with a red gate: refused, 0 backups" "gate is red"
gatescript 0
# Threat 8's neighbour: another session ships between this one's fetch and its push.
git checkout -q --detach origin/main && echo raced > raced.txt && git add raced.txt && git commit -q -m "another session ships"; RACED=$(git rev-parse HEAD); git checkout -q hotfix/h
shim "$TMP/shipr" <<SH
#!/bin/sh
case "\$1" in push) [ -e "$TMP/shipr/done" ] || { : > "$TMP/shipr/done"; "$(command -v git)" push -q "$TMP/origin.git" "$RACED:refs/heads/main"; };; esac
exec "$(command -v git)" "\$@"
SH
: > "$LEAVES"; YF "$TMP/shipr/mk ship"; git fetch -q --prune origin
assert_eq "(m) another session's ship lands between the fetch and the push: refused, their commit stands, 0 transport" "1 $RACED _backup-data production|_backup-payload production" "$(nz "$YRC") $(prodsha) $(leaves)"
rm -rf "$TMP/shipr"; git push -qf origin "$HMAIN:refs/heads/main"; git branch -q -f main "$HMAIN"; git fetch -q --prune origin
git checkout -q --detach origin/main && echo moved > moved.txt && git add moved.txt && git commit -q -m "production moves"
git push -q origin HEAD:refs/heads/main; git checkout -q hotfix/h; git fetch -q origin
shiprefused "(k) production advanced since the hotfix branched: refused naming the update" "update the hotfix from production"
git push -qf origin "$HMAIN:refs/heads/main"; git branch -q -f main "$HMAIN"; git fetch -q --prune origin
: > "$LEAVES"; YF "make --no-print-directory ship"; git fetch -q --prune origin
assert_eq "(k) Y make ship from hotfix/h: exit 0, production is main+H (AF-5)" "0 $HFIX" "$YRC $(prodsha)"
assert_eq "…(k) both backups, then one production deploy, ledger and opcache — 0 staging leaves" "$SHIPPED" "$(leaves)"
assert_eq "…(k) and staging is rebuilt on the new production tip, carrying H and sh (FR-8)" "$(handtree origin/main "$PSH") sh 1" "$(treeof origin/staging) $(onstg) $(git merge-base --is-ancestor "$HFIX" origin/staging && echo 1 || echo 0)"
# R49-1: environments.production.confirm governs make deploy and nothing else.
git checkout -q -b hotfix/g origin/main
sed -i "/^  production:/s/confirm: [a-z]*/confirm: false/" site.yml && git commit -q -am "production confirm: false"
askedanyway() { local l="$1" before was; before=$(git ls-remote origin); was=$(prodsha); : > "$LEAVES"
  EOUT=$(E "make --no-print-directory ship"); ERC=$?; git checkout -q hotfix/g
  assert_eq "$l" "1 1 $before|$was|" "$(nz "$ERC") $(has "$EOUT" "Type 'yes'") $(git ls-remote origin)|$(prodsha)|$(leaves)"; }
askedanyway "(g) production confirm: false, nothing typed: ship asked anyway, refused, moved nothing (FR-9)"
sed -i "/^  production:/s/, *confirm: [a-z]*}/}/" site.yml && git commit -q -am "production without a confirm key"
assert_eq "setup: production declares no confirm key at all" "" "$(scripts/site environments.production.confirm 2>/dev/null)"
askedanyway "(g) no confirm key, nothing typed: the same — the key never governed ship"
git checkout -q -B staging origin/staging; : > "$LEAVES"; DOUT=$(M deploy-test env=staging < /dev/null); DRC=$?
assert_eq "…(g) the twin: staging declares confirm: false, so its deploy still runs unprompted" "0 0 _deploy-transport staging" "$DRC $(has "$DOUT" "Type 'yes'") $(leaves)"
git checkout -q hotfix/g; HG=$(git rev-parse HEAD); : > "$LEAVES"; YF "FAILLEAF=_deploy-transport make --no-print-directory ship"; git fetch -q --prune origin
assert_eq "(l) the transport fails after the push: non-zero, and production on origin HAS advanced (threat 8)" "1 $HG" "$(nz "$YRC") $(prodsha)"
assert_eq "…(l) and it says the branch is ahead of the site, naming the recovery" "1 1" "$(has "$YOUT" 'ahead of') $(has "$YOUT" 'make deploy env=production')"
# T02-M6: with no staging environment BR_REVIEW falls back to the production branch — the rebuild must not run.
git checkout -q -f main; git checkout -q -b hotfix/solo origin/main
sed -i '/^  staging:/d' site.yml && echo solo > solo.txt && git add -A && git commit -q -m "no staging environment"
SOLO=$(git rev-parse HEAD); WASSTG=$(exact refs/heads/staging); : > "$LEAVES"; YF "make --no-print-directory ship"; git fetch -q --prune origin
assert_eq "(M6) a project with no staging environment: the hotfix ships, production is the hotfix commit" "0 $SOLO" "$YRC $(prodsha)"
assert_eq "…(M6) and no rebuild ran: staging untouched, no lost lease, no dropped commit, the five production leaves" "$WASSTG 0 0 $SHIPPED" "$(exact refs/heads/staging) $(has "$YOUT" 'run it again') $(has "$YOUT" 'dropped') $(leaves)"
git checkout -q -f -B main "$HMAIN"; git branch -q -f staging "$HSTG"; git push -qf origin "$HMAIN:refs/heads/main" "$HSTG:refs/heads/staging"
git push -q origin ":refs/heads/feature/sh"; git branch -q -D feature/sh; git branch -q -D hotfix/h hotfix/g hotfix/solo >/dev/null 2>&1
for t in staging production; do git push -q origin ":refs/tags/deployed/$t" 2>/dev/null; git tag -d "deployed/$t" >/dev/null 2>&1; done; git fetch -q --prune origin; : > "$LEAVES"
assert_eq "…and the hotfix section leaves origin, the checkout, the tree and the leaf log as it found them" "$HORIG main " "$(git ls-remote origin) $(git branch --show-current) $(git status --porcelain)"

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
