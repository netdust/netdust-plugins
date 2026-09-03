#!/usr/bin/env bash
# Invariants for the deploy tooling. Portable between projects — asserts on
# rules, never on this project's hostnames or branch names.
# Never contacts a server.
set -uo pipefail
cd "$(dirname "$0")/../.."

PASS=0; FAIL=0

assert_eq() { # label expected actual
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); printf '  ok   %s\n' "$1"
  else FAIL=$((FAIL+1)); printf '  FAIL %s\n       expected: [%s]\n       actual:   [%s]\n' "$1" "$2" "$3"; fi
}

assert_nonempty() { # label value
  if [ -n "$2" ]; then PASS=$((PASS+1)); printf '  ok   %s\n' "$1"
  else FAIL=$((FAIL+1)); printf '  FAIL %s (empty)\n' "$1"; fi
}

assert_exit() { # label expected_code command...
  local label="$1" want="$2"; shift 2
  "$@" >/dev/null 2>&1
  local got=$?
  if [ "$got" = "$want" ]; then PASS=$((PASS+1)); printf '  ok   %s\n' "$label"
  else FAIL=$((FAIL+1)); printf '  FAIL %s (exit %s, expected %s)\n' "$label" "$got" "$want"; fi
}

assert_refuses() { # label pattern command...
  local label="$1" pattern="$2"; shift 2
  local out
  out=$("$@" 2>&1)
  if [ $? -eq 0 ]; then
    FAIL=$((FAIL+1)); printf '  FAIL %s (succeeded, expected refusal)\n' "$label"
  elif printf '%s' "$out" | grep -q "$pattern"; then
    PASS=$((PASS+1)); printf '  ok   %s\n' "$label"
  else
    FAIL=$((FAIL+1)); printf '  FAIL %s (refused, but not with "%s")\n       got: %s\n' "$label" "$pattern" "$out"
  fi
}

WEBROOT=$(scripts/site structure.webroot)

echo "scripts/site — reader"
assert_nonempty "reads a top-level scalar"  "$(scripts/site site.name)"
assert_nonempty "reads a nested scalar"     "$(scripts/site structure.webroot)"
assert_nonempty "lists a mapping's keys"    "$(scripts/site environments)"
assert_exit     "missing key exits 1" 1 scripts/site environments.nope.path
assert_exit     "bad usage exits 2"   2 scripts/site

echo
echo "site.yml — every environment is fully described"
for e in $(scripts/site environments); do
  for k in url path branch role confirm; do
    assert_nonempty "$e.$k is set" "$(scripts/site environments.$e.$k)"
  done
done
HAS_PROD=$(scripts/site environments.production.path >/dev/null 2>&1 && echo yes || echo no)
if [ "$HAS_PROD" = "yes" ]; then
  assert_eq "production requires a typed confirmation" \
    "true" "$(scripts/site environments.production.confirm)"
else
  PASS=$((PASS+1)); printf '  ok   no production environment yet (staging-only project)\n'
fi
# Only production may demand a typed confirmation — a prompt on a routine
# environment turns every deploy into a chore. The check needs a declared
# production environment to be meaningful, so it is DEFERRED (not waived) while
# one is missing: an undeclared production is itself the thing to fix, and
# declaring it re-engages this assertion.
for e in $(scripts/site environments); do
  [ "$e" = "production" ] && continue
  if [ "$HAS_PROD" != "yes" ]; then
    PASS=$((PASS+1)); printf '  ok   %s prompt check deferred — declare environments.production\n' "$e"
    continue
  fi
  assert_eq "$e does not prompt" "false" "$(scripts/site environments.$e.confirm)"
done

echo
echo "site.yml — the payload is a closed, tracked list"
METHOD=$(scripts/site deploy.method)
if [ "$METHOD" != "rsync" ]; then
  PASS=$((PASS+1)); printf '  ok   payload not required for the %s transport\n' "$METHOD"
else
assert_nonempty "payload is not empty" "$(scripts/site deploy.payload)"
assert_eq "payload never contains uploads" \
  "0" "$(scripts/site deploy.payload | grep -c uploads)"
assert_eq "payload never contains wp core" \
  "0" "$(scripts/site deploy.payload | grep -cx 'wp')"
for p in $(scripts/site deploy.payload); do
  assert_eq "payload path exists locally: $p" \
    "1" "$([ -d "$WEBROOT/$p" ] && echo 1 || echo 0)"
  # An untracked payload path deploys as an empty directory, and a
  # worktree-based rollback would then rsync --delete it off the server.
  assert_eq "payload path is tracked in git: $p" \
    "1" "$([ "$(git ls-files "$WEBROOT/$p" | head -1 | wc -l)" -gt 0 ] && echo 1 || echo 0)"
done
fi

if [ "$METHOD" = "rsync" ]; then
echo
echo "deploy.exclude — must not hide payload content"
assert_eq "does not exclude *.map (font-encoding tables are not source maps)" \
  "0" "$(scripts/site deploy.exclude | grep -cx '\*\.map')"
assert_eq "excludes repo metadata" \
  "1" "$(scripts/site deploy.exclude | grep -cx '\.git\*')"
fi

echo
echo "state dir — must sit outside every web root"
STATE=$(scripts/site deploy.state_dir)
assert_nonempty "state_dir is set" "$STATE"
for e in $(scripts/site environments); do
  P=$(scripts/site environments.$e.path)
  case "$STATE" in
    "$P"/*) FAIL=$((FAIL+1)); printf '  FAIL state_dir is inside %s (web-served)\n' "$e";;
    *)      PASS=$((PASS+1)); printf '  ok   state_dir is outside %s\n' "$e";;
  esac
done

echo
echo "deploy gate — refusals"
assert_refuses "refuses a missing env argument" "Usage: make deploy env=" make -s _deploy-gate
assert_refuses "refuses an unknown environment" "Unknown environment"    make -s _deploy-gate env=nope
CURRENT=$(git branch --show-current)
PROD_BRANCH=$(scripts/site environments.production.branch 2>/dev/null)
if [ "$HAS_PROD" = "yes" ] && [ "$CURRENT" != "$PROD_BRANCH" ]; then
  assert_refuses "refuses production from the wrong branch" "deploys from" \
    make -s _deploy-gate env=production
fi

echo
echo "data direction — backward only"
assert_refuses "refuses refresh into production"  "never into production" make -s _refuse-production env=production
assert_refuses "refuses block-mail on production" "never into production" make -s block-mail env=production
assert_refuses "refuses an unknown refresh target" "Unknown environment"  make -s _refuse-production env=nope
assert_refuses "refuses an unknown pull source"    "Unknown environment"  make -s pull env=nope
assert_eq "no target pushes local data forward" \
  "0" "$(grep -cE '^sync-to-staging:' Makefile)"
assert_eq "the mail block mu-plugin exists in the repo" \
  "1" "$([ -f scripts/remote/00-block-outgoing-mail.php ] && echo 1 || echo 0)"
assert_eq "the mail block is parameterised, not hardcoded" \
  "1" "$(grep -q '__PRODUCTION_HOST__' scripts/remote/00-block-outgoing-mail.php && echo 1 || echo 0)"

echo
echo "promote — one feature, not the whole integration branch"
assert_refuses "refuses promote without a name"  "Usage: make promote name=" make -s promote
# The flow floor runs first: without an origin, promote refuses for that reason.
if git remote get-url origin >/dev/null 2>&1; then
  assert_refuses "refuses an unknown feature branch" "No such branch"        make -s promote name=definitely-not-a-real-feature
else
  assert_refuses "refuses an unknown feature branch" "no 'origin' remote"   make -s promote name=definitely-not-a-real-feature
fi

echo
echo "transport — one workflow, pluggable file movement"
M=$(scripts/site deploy.method)
case "$M" in
  rsync|git-push) PASS=$((PASS+1)); printf '  ok   deploy.method is a known transport (%s)\n' "$M";;
  *)              FAIL=$((FAIL+1)); printf '  FAIL deploy.method is "%s" (expected rsync or git-push)\n' "$M";;
esac
if [ "$M" = "git-push" ]; then
  assert_nonempty "git-push declares post_deploy steps" "$(scripts/site deploy.post_deploy_hooks)"
fi

echo
printf '%s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
