#!/usr/bin/env bash
# Structural + behavioural tests for the vendored devops core.
# Contacts no server: every environment in the fixture points at an
# unroutable host, and every test stops at a local gate before transport.

set -uo pipefail
DIST="$(cd "$(dirname "${BASH_SOURCE[0]}")/../dist" && pwd)"
PASS=0; FAIL=0
ok()   { printf '  ✅ %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  ❌ %s\n'  "$1"; printf '     %s\n' "${2:-}"; FAIL=$((FAIL+1)); }
strip() { sed 's/\x1b\[[0-9;]*m//g'; }

echo "── structure ──"

# A backtick inside a shell recipe is command substitution, not a comment.
# `@: "... `make ship` ..."` re-invoked make and recursed until the process
# table gave out. Comments in recipes use single quotes and no backticks.
if grep -nE '^\t.*`' "$DIST/Makefile.netdust" "$DIST"/mk/*.mk >/dev/null 2>&1; then
    bad "no backticks in recipe lines" "$(grep -nE '^\t.*`' "$DIST/Makefile.netdust" "$DIST"/mk/*.mk | head -3)"
else
    ok "no backticks in recipe lines"
fi

# Every stack must define the four hooks Makefile.netdust calls, directly or
# through an include. A missing one silently no-ops a safety step.
for mk in wp statamic node generic; do
    missing=""
    body=$(cat "$DIST/mk/$mk.mk")
    case "$body" in *"include mk/ddev.mk"*) body="$body$(cat "$DIST/mk/ddev.mk")";; esac
    for hook in _help-stack _status-stack _doctor-stack _backup-data; do
        case "$body" in *"$hook:"*) ;; *) missing="$missing $hook";; esac
    done
    [ -z "$missing" ] && ok "mk/$mk.mk defines all four hooks" \
                      || bad "mk/$mk.mk missing hooks" "$missing"
done

# Makefile.netdust must not define the hooks itself: a default recipe wins over
# the stack's (last definition wins) and make only warns.
if grep -qE '^(_help-stack|_status-stack|_doctor-stack|_backup-data):' "$DIST/Makefile.netdust"; then
    bad "core defines no stack hooks" "found a hook recipe in Makefile.netdust"
else
    ok "core defines no stack hooks"
fi

echo "── behaviour ──"
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
P="$WORK/proj"; mkdir -p "$P/web/app/plugins/p" "$P/web/app/themes/t"; cd "$P"
# A payload path must be TRACKED in git, not merely present: an untracked one
# deploys as an empty directory and a rollback --deletes it off the server.
# deploy-test.sh asserts exactly that, so the fixture has to satisfy it.
echo '<?php // fixture' > "$P/web/app/plugins/p/p.php"
cat > site.yml <<'YML'
site: {name: fixture, domain: example.invalid, risk: low}
structure: {type: bedrock, stack: wp, webroot: web, wpcli_path: web/wp}
environments:
  staging:    {url: "https://staging.example.invalid", path: /srv/staging, branch: staging, role: review, confirm: false}
  production: {url: "https://example.invalid", path: /srv/prod, branch: main, role: live, confirm: true}
deploy:
  method: rsync
  ssh_host: nobody@example.invalid
  state_dir: /srv/.state
  wp_path: web/wp
  content_dir: app
  payload: [app/plugins/p]
  exclude: [".git*", "node_modules", "*.log", "/memory/", "/tasks/"]
local: {ddev_project: fixture, url: "https://fixture.ddev.site"}
commands: {gate: "true"}
YML
mkdir -p scripts && cp "$DIST/scripts/devops-version" scripts/ && chmod +x scripts/devops-version
NETDUST_DEVOPS_DIST="$DIST" scripts/devops-version --update >/dev/null 2>&1
printf 'STACK := wp\ninclude Makefile.netdust\n' > Makefile
git init -q . && git add -A && git -c user.email=t@t -c user.name=T commit -qm init
git branch -q -m main
git init -q --bare "$WORK/origin.git" && git remote add origin "$WORK/origin.git"
# main must be ON origin: the flow floor refuses any verb while a rung carries
# unpushed commits, and that refusal would mask the one under test.
git push -q -u origin main 2>/dev/null && git push -q origin main:staging 2>/dev/null

out=$(make help 2>&1 | strip)
case "$out" in
    *"warning: overriding recipe"*) bad "make help emits no override warnings" "$(printf '%s' "$out" | grep warning | head -2)";;
    *"DDEV + WordPress"*)           ok  "make help shows the stack's own verbs";;
    *)                              bad "make help shows the stack's own verbs" "LOCAL block missing";;
esac

# The recursion regression: ship must terminate, and must refuse without a tty
# BEFORE the gate or either backup runs (both of those touch the server).
out=$(timeout 20 make ship < /dev/null 2>&1 | strip)
rc=$?
if [ $rc -eq 124 ]; then
    bad "ship terminates" "timed out — recursion regression"
elif ! printf '%s' "$out" | grep -q "needs a terminal"; then
    bad "ship refuses without a terminal" "$(printf '%s' "$out" | head -2)"
elif printf '%s' "$out" | grep -qE "gate passed|Backing up"; then
    bad "ship refuses BEFORE gate and backups" "server work ran before the tty check"
else
    ok "ship refuses without a terminal, before any server contact"
fi

out=$(timeout 20 make release < /dev/null 2>&1 | strip)
printf '%s' "$out" | grep -q "needs a terminal" \
    && ok "release refuses without a terminal" \
    || bad "release refuses without a terminal" "$(printf '%s' "$out" | head -2)"

# promote checks the feature exists before the tty guard (a local check, no
# server contact) — so the fixture needs a real feature branch to reach it.
git branch -q feature/x main && git push -q origin feature/x 2>/dev/null
out=$(timeout 20 make promote name=x < /dev/null 2>&1 | strip)
printf '%s' "$out" | grep -q "needs a terminal" \
    && ok "promote refuses without a terminal" \
    || bad "promote refuses without a terminal" "$(printf '%s' "$out" | head -2)"

out=$(timeout 20 make deploy env=staging < /dev/null 2>&1 | strip)
printf '%s' "$out" | grep -q "staging deploys from 'staging'" \
    && ok "deploy refuses from the wrong branch" \
    || bad "deploy refuses from the wrong branch" "$(printf '%s' "$out" | head -2)"

out=$(timeout 20 make save < /dev/null 2>&1 | strip)
printf '%s' "$out" | grep -q "deploy-only, never worked on" \
    && ok "save refuses on a rung branch" \
    || bad "save refuses on a rung branch" "$(printf '%s' "$out" | head -2)"

out=$(timeout 20 make deploy env=nosuchenv < /dev/null 2>&1 | strip)
printf '%s' "$out" | grep -q "Unknown environment" \
    && ok "deploy refuses an unknown environment" \
    || bad "deploy refuses an unknown environment" "$(printf '%s' "$out" | head -2)"

# An unknown stack must fall back to generic rather than fail to parse.
sed -i 's/^STACK := wp/STACK := nosuchstack/' Makefile
out=$(timeout 20 make help 2>&1 | strip)
printf '%s' "$out" | grep -q "no local-loop verbs" \
    && ok "unknown stack falls back to generic.mk" \
    || bad "unknown stack falls back to generic.mk" "$(printf '%s' "$out" | head -3)"

# generic has no data verb: ship must refuse rather than back up nothing.
out=$(timeout 20 make _backup-data env=production < /dev/null 2>&1 | strip)
printf '%s' "$out" | grep -q "refuses to back up nothing" \
    && ok "a stack with no data verb refuses to ship" \
    || bad "a stack with no data verb refuses to ship" "$(printf '%s' "$out" | head -2)"
sed -i 's/^STACK := nosuchstack/STACK := wp/' Makefile

# The vendored tooling tests must run under the SPLIT layout. flow-test.sh
# builds its own throwaway repo, and when the Makefile became
# Makefile.netdust + mk/ it kept copying only `Makefile` — 31 of its 35 checks
# failed with "No such file or directory" while the core itself was fine.
# Running them here is the only thing that catches that class of break.
out=$(timeout 300 make test < /dev/null 2>&1 | strip)
if printf '%s' "$out" | grep -q "No such file or directory"; then
    bad "make test runs under the split layout" "$(printf '%s' "$out" | grep 'No such file' | head -1)"
elif printf '%s' "$out" | grep -qE "^flow-test: [0-9]+ ok, 0 failed"; then
    ok "make test runs the vendored suites under the split layout"
else
    bad "make test runs under the split layout" "$(printf '%s' "$out" | tail -3)"
fi

echo "── vendoring ──"
printf '\n# edited by hand\n' >> mk/wp.mk
out=$(NETDUST_DEVOPS_DIST="$DIST" scripts/devops-version --check 2>&1 | strip)
printf '%s' "$out" | grep -q "EDITED IN PLACE: mk/wp.mk" \
    && ok "drift check names a file edited in place" \
    || bad "drift check names a file edited in place" "$(printf '%s' "$out" | head -2)"

NETDUST_DEVOPS_DIST="$DIST" scripts/devops-version --update >/dev/null
out=$(NETDUST_DEVOPS_DIST="$DIST" scripts/devops-version --check 2>&1 | strip)
printf '%s' "$out" | grep -q "current" \
    && ok "update restores the managed files" \
    || bad "update restores the managed files" "$(printf '%s' "$out" | head -2)"

# The project's own Makefile is the one file vendoring must never touch.
grep -q "^STACK := wp" Makefile \
    && ok "devops-update leaves the project Makefile alone" \
    || bad "devops-update leaves the project Makefile alone" "project Makefile was overwritten"

echo
printf '%s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
