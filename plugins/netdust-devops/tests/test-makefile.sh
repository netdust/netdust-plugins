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

# Every (stack, template) row in the registry must scaffold cleanly, with no
# token left unrendered. A token added to a template with no matching value
# ships a literal "{{THEME_FLAVOUR}}" into a real project's site.yml, where the
# first thing to read it takes the placeholder as a value.
#
# Asserted by SCAFFOLDING, not by grepping the script: the renderer loops over
# key names, so the literal "{{TOKEN}}" never appears in bin/new-project and a
# grep-based check silently passes forever.
SCAFF="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/bin/new-project"
REG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/templates/stacks.tsv"
TOKWORK=$(mktemp -d)
rowfail=""
while IFS=$'\t' read -r st tp rest; do
    case "$st" in ''|\#*) continue;; esac
    out="$TOKWORK/$st-$tp"
    if ! "$SCAFF" "tok${st}${tp//-/}" --stack="$st" --template="$tp" --dir="$out" >/dev/null 2>&1; then
        rowfail="$rowfail $st/$tp(scaffold-failed)"; continue
    fi
    left=$(grep -rohE '\{\{[A-Z_]+\}\}' "$out" --exclude-dir=.git --exclude-dir=mk \
             --exclude=Makefile.netdust 2>/dev/null | sort -u | tr '\n' ',' || true)
    [ -n "$left" ] && rowfail="$rowfail $st/$tp($left)"
    # …and the SCAFFOLDED OUTPUT must name no caller either. The plugin-level
    # check above misses this: a template can be clean in the repo and still
    # render a caller's name into every project it creates.
    named=$(grep -rlniE 'netdust-wp-manager|wp-manager|the fleet manager|the fleet.s weekly' \
              "$out" --exclude-dir=.git --exclude-dir=mk --exclude=Makefile.netdust \
              --exclude=work-audit.sh 2>/dev/null | sed "s|$out/||" | tr '\n' ' ' || true)
    [ -n "$named" ] && rowfail="$rowfail $st/$tp(names-caller: $named)"
done < "$REG"
rm -rf "$TOKWORK"
[ -z "$rowfail" ] && ok "every registry row scaffolds with no unrendered token" \
                  || bad "every registry row scaffolds with no unrendered token" "$rowfail"

# The registry is the only place a project shape is declared.
regcols=$(grep -vc '^#' "$REG" 2>/dev/null || echo 0)
[ "$regcols" -ge 5 ] && ok "the stack/template registry has $regcols rows" \
                     || bad "the stack/template registry has rows" "found $regcols"

# CALLERS vs TOOLS — the distinction this asserts.
#
# This plugin acts on ONE project, from inside its repo, and has no opinion
# about what INVOKES it: a person, an agent, a fleet tool reporting across many
# repos. Naming a caller inverts the dependency (the caller knows this plugin;
# this plugin must not know the caller) and, in a template, ships that
# assumption into every scaffolded project regardless of stack.
#
# It DOES name the tools it operates with — git, ddev, rsync, ssh, composer,
# herdr. Those are the environment the verbs run in, not things that call them,
# and refusing to name them would make the skills useless. The test targets
# callers only.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
callers=$(grep -rlniE 'netdust-wp-manager|wp-manager|new-site\.sh|the fleet manager' "$ROOT" \
            --exclude-dir=.git --exclude="$(basename "${BASH_SOURCE[0]}")" 2>/dev/null || true)
[ -z "$callers" ] && ok "the plugin names no caller" \
                  || bad "the plugin names no caller" "$(printf '%s' "$callers" | sed "s|$ROOT/||" | tr '\n' ' ')"

# A fleet-scoped command living here is the same inversion in command form.
fleetcmds=$(grep -rlniE '^description:.*(fleet|across (all|every) (site|project))' "$ROOT/commands" 2>/dev/null || true)
[ -z "$fleetcmds" ] && ok "no fleet-scoped command ships in the project layer" \
                    || bad "no fleet-scoped command ships in the project layer" "$(printf '%s' "$fleetcmds" | sed "s|$ROOT/||")"

# The mail block self-disables on production. A SUBSTRING test against WP_HOME
# is wrong whenever staging is a subdomain of production —
# strpos('https://staging.example.com','example.com') matches, so the block
# disabled itself on staging and let real mail out. 5 of 7 fleet projects were
# shaped that way (josworld, 2026-09-05).
BLOCK="$DIST/scripts/remote/00-block-outgoing-mail.php"
if grep -q 'strpos( *\$home' "$BLOCK" 2>/dev/null; then
    bad "mail block matches the production host exactly" "still uses strpos on WP_HOME"
else
    ok "mail block matches the production host exactly"
fi

# The decision must be behaviourally correct, not merely strpos-free.
if [ -f "$BLOCK" ] && command -v php >/dev/null 2>&1; then
    verdict=$(php -r '
        function add_action($a,$b,$c=10,$d=1){} function add_filter($a,$b,$c=10,$d=1){}
        $s = str_replace("__PRODUCTION_HOST__", "example.com", file_get_contents($argv[1]));
        eval(preg_replace("/^<\?php/", "", $s, 1));
        $bad = [];
        foreach (["https://staging.example.com" => false, "https://notexample.com" => false,
                  "" => false, "https://example.com" => true, "https://EXAMPLE.com" => true] as $home => $want) {
            if (ntdst_mail_block_is_production($home, "example.com") !== $want) { $bad[] = $home === "" ? "(empty)" : $home; }
        }
        echo $bad ? implode(",", $bad) : "ok";
    ' "$BLOCK" 2>&1)
    [ "$verdict" = "ok" ] && ok "mail block: staging subdomain stays blocked, production disables, empty fails closed" \
                          || bad "mail block host decision" "wrong verdict for: $verdict"
fi

# The block is installed INTO a payload directory that deploys rsync with
# --delete, and it exists only on the server — so the template must exclude it
# or every deploy removes it and mail silently resumes.
if grep -q '00-block-outgoing-mail\.php' "$DIST/../templates/site.yml.tmpl" 2>/dev/null; then
    ok "site.yml template excludes the mail block from --delete"
else
    bad "site.yml template excludes the mail block from --delete" "deploy.exclude is missing the entry"
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

echo "── worktrees: parallel agents each get one ──"
# Every promoting verb does `git checkout <rung>`, and a rung checked out in
# another worktree cannot be checked out here. Without a guard, `make finish`
# in a linked worktree died mid-verb on a raw git error —
#   fatal: 'development' is already used by worktree at ...
# — the exact shape _ensure-flow exists to prevent, and the normal case for any
# orchestrator that gives each parallel agent its own worktree.
WT="$WORK/wt"; mkdir -p "$WT"; cd "$WT"
git init -q --bare origin.git && git clone -q origin.git base 2>/dev/null && cd base
mkdir -p scripts web
cp "$DIST/scripts/devops-version" scripts/ && chmod +x scripts/devops-version
cat > site.yml <<'WTYML'
site: {name: wt, domain: wt.invalid, risk: low}
structure: {stack: generic, type: custom-site, webroot: web}
environments:
  development: {url: "https://dev.wt.invalid", path: /srv/d, branch: development, role: sandbox, confirm: false}
  staging:     {url: "https://stg.wt.invalid", path: /srv/s, branch: staging, role: review, confirm: false}
  production:  {url: "https://wt.invalid", path: /srv/p, branch: main, role: live, confirm: true}
deploy: {method: rsync, ssh_host: nobody@wt.invalid, state_dir: /srv/.s, payload: [], exclude: [".git*"]}
local: {ddev_project: wt, url: "https://wt.ddev.site"}
commands: {test: "true", gate: "true"}
WTYML
NETDUST_DEVOPS_DIST="$DIST" scripts/devops-version --update >/dev/null 2>&1
printf 'STACK := generic\ninclude Makefile.netdust\n' > Makefile
touch web/.gitkeep
git add -A && git -c user.email=t@t -c user.name=T commit -qm init >/dev/null && git branch -M main
git push -q -u origin main 2>/dev/null
git push -q origin main:staging 2>/dev/null && git push -q origin main:development 2>/dev/null
git checkout -q -b development origin/development
git worktree add -q ../agent -b feature/par origin/development
cd ../agent && echo work > web/f.txt
git add -A && git -c user.email=t@t -c user.name=T commit -qm "parallel work" >/dev/null

wtout=$(timeout 60 make finish < /dev/null 2>&1 | strip)
if printf '%s' "$wtout" | grep -q 'already used by worktree'; then
    bad "finish refuses by name in a linked worktree" "it died on the raw git error"
elif printf '%s' "$wtout" | grep -q 'checked out in another worktree'; then
    ok "finish refuses by name in a linked worktree"
else
    bad "finish refuses by name in a linked worktree" "$(printf '%s' "$wtout" | tail -2)"
fi
printf '%s' "$wtout" | grep -q 'make finish name=par' \
    && ok "the refusal names the command that actually works" \
    || bad "the refusal names the command that actually works" "$(printf '%s' "$wtout" | grep -i 'cd ' | head -1)"

cd "$WT/base"
finout=$(timeout 60 make finish name=par < /dev/null 2>&1 | strip)
printf '%s' "$finout" | grep -q 'Merged to development' \
    && ok "finish name=<x> merges a branch held by another worktree" \
    || bad "finish name=<x> merges a branch held by another worktree" "$(printf '%s' "$finout" | tail -2)"
git log --oneline development 2>/dev/null | grep -q 'Merge feature/par' \
    && ok "the parallel work actually landed on the rung" \
    || bad "the parallel work actually landed" "no merge commit on development"
printf '%s' "$finout" | grep -q 'kept — it is checked out in a worktree' \
    && ok "a branch still held by a worktree is kept, not silently left half-deleted" \
    || bad "a held branch is reported" "$(printf '%s' "$finout" | tail -1)"

missout=$(timeout 60 make finish name=nosuch < /dev/null 2>&1 | strip)
printf '%s' "$missout" | grep -q 'No feature/nosuch or hotfix/nosuch' \
    && ok "finish name=<unknown> refuses and lists what is in flight" \
    || bad "finish name=<unknown> refuses" "$(printf '%s' "$missout" | tail -2)"
cd "$P"

echo
echo "── adopting an existing project ──"
# A project that predates this plugin must be able to gain `make` WITHOUT
# losing the site.yml someone filled in by hand. Without --adopt the only
# options were "refuse" and "--force, which overwrites site.yml" — i.e. copy
# the files in by hand, the exact thing this plugin exists to end.
AD="$WORK/adopt"; mkdir -p "$AD/memory" "$AD/tasks" "$AD/web/app/plugins/p"; cd "$AD"
cat > site.yml <<'ADYML'
site: {name: adopted, domain: adopted.invalid, risk: high}
structure: {stack: wp, type: bedrock, webroot: web, wpcli_path: web/wp}
environments:
  production: {url: "https://adopted.invalid", path: /srv/a, branch: main, role: live, confirm: true}
deploy: {method: rsync, ssh_host: nobody@adopted.invalid, state_dir: /srv/.s, wp_path: web/wp, content_dir: web/app, payload: [app/plugins/p]}
local: {ddev_project: adopted, url: "https://adopted.ddev.site"}
commands: {test: "true", gate: "true"}
ADYML
printf 'HAND WRITTEN STATE\n'  > memory/STATE.md
printf -- '- [ ] a real task\n' > tasks/todo.md
printf 'MY OWN RULES\n'         > CLAUDE.md
printf 'legacy:\n\t@echo old\n' > Makefile
git init -q . && git add -A && git -c user.email=t@t -c user.name=T commit -qm pre
AD_BEFORE=$(git rev-parse HEAD)

adopt_out=$("$SCAFF" adopted --stack=wp --adopt 2>&1)
if [ $? -ne 0 ]; then
    bad "--adopt succeeds on an existing project" "$(printf '%s' "$adopt_out" | tail -2)"
else
    ok "--adopt succeeds on an existing project"
    grep -q 'risk: high' site.yml && grep -q 'app/plugins/p' site.yml \
        && ok "--adopt keeps the existing site.yml" \
        || bad "--adopt keeps the existing site.yml" "it was overwritten"
    grep -q 'HAND WRITTEN STATE' memory/STATE.md && grep -q 'a real task' tasks/todo.md \
        && grep -q 'MY OWN RULES' CLAUDE.md \
        && ok "--adopt keeps notes and CLAUDE.md" \
        || bad "--adopt keeps notes and CLAUDE.md" "one was overwritten"
    grep -q 'old' Makefile.pre-devops 2>/dev/null \
        && ok "--adopt preserves the old Makefile beside the new one" \
        || bad "--adopt preserves the old Makefile" "Makefile.pre-devops missing"
    [ "$AD_BEFORE" = "$(git rev-parse HEAD)" ] \
        && ok "--adopt never touches git" \
        || bad "--adopt never touches git" "it committed or branched"
    [ -f Makefile.netdust ] && [ -f scripts/site ] && [ -f .netdust-devops ] \
        && ok "--adopt vendors the core" \
        || bad "--adopt vendors the core" "missing Makefile.netdust / scripts/site / .netdust-devops"
    make status >/dev/null 2>&1 \
        && ok "make runs in the adopted project" \
        || bad "make runs in the adopted project" "$(make status 2>&1 | head -2)"
fi
cd "$P"

echo
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
