#!/usr/bin/env bash
# Structural + behavioural tests for the vendored devops core.
# Contacts no server: every environment in the fixture points at an
# unroutable host, and every test stops at a local gate before transport.

set -uo pipefail
DIST="$(cd "$(dirname "${BASH_SOURCE[0]}")/../dist" && pwd)"
ROOT="$(dirname "$DIST")"
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

# The middle rung is gone: no variable for it, and no verb that merges one rung
# into the next (FR-1, FR-2). The scaffolder and the templates are swept too —
# a template that teaches it ships the removed rung into every new project. The
# forbidden strings are assembled here rather than spelled, so this file stays
# clean under the sweep it asserts.
rung=$(grep -rlE "BR_""INTEG|make ""release\b" "$DIST" "$ROOT/bin" "$ROOT/templates" 2>/dev/null \
         | sed "s|$ROOT/||" | tr '\n' ' ')
[ -z "$rung" ] && ok "the core, the scaffolder and the templates name no removed rung or verb" \
               || bad "the core, the scaffolder and the templates name no removed rung or verb" "$rung"

# Every (stack, template) row in the registry must scaffold cleanly, with no
# token left unrendered. A token added to a template with no matching value
# ships a literal "{{THEME_FLAVOUR}}" into a real project's site.yml, where the
# first thing to read it takes the placeholder as a value.
#
# Asserted by SCAFFOLDING, not by grepping the script: the renderer loops over
# key names, so the literal "{{TOKEN}}" never appears in bin/new-project and a
# grep-based check silently passes forever.
SCAFF="$ROOT/bin/new-project"
REG="$ROOT/templates/stacks.tsv"
TOKWORK=$(mktemp -d)
rowfail=""; brfail=""; flowfail=""
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
    # A fresh project has the two rungs and nothing else, so nothing it does
    # next can be refused as unmigrated (FR-11, SC-7).
    br=$(git -C "$out" branch --format='%(refname:short)' 2>/dev/null | sort | paste -sd' ')
    [ "$br" = "main staging" ] || brfail="$brfail $st/$tp(branches: ${br:-none})"
    fout=$(cd "$out" && timeout 20 make --no-print-directory feature name=x < /dev/null 2>&1 | strip)
    case "$fout" in *"environments.development"*) flowfail="$flowfail $st/$tp(refused-as-unmigrated)";; esac
    case "$fout" in *"no 'origin' remote"*) ;; *) flowfail="$flowfail $st/$tp(never-reached-the-flow-floor)";; esac
done < "$REG"
rm -rf "$TOKWORK"
[ -z "$rowfail" ] && ok "every registry row scaffolds with no unrendered token" \
                  || bad "every registry row scaffolds with no unrendered token" "$rowfail"
[ -z "$brfail" ] && ok "…and creates main and staging only" \
                 || bad "…and creates main and staging only" "$brfail"
[ -z "$flowfail" ] && ok "…and its first make feature is not refused as unmigrated" \
                   || bad "…and its first make feature is not refused as unmigrated" "$flowfail"

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

# doctor reports the commands.* keys a core reads that site.yml never declared; a
# key it expects must also be one a new project is scaffolded with.
EXPECTED=$(sed -n 's/^_DOCTOR_COMMANDS := //p' "$DIST/Makefile.netdust")
MISSING=""
for k in $EXPECTED; do grep -qE "^  $k: " "$ROOT/templates/site.yml.tmpl" || MISSING="$MISSING $k"; done
if [ -n "$EXPECTED" ] && [ -z "$MISSING" ]; then
    ok "every commands.* key doctor expects ($EXPECTED) is in the site.yml template"
else
    bad "every commands.* key doctor expects is in the site.yml template" "missing:${MISSING:- (no list found)}"
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
  exclude: [".git*", "node_modules", "*.log", "/memory/", "/tasks/", "00-block-outgoing-mail.php"]
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

# ship leaves from the staging branch or a hotfix branch, and never checks you
# out anywhere first — the old _ship-branch switched you onto production before
# the gate ran. _ship-path is the step, tested on its own because ship's tty
# check comes first and a test has no tty.
git checkout -q -b staging origin/staging
out=$(timeout 20 make _ship-path 2>&1 | strip)
if [ "$(git branch --show-current)" = "staging" ] && printf '%s' "$out" | grep -q "deployed/staging"; then
    ok "ship wants a deployed staging, and moves nobody"
else
    bad "ship wants a deployed staging, and moves nobody" "on $(git branch --show-current): $(printf '%s' "$out" | head -2)"
fi
git checkout -q main
out=$(timeout 20 make _ship-path 2>&1 | strip)
if [ "$(git branch --show-current)" = "main" ] && printf '%s' "$out" | grep -q "hotfix"; then
    ok "ship refuses from a branch that is neither route, naming both"
else
    bad "ship refuses from a branch that is neither route, naming both" "on $(git branch --show-current): $(printf '%s' "$out" | head -2)"
fi
git checkout -q staging && echo dirty >> site.yml
out=$(timeout 20 make _ensure-clean-git verb=ship 2>&1 | strip)
if printf '%s' "$out" | grep -q "uncommitted" && printf '%s' "$out" | grep -q "Nothing uncommitted ships"; then
    ok "ship refuses a dirty tree"
else
    bad "ship refuses a dirty tree" "$(printf '%s' "$out" | head -2)"
fi
git checkout -q -- site.yml && git checkout -q main

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
out=$(timeout 900 make test < /dev/null 2>&1 | strip)
if printf '%s' "$out" | grep -q "No such file or directory"; then
    bad "make test runs under the split layout" "$(printf '%s' "$out" | grep 'No such file' | head -1)"
elif printf '%s' "$out" | grep -qE "^flow-test: [0-9]+ ok, 0 failed"; then
    ok "make test runs the vendored suites under the split layout"
else
    bad "make test runs under the split layout" "$(printf '%s' "$out" | tail -3)"
fi

echo "── a rung without a server ──"
# A project declares every rung even before it has a server for each: the
# devops skill says to declare production with its branch and NO path, and a
# development rung may be branch-only. The vendored deploy-test.sh demanded
# url+path on every environment and compared state_dir against an EMPTY path
# (""/* matches everything), so a correctly shaped site.yml failed 5 checks
# (todai-client, 2026-09-08).
R="$WORK/rungs"; mkdir -p "$R/web/app" "$R/scripts"; cd "$R"
cat > site.yml <<'RYML'
site: {name: rungs, domain: rungs.invalid, risk: low}
structure: {type: bedrock, stack: wp, webroot: web, wpcli_path: web/wp}
environments:
  development: {branch: development, role: "no server — this project never migrated off it", confirm: false}
  staging:     {url: "https://staging.rungs.invalid", path: /srv/staging, branch: staging, role: "live client subdomain", confirm: true}
  production:  {url: "https://rungs.invalid", branch: main, role: "not provisioned — main is the production branch", confirm: true}
deploy:
  method: git-push
  ssh_host: nobody@rungs.invalid
  state_dir: /srv/.state
  wp_path: web/wp
  content_dir: web/app
  payload: []
  post_deploy_hooks: ["composer install --no-dev --no-interaction"]
local: {ddev_project: rungs, url: "https://rungs.ddev.site"}
commands: {gate: "true"}
RYML
cp "$DIST/scripts/devops-version" scripts/ && chmod +x scripts/devops-version
NETDUST_DEVOPS_DIST="$DIST" scripts/devops-version --update >/dev/null 2>&1
printf 'STACK := wp\ninclude Makefile.netdust\n' > Makefile
touch web/app/.gitkeep
git init -q . && git add -A && git -c user.email=t@t -c user.name=T commit -qm init
git branch -q -m main
git init -q --bare "$WORK/rungs-origin.git" && git remote add origin "$WORK/rungs-origin.git"
git push -q -u origin main 2>/dev/null && git push -q origin main:staging main:development 2>/dev/null

out=$(timeout 120 scripts/tests/deploy-test.sh 2>&1 | strip)
if printf '%s' "$out" | grep -qE "^[0-9]+ passed, 0 failed"; then
    ok "deploy-test accepts a branch-only rung and a pathless production"
else
    bad "deploy-test accepts a branch-only rung and a pathless production" "$(printf '%s' "$out" | grep FAIL | head -3 | tr '\n' ' ')"
fi

# Over git-push there is no payload to archive — it lives in git, and the
# previous commit is the rollback. _backup-payload tarred nothing, measured
# 0 bytes and refused the ship; daan's first production ship stopped between
# the server revert and the pull (2026-09-03). It must say so and exit 0
# without touching the server.
out=$(timeout 20 make _backup-payload env=production < /dev/null 2>&1); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -eq 0 ] && printf '%s' "$out" | grep -q "payload lives in git"; then
    ok "ship skips the payload archive on git-push"
else
    bad "ship skips the payload archive on git-push" "exit $rc: $(printf '%s' "$out" | head -2 | tr '\n' ' ')"
fi

# This fixture never migrated off `development`, which two live client projects
# have not either (FR-10). No verb here merges into a third rung, so each one
# that would refuses — naming the migration and the way back to the core that
# still had it — before it creates a branch or touches origin. The terminal
# guard fires first on promote, unpromote and ship, so all five run under a pty.
REMOTES=$(git ls-remote origin); BRANCHES=$(git branch --list 'feature/*' 'hotfix/*')
unmig=""
for v in "feature name=x" "hotfix name=x" "promote name=x" "unpromote name=x" "ship"; do
    out=$(timeout 30 script -qec "make --no-print-directory $v" /dev/null <<< yes 2>&1); rc=$?
    out=$(printf '%s' "$out" | strip | tr -d '\r')
    [ $rc -ne 0 ] || unmig="$unmig ${v%% *}(exit-0)"
    printf '%s' "$out" | grep -q "drop environments.development from site.yml" \
        || unmig="$unmig ${v%% *}(no-migrate-line)"
    printf '%s' "$out" | grep -q "git checkout <commit before the update> -- Makefile.netdust mk scripts .netdust-devops" \
        || unmig="$unmig ${v%% *}(no-way-back)"
done
[ -z "$unmig" ] && ok "every merging verb refuses on an unmigrated project, naming the migration and the way back" \
               || bad "every merging verb refuses on an unmigrated project, naming the migration and the way back" "$unmig"
[ "$(git branch --list 'feature/*' 'hotfix/*')" = "$BRANCHES" ] && [ "$(git ls-remote origin)" = "$REMOTES" ] \
    && ok "…and it branched nothing and left origin exactly as it was" \
    || bad "…and it branched nothing and left origin exactly as it was" "$(git branch --list 'feature/*' 'hotfix/*')"

# Everything that does not merge keeps working: the refusal is a flow floor,
# not a lockout of the project.
if timeout 60 make status < /dev/null >/dev/null 2>&1 && timeout 20 make gate < /dev/null >/dev/null 2>&1; then
    ok "…while status and gate still run there"
else
    bad "…while status and gate still run there" "status or gate exited non-zero"
fi
cd "$P"

echo "── worktrees: parallel agents each get one ──"
# promote used to `git checkout <rung>`, so a rung held by another worktree died
# mid-verb on a raw git error —
#   fatal: 'staging' is already used by worktree at ...
# The rebuild does its merging in a throwaway worktree of its own and pushes,
# so the rung is never checked out here: the normal case for an orchestrator
# that gives each parallel agent a worktree simply works.
WT="$WORK/wt"; mkdir -p "$WT"; cd "$WT"
git init -q --bare origin.git && git clone -q origin.git base 2>/dev/null && cd base
mkdir -p scripts web
cp "$DIST/scripts/devops-version" scripts/ && chmod +x scripts/devops-version
cat > site.yml <<'WTYML'
site: {name: wt, domain: wt.invalid, risk: low}
structure: {stack: generic, type: custom-site, webroot: web}
environments:
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
git push -q origin main:staging 2>/dev/null
git checkout -q -b staging origin/staging
git worktree add -q ../agent -b feature/par origin/main
cd ../agent && echo work > web/f.txt
git add -A && git -c user.email=t@t -c user.name=T commit -qm "parallel work" >/dev/null
git push -q origin feature/par 2>/dev/null

WTN=$(git worktree list | wc -l | tr -d ' ')
wtout=$(timeout 60 script -qec "make promote name=par" /dev/null <<< yes 2>&1 | strip)
git fetch -q origin
subj=$(git log --merges --first-parent --format='%s' origin/main..origin/staging | paste -sd' ')
if printf '%s' "$wtout" | grep -q 'already used by worktree'; then
    bad "promote runs from a linked worktree while the rung is checked out elsewhere" "it died on the raw git error"
elif [ "$subj" = "promote: par" ]; then
    ok "promote runs from a linked worktree while the rung is checked out elsewhere"
else
    bad "promote runs from a linked worktree while the rung is checked out elsewhere" "$(printf '%s' "$wtout" | tail -2)"
fi
[ "$(git worktree list | wc -l | tr -d ' ')" = "$WTN" ] \
    && ok "…and it took its own throwaway worktree with it" \
    || bad "…and it took its own throwaway worktree with it" "$(git worktree list | tail -2)"
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
    stout=$(make status 2>&1); strc=$?
    [ $strc -eq 0 ] \
        && ok "make runs in the adopted project" \
        || bad "make runs in the adopted project" "$(printf '%s' "$stout" | head -2)"
    printf '%s' "$stout" | grep -q "STAGING" \
        && bad "a project with no staging environment shows no staging block" "$(printf '%s' "$stout" | grep -A3 STAGING)" \
        || ok "a project with no staging environment shows no staging block"
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
echo "── command-line allowlist ──"
# Every variable settable on a make command line reaches a shell inside a
# double-quoted string, where $( ) substitutes and a " ends the quote — so
# `make rollback env='a"; touch PWNED; echo "'` used to run the payload. Each
# case pins the refusal's reason AND the absence of its marker: a non-zero exit
# on its own would be vacuous.
cd "$P"; git checkout -q -- . 2>/dev/null; rm -f dirt.txt
CLI="$WORK/cli"; mkdir -p "$CLI/bin"
# Real ssh reads no stdin under -n, and the core gives -n to every read
# (`deployed`, rollback's ledger tail) while the ledger WRITES pipe data into a
# plain `ssh -q`. A shim that swallows stdin either way hangs the whole suite
# whenever the runner's own stdin is an open stream that never sends EOF.
cat > "$CLI/bin/ssh" <<SH
#!/bin/sh
echo "\$*" >> "$CLI/ssh.log"
case " \$* " in *" -qn "*|*" -n "*) exec < /dev/null;; esac
case "\$*" in *"tail -2"*) tail -2 "$CLI/ledger" 2>/dev/null | head -1;; *) cat >/dev/null;; esac
SH
cat > "$CLI/bin/rsync" <<SH
#!/bin/sh
printf '[%s]' "\$@" >> "$CLI/rsync.log"; echo >> "$CLI/rsync.log"
SH
chmod +x "$CLI/bin/ssh" "$CLI/bin/rsync"
CLIPATH="$CLI/bin:$PATH"
M() { env PATH="$CLIPATH" make --no-print-directory "$@" < /dev/null 2>&1; }
pwned() { (cd "$CLI" && ls pwn-* 2>/dev/null | paste -sd' '); }
# Three payload forms per sink: make's own expansion, command substitution in
# the shell the recipe builds, and a break out of the surrounding "…".
inject() {
    local dir="$1" tgt="$2" var="$3" f; shift 3
    for f in "\$(shell touch $CLI/pwn-$tgt-$var-make)" "\$(touch $CLI/pwn-$tgt-$var-sub)" \
             "a\"; touch $CLI/pwn-$tgt-$var-quote; echo \""; do
        env PATH="$CLIPATH" make -C "$dir" --no-print-directory "$tgt" "$@" "$var=$f" \
            < /dev/null > /dev/null 2>&1
    done
}

git checkout -q staging
inject "$P" rollback        env
inject "$P" deploy          env
inject "$P" _need-tty       verb
inject "$P" _worktree-guard rung
inject "$P" deploy          dryrun env=staging
echo dirt > dirt.txt; inject "$P" _ensure-clean-git verb; rm -f dirt.txt
[ -z "$(pwned)" ] && ok "env=, verb=, rung= and dryrun= run nothing in the targets that interpolate them" \
                  || bad "env=, verb=, rung= and dryrun= run nothing in the targets that interpolate them" "$(pwned)"

out=$(M _need-tty 'verb=a"; echo "' | strip)
printf '%s' "$out" | grep -q "Refused verb=" \
    && ok "…and the refusal names the variable it refused" \
    || bad "…and the refusal names the variable it refused" "$(printf '%s' "$out" | head -2)"

# name= is checked by the verbs themselves: its empty case needs the Usage line.
for v in feature hotfix promote unpromote; do
    for f in "a\"; touch $CLI/pwn-name-$v; echo \"" "\$(shell touch $CLI/pwn-nameshell-$v)"; do
        M "$v" "name=$f" > /dev/null 2>&1
    done
done
[ -z "$(pwned)" ] && ok "a quote-break or \$(shell) payload in name= reaches no shell" \
                  || bad "a quote-break or \$(shell) payload in name= reaches no shell" "$(pwned)"

# The stack layers are not edited: one make variable is global to the
# invocation, so the core's parse-time refusal covers a sink it cannot see.
WPU="$WORK/wpu"; cp -r "$P" "$WPU"
printf 'STACK := wp\ninclude Makefile.netdust\n_check-ddev _pull-db _pull-plugins _pull-uploads:\n\t@:\n' > "$WPU/Makefile"
inject "$WPU" pull uploads
[ -z "$(pwned)" ] && ok "uploads= runs nothing in the wp layer's pull, which the core never sees" \
                  || bad "uploads= runs nothing in the wp layer's pull, which the core never sees" "$(pwned)"

# A variable the flow does not take is not an operator input at all. SITE= is
# the command in $(shell $(SITE) …), so it would run at PARSE time.
for v in "SITE=touch $CLI/pwn-site; scripts/site" "WEBROOT=a\"; touch $CLI/pwn-webroot; echo \"" "_name-ok=ok"; do
    M status "$v" > /dev/null 2>&1
    M promote "$v" "name=a\"; touch $CLI/pwn-nameloose; echo \"" > /dev/null 2>&1
done
[ -z "$(pwned)" ] && ok "SITE=, WEBROOT= and _name-ok= are refused, so none of them reaches a shell" \
                  || bad "SITE=, WEBROOT= and _name-ok= are refused, so none of them reaches a shell" "$(pwned)"

out=$(M status SITE=x); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "SITE is not an operator input"; then
    ok "make status SITE=… is refused at parse, naming SITE"
else
    bad "make status SITE=… is refused at parse, naming SITE" "exit $rc: $(printf '%s' "$out" | head -2)"
fi

out=$(M help NAME=x); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "NAME is not an operator input"; then
    ok "make help NAME=x is refused, naming NAME"
else
    bad "make help NAME=x is refused, naming NAME" "exit $rc: $(printf '%s' "$out" | head -2)"
fi

# A project whose own target takes NAME opens the door itself, ABOVE the
# include — _CLI_VARS is :=, so a declaration below it is read too late.
cp Makefile "$CLI/Makefile.keep"
printf 'STACK := wp\n_CLI_EXTRA := NAME\ninclude Makefile.netdust\n' > Makefile
out=$(M help NAME=x); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -eq 0 ] && printf '%s' "$out" | grep -q "FLOW"; then
    ok "…and _CLI_EXTRA := NAME lets the project's own input through"
else
    bad "…and _CLI_EXTRA := NAME lets the project's own input through" "exit $rc: $(printf '%s' "$out" | head -2)"
fi
awk '/_CLI_EXTRA/{d=NR} /^include Makefile.netdust/{i=NR} END{exit !(d && i && d < i)}' Makefile \
    && ok "…declared above the include, where the core still reads it" \
    || bad "…declared above the include, where the core still reads it" "$(cat Makefile)"
cp "$CLI/Makefile.keep" Makefile

# -e is the same hole from the other side: it lets the environment overwrite
# every value this file reads from site.yml.
out=$(env PATH="$CLIPATH" BLUE="a\"; touch $CLI/pwn-dashe; echo \"" \
        make -e --no-print-directory help < /dev/null 2>&1); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "make -e is refused" && [ -z "$(pwned)" ]; then
    ok "make -e is refused: the environment may not overwrite what site.yml declares"
else
    bad "make -e is refused: the environment may not overwrite what site.yml declares" "exit $rc: $(printf '%s' "$out" | head -2) $(pwned)"
fi

# make's own flags are the same hole again: -i runs past every failed check, and
# under -n, -t and -q a recipe line holding $(MAKE) still executes.
flagbad=""
for f in -i -n -t -q --ignore-errors --dry-run --just-print --recon --touch --question --environment-overrides; do
    out=$(M "$f" help); rc=$?
    { [ $rc -ne 0 ] && printf '%s' "$out" | strip | grep -q "is refused"; } || flagbad="$flagbad $f(exit-$rc)"
done
[ -z "$flagbad" ] && ok "-i, -n, -t, -q and every long spelling of them are refused at parse" \
                  || bad "-i, -n, -t, -q and every long spelling of them are refused at parse" "$flagbad"
M -i promote "name=x\";touch $CLI/pwn-dashi;echo \"" > /dev/null 2>&1
[ -z "$(pwned)" ] && ok "…so -i cannot carry a name= payload past _check-name" \
                  || bad "…so -i cannot carry a name= payload past _check-name" "$(pwned)"
flagbad=""
for f in -s -k -j2; do
    out=$(M "$f" help); rc=$?
    { [ $rc -eq 0 ] && printf '%s' "$out" | grep -q "FLOW"; } || flagbad="$flagbad $f(exit-$rc)"
done
[ -z "$flagbad" ] && ok "…while -s, -k and -j2 still run" || bad "…while -s, -k and -j2 still run" "$flagbad"

# STACK is the same hole once more: help echoes it inside a double-quoted shell
# string, and `?=` takes an exported one whenever the project Makefile declares
# none — which the scaffold always does, so only a hand-written Makefile is bare.
NOSTK="$WORK/nostack"; cp -r "$P" "$NOSTK"
printf 'include Makefile.netdust\n' > "$NOSTK/Makefile"
out=$(env PATH="$CLIPATH" STACK="a\"; touch $CLI/pwn-stack; echo \"" \
        make -C "$NOSTK" --no-print-directory help < /dev/null 2>&1); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -eq 0 ] && [ -z "$(pwned)" ] && printf '%s' "$out" | grep -q "stack: wp"; then
    ok "an exported STACK reaches no shell, and site.yml still names the stack"
else
    bad "an exported STACK reaches no shell, and site.yml still names the stack" "exit $rc: $(pwned) $(printf '%s' "$out" | head -1)"
fi
printf 'STACK := generic\ninclude Makefile.netdust\n' > "$NOSTK/Makefile"
out=$(env PATH="$CLIPATH" STACK=wp make -C "$NOSTK" --no-print-directory help < /dev/null 2>&1 | strip)
printf '%s' "$out" | grep -q "stack: generic" \
    && ok "…and the project Makefile's own STACK := still wins over the environment" \
    || bad "…and the project Makefile's own STACK := still wins over the environment" "$(printf '%s' "$out" | head -1)"

# Inherited from a polluted shell it is dropped with a warning instead, so a
# read-only verb still runs.
out=$(env PATH="$CLIPATH" "env=a\"; touch $CLI/pwn-envpoll; echo \"" "verb=\$(touch $CLI/pwn-verbpoll)" \
        bash -c 'make --no-print-directory help >/dev/null </dev/null \
              && make --no-print-directory status >/dev/null </dev/null \
              && make --no-print-directory gate >/dev/null </dev/null' < /dev/null 2>&1); rc=$?
if [ $rc -eq 0 ] && [ -z "$(pwned)" ]; then
    ok "a hostile env= and verb= in the ENVIRONMENT leave help, status and gate runnable, and neither runs"
else
    bad "a hostile env= and verb= in the ENVIRONMENT leave help, status and gate runnable" "exit $rc: $(pwned) $(printf '%s' "$out" | strip | head -2)"
fi

out=$(M _need-tty verb="promote name=x" | strip)
printf '%s' "$out" | grep -q "make promote name=x needs a terminal" \
    && ok "verb= still carries a space and an '=' through to _need-tty" \
    || bad "verb= still carries a space and an '=' through to _need-tty" "$(printf '%s' "$out" | head -2)"

# The cases below read deployed/staging, and an unfixed core deploys for real
# out of the injections above — so the tag starts from nothing either way.
git push -q --delete origin refs/tags/deployed/staging > /dev/null 2>&1
git tag -d deployed/staging > /dev/null 2>&1

# dryrun= is a boolean: the core writes rsync's own flag, so no make variable
# ever carries another program's argument.
rsyncrun() { : > "$CLI/rsync.log"
    RSOUT=$(env PATH="$CLIPATH" make --no-print-directory _deploy-rsync env=staging "$@" < /dev/null 2>&1); RSRC=$?; }
rsyncarg() { grep -cF -- "[$1]" "$CLI/rsync.log"; }
rsynclines() { wc -l < "$CLI/rsync.log" | tr -d ' '; }
rsyncrun
if [ $RSRC -eq 0 ] && [ "$(rsynclines)" = 1 ] && [ "$(rsyncarg --dry-run)" = 0 ]; then
    ok "_deploy-rsync without dryrun= runs rsync once, without --dry-run"
else
    bad "_deploy-rsync without dryrun= runs rsync once, without --dry-run" "exit $RSRC: $(cat "$CLI/rsync.log")"
fi
rsyncrun dryrun=1
if [ $RSRC -eq 0 ] && [ "$(rsyncarg --dry-run)" = 1 ] && [ "$(rsyncarg 1)" = 0 ]; then
    ok "dryrun=1 hands rsync --dry-run, never the value itself"
else
    bad "dryrun=1 hands rsync --dry-run, never the value itself" "exit $RSRC: $(cat "$CLI/rsync.log")"
fi
rsyncrun dryrun=--dry-run
if [ $RSRC -ne 0 ] && printf '%s' "$RSOUT" | strip | grep -q "Refused dryrun=" && [ ! -s "$CLI/rsync.log" ]; then
    ok "dryrun=--dry-run is refused at parse, naming dryrun=, and rsync never runs"
else
    bad "dryrun=--dry-run is refused at parse, naming dryrun=, and rsync never runs" "exit $RSRC: $(printf '%s' "$RSOUT" | strip | head -2)"
fi
[ "$(grep -c 'dryrun=--dry-run' "$DIST/Makefile.netdust")" = 0 ] \
    && ok "no make variable in the core carries rsync's flag" \
    || bad "no make variable in the core carries rsync's flag" "$(grep -n 'dryrun=--dry-run' "$DIST/Makefile.netdust" | head -2)"

: > "$CLI/rsync.log"
out=$(M deploy-test env=staging); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -eq 0 ] && [ "$(rsyncarg --dry-run)" = 1 ] && [ -z "$(git ls-remote origin 'refs/tags/deployed/*')" ]; then
    ok "make deploy-test env=staging reaches the transport with --dry-run, and writes no ledger"
else
    bad "make deploy-test env=staging reaches the transport with --dry-run, and writes no ledger" "exit $rc: $(printf '%s' "$out" | tail -2)"
fi

echo
echo "── the deploy tag fails closed ──"
# ship reads deployed/staging from origin to prove a tree was deployed, so a
# tag that does not reach origin is a failed deploy, not a warning.
HOOK="$WORK/origin.git/hooks/pre-receive"
NOTAG='#!/bin/sh
while read -r o n r; do case "$r" in refs/tags/deployed/*) exit 1;; esac; done'
printf '%s\n' "$NOTAG" > "$HOOK"; chmod +x "$HOOK"
out=$(M deploy env=staging); rc=$?; rm -f "$HOOK"; out=$(printf '%s' "$out" | strip)
if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "deploy tag not pushed — the ledger on origin is stale"; then
    ok "origin refusing the deploy tag fails the deploy, naming the stale ledger"
else
    bad "origin refusing the deploy tag fails the deploy, naming the stale ledger" "exit $rc: $(printf '%s' "$out" | tail -2)"
fi
out=$(M deploy env=staging); rc=$?
if [ $rc -eq 0 ] && [ "$(git ls-remote origin refs/tags/deployed/staging | cut -f1)" = "$(git rev-parse HEAD)" ]; then
    ok "…and with origin taking it, deploy stamps deployed/staging at HEAD"
else
    bad "…and with origin taking it, deploy stamps deployed/staging at HEAD" "exit $rc: $(printf '%s' "$out" | strip | tail -2)"
fi

# A rollback that leaves the tag on the rolled-back-FROM commit lets ship pass
# against a tree the environment no longer runs.
echo rb > rb.txt && git add rb.txt && git -c user.email=t@t -c user.name=T commit -qm rb
git push -q origin staging 2>/dev/null
PREV=$(git rev-parse HEAD~1)
printf '%s %s staging T\n%s %s staging T\n' 2026-01-01T00:00:00 "$PREV" 2026-01-02T00:00:00 "$(git rev-parse HEAD)" > "$CLI/ledger"
M deploy env=staging > /dev/null 2>&1
WTN=$(git worktree list | wc -l | tr -d ' ')
printf '%s\n' "$NOTAG" > "$HOOK"; chmod +x "$HOOK"
out=$(env PATH="$CLIPATH" script -qec "make --no-print-directory rollback env=staging" /dev/null <<< yes 2>&1); rc=$?
rm -f "$HOOK"; out=$(printf '%s' "$out" | strip)
if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "deploy tag not pushed" \
   && [ "$(git worktree list | wc -l | tr -d ' ')" = "$WTN" ]; then
    ok "a rollback whose tag origin refuses fails, and leaves no worktree behind"
else
    bad "a rollback whose tag origin refuses fails, and leaves no worktree behind" "exit $rc: $(printf '%s' "$out" | tail -2)"
fi
out=$(env PATH="$CLIPATH" script -qec "make --no-print-directory rollback env=staging" /dev/null <<< yes 2>&1); rc=$?
if [ $rc -eq 0 ] && [ "$(git ls-remote origin refs/tags/deployed/staging | cut -f1)" = "$PREV" ]; then
    ok "make rollback env=staging moves deployed/staging on origin to the commit it rolled back to"
else
    bad "make rollback env=staging moves deployed/staging on origin to the commit it rolled back to" \
        "exit $rc: tag=$(git ls-remote origin refs/tags/deployed/staging | cut -f1) want=$PREV"
fi

# A rollback whose worktree cannot be made has rsynced nothing: it may not write
# the ledger, and may not stamp the checkout's own HEAD as what the server runs.
mkdir -p "$CLI/nogit"; GIT=$(command -v git)
printf '#!/bin/sh\ncase "$*" in *"worktree add"*) exit 1;; esac\nexec %s "$@"\n' "$GIT" > "$CLI/nogit/git"
chmod +x "$CLI/nogit/git"; : > "$CLI/ssh.log"
TAG=$(git ls-remote origin refs/tags/deployed/staging)
out=$(env PATH="$CLI/nogit:$CLIPATH" script -qec "make --no-print-directory rollback env=staging" /dev/null <<< yes 2>&1); rc=$?
if [ $rc -ne 0 ] && ! grep -q 'cat >' "$CLI/ssh.log" && [ "$(git ls-remote origin refs/tags/deployed/staging)" = "$TAG" ]; then
    ok "a rollback that cannot make its worktree fails, writes no ledger and leaves the tag"
else
    bad "a rollback that cannot make its worktree fails, writes no ledger and leaves the tag" \
        "exit $rc: ledger writes=$(grep -c 'cat >' "$CLI/ssh.log") tag=$(git ls-remote origin refs/tags/deployed/staging | cut -f1)"
fi

# Over git-push the server runs a git checkout and there is no payload to
# rsync: the loop moved nothing, then the ledger and the tag said it had
# (daan, netdust, stride — all git-push, all payload: []).
sed -i 's/^  method: rsync/  method: git-push/' site.yml
: > "$CLI/ssh.log"; : > "$CLI/rsync.log"; TAG=$(git ls-remote origin refs/tags/deployed/staging)
out=$(env PATH="$CLIPATH" script -qec "make --no-print-directory rollback env=staging" /dev/null <<< yes 2>&1); rc=$?
out=$(printf '%s' "$out" | strip); git checkout -q -- site.yml
if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "not supported over git-push" \
   && ! printf '%s' "$out" | grep -q "rolled back to" && [ ! -s "$CLI/ssh.log" ] && [ ! -s "$CLI/rsync.log" ] \
   && [ "$(git ls-remote origin refs/tags/deployed/staging)" = "$TAG" ]; then
    ok "rollback over git-push refuses by name: no server contact, no ledger, the tag unmoved"
else
    bad "rollback over git-push refuses by name: no server contact, no ledger, the tag unmoved" \
        "exit $rc: ssh=$(wc -l < "$CLI/ssh.log") tag=$(git ls-remote origin refs/tags/deployed/staging | cut -f1) — $(printf '%s' "$out" | tail -1)"
fi

echo
echo "── the rebuild: unpromote tells the truth, and local staging follows ──"
SY="$WORK/sync"; mkdir -p "$SY"; cd "$SY" || exit 1
git init -q --bare origin.git && git clone -q origin.git base 2>/dev/null
cd "$SY/base" || exit 1
git -C "$WT/base" archive main | tar -x
git add -A && git -c user.email=t@t -c user.name=T commit -qm init >/dev/null && git branch -M main
git push -q -u origin main 2>/dev/null; git push -q origin main:staging 2>/dev/null
git checkout -q -b staging origin/staging
feat() { git checkout -q -b "feature/$1" "$2" && echo "$1" > "web/$1.txt" && git add -A \
    && git -c user.email=t@t -c user.name=T commit -qm "$1" >/dev/null && git push -q origin "feature/$1" 2>/dev/null
    git checkout -q staging; }
feat a origin/main; feat b origin/main; feat b2 feature/a
PTY() { env PATH="$CLIPATH" timeout 60 script -qec "make --no-print-directory $1" /dev/null <<< yes 2>&1; }

# feature/b2 was branched from feature/a, so a's commits ride in on b2's pin.
PTY "promote name=a" > /dev/null; PTY "promote name=b2" > /dev/null

# "Which branches are promoted and which are not?" — a feature branches from
# production, so nothing on it says. status reads staging's own promote: merges.
git push -q origin feature/a:refs/heads/feature/c 2>/dev/null
out=$(M status | strip)
if printf '%s' "$out" | grep -qE '^  promoted: +a, b2$' \
   && printf '%s' "$out" | grep -qE '^  via another: +c$' \
   && printf '%s' "$out" | grep -qE '^  not promoted: +b \(1 commit' \
   && ! printf '%s' "$out" | grep -qE '(empty|h)\b.*commit'; then
    ok "status lists what is promoted, what rides in through another, and what is not on staging"
else
    bad "status lists what is promoted, what rides in through another, and what is not on staging" "$(printf '%s' "$out" | sed -n '/STAGING/,/^$/p')"
fi
git push -q origin --delete feature/c 2>/dev/null
REMOTES=$(git ls-remote origin)
out=$(PTY "unpromote name=a"); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "feature/a is still on staging through another promoted feature" \
   && [ "$(git ls-remote origin)" = "$REMOTES" ]; then
    ok "unpromote refuses a feature another promoted feature still carries, and pushes nothing"
else
    bad "unpromote refuses a feature another promoted feature still carries, and pushes nothing" "exit $rc: $(printf '%s' "$out" | tail -2)"
fi

# The rebuild force-pushes commits made in a throwaway worktree. No raw git runs
# between these verbs: the advertised path has to work as advertised.
M deploy env=staging > /dev/null; PTY "promote name=b" > /dev/null
out=$(M deploy env=staging); rc=$?
if [ $rc -eq 0 ] && [ "$(git ls-remote origin refs/tags/deployed/staging | cut -f1)" = "$(git ls-remote origin refs/heads/staging | cut -f1)" ]; then
    ok "promote, deploy, promote, deploy: the second deploy ships what origin/staging is"
else
    bad "promote, deploy, promote, deploy: the second deploy ships what origin/staging is" "exit $rc: $(printf '%s' "$out" | strip | tail -2)"
fi
git checkout -q feature/b; PTY "unpromote name=b" > /dev/null
[ "$(git rev-parse staging)" = "$(git ls-remote origin refs/heads/staging | cut -f1)" ] \
    && ok "…and from a feature branch, local staging ends on origin/staging" \
    || bad "…and from a feature branch, local staging ends on origin/staging" "local $(git rev-parse --short staging)"
# A dirty staging checkout that the reset would clobber: the push already landed.
git checkout -q staging; echo mine > web/b.txt
out=$(PTY "promote name=b"); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -eq 0 ] && printf '%s' "$out" | grep -q "git reset --keep origin/staging" && [ "$(cat web/b.txt)" = mine ]; then
    ok "…and a checkout it cannot move is told how, without failing a rebuild that landed"
else
    bad "…and a checkout it cannot move is told how, without failing a rebuild that landed" "exit $rc: $(printf '%s' "$out" | tail -2)"
fi
rm -f web/b.txt; git reset -q --keep origin/staging

# Two ways a promote adds nothing: no commits over production, or a tip that a
# promoted feature sorting before it already carries ("Already up to date").
git push -q origin origin/main:refs/heads/feature/empty feature/a:refs/heads/feature/z 2>/dev/null
REMOTES=$(git ls-remote origin)
for n in empty z; do
    out=$(PTY "promote name=$n"); rc=$?; out=$(printf '%s' "$out" | strip)
    if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "feature/$n added nothing to staging" \
       && ! printf '%s' "$out" | grep -q "✅" && [ "$(git ls-remote origin)" = "$REMOTES" ]; then
        ok "promote name=$n adds nothing: it says so, fails, and pushes nothing"
    else
        bad "promote name=$n adds nothing: it says so, fails, and pushes nothing" "exit $rc: $(printf '%s' "$out" | tail -2)"
    fi
done

# Driven as a target: ship runs _ship-path before the gate and the confirmation.
git checkout -q -b hotfix/h origin/main
for s in "fix one" "fix two"; do git -c user.email=t@t -c user.name=T commit -q --allow-empty -m "$s"; done
out=$(M _ship-path); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -eq 0 ] && printf '%s' "$out" | grep -q "fix one" && printf '%s' "$out" | grep -q "fix two"; then
    ok "a hotfix ship path lists the commits it carries over production"
else
    bad "a hotfix ship path lists the commits it carries over production" "exit $rc: $(printf '%s' "$out" | tail -2)"
fi

git checkout -q staging; : > "$CLI/ssh.log"
out=$(M rollback env=staging); rc=$?; out=$(printf '%s' "$out" | strip)
if [ $rc -ne 0 ] && printf '%s' "$out" | grep -q "needs a terminal" && [ ! -s "$CLI/ssh.log" ]; then
    ok "rollback without a terminal refuses before any ssh"
else
    bad "rollback without a terminal refuses before any ssh" "exit $rc: ssh calls=$(wc -l < "$CLI/ssh.log" | tr -d ' ')"
fi
cd "$P" || exit 1

echo
echo "── pull and refresh: the local tree, and what git owns in it ──"
# daan, make pull env=staging (2026-09-24): git-push Bedrock, content_dir web/app,
# no deploy.payload. The local side prefixed the webroot to a path that is
# relative to the environment (the repo root over git-push) — web/web/app — and
# the empty payload left the themes mirror running --delete with nothing
# excluded, over the project's own tracked theme.
PL="$WORK/pull"; mkdir -p "$PL/scripts" "$PL/web/app/plugins/own" "$PL/web/app/themes/mine" "$PL/web/app/uploads"; cd "$PL"
cat > site.yml <<'PLYML'
site: {name: pull, domain: pull.invalid, risk: low}
structure: {type: bedrock, stack: wp, webroot: web, wpcli_path: web/wp}
environments:
  staging:    {url: "https://staging.pull.invalid", path: /srv/staging, branch: staging, role: review, confirm: false}
  production: {url: "https://pull.invalid", path: /srv/prod, branch: main, role: live, confirm: true}
deploy:
  method: git-push
  ssh_host: nobody@pull.invalid
  state_dir: /srv/.state
  wp_path: web/wp
  content_dir: web/app
local: {ddev_project: pull, url: "https://pull.ddev.site"}
commands: {gate: "true"}
PLYML
cp "$DIST/scripts/devops-version" scripts/ && chmod +x scripts/devops-version
NETDUST_DEVOPS_DIST="$DIST" scripts/devops-version --update >/dev/null 2>&1
printf 'STACK := wp\ninclude Makefile.netdust\n' > Makefile
echo '<?php' > web/app/plugins/own/own.php; echo '/* mine */' > web/app/themes/mine/style.css
touch web/app/uploads/.gitkeep
mkdir -p web/app/themes/café && echo '/* é */' > web/app/themes/café/style.css
git init -q . && git add -A && git -c user.email=t@t -c user.name=T commit -qm init
# the target of a pull: rsync runs on the stub, so a missing parent is a wrong path
rsynced() { grep -F -- "[$1]" "$CLI/rsync.log" | grep -F -- "[$2]"; }

: > "$CLI/rsync.log"; out=$(M _pull-plugins env=staging | strip)
if rsynced "nobody@pull.invalid:/srv/staging/web/app/plugins/" "web/app/plugins/" >/dev/null \
   && rsynced "nobody@pull.invalid:/srv/staging/web/app/themes/" "web/app/themes/" >/dev/null; then
    ok "git-push pull mirrors env/web/app into web/app — local and remote agree"
else
    bad "git-push pull mirrors env/web/app into web/app — local and remote agree" "$(cat "$CLI/rsync.log")"
fi
if rsynced "web/app/themes/" "--exclude=/mine" >/dev/null && rsynced "web/app/plugins/" "--exclude=/own" >/dev/null \
   && ! printf '%s' "$out" | grep -q "no such key"; then
    ok "…and with no deploy.payload, the tracked theme and plugin are excluded from --delete"
else
    bad "…and with no deploy.payload, the tracked theme and plugin are excluded from --delete" "$(cat "$CLI/rsync.log") $out"
fi

: > "$CLI/rsync.log"; M _pull-uploads env=staging > /dev/null
rsynced "web/app/uploads/" "--exclude=/.gitkeep" >/dev/null \
    && ok "pull uploads lands in web/app/uploads and keeps what git tracks there" \
    || bad "pull uploads lands in web/app/uploads and keeps what git tracks there" "$(cat "$CLI/rsync.log")"

: > "$CLI/ssh.log"; M _refresh-plugins env=staging > /dev/null
grep "themes/" "$CLI/ssh.log" | grep -qF -- "--exclude=/mine" \
    && ok "refresh over git-push keeps the tracked theme out of the server-side --delete" \
    || bad "refresh over git-push keeps the tracked theme out of the server-side --delete" "$(cat "$CLI/ssh.log")"

# rsync: the environment directory IS the web root, so content_dir is read under it.
sed -i 's/^  method: git-push/  method: rsync/; s/^  content_dir: web\/app/  content_dir: app/' site.yml
: > "$CLI/rsync.log"; M _pull-plugins env=staging > /dev/null
rsynced "nobody@pull.invalid:/srv/staging/app/plugins/" "web/app/plugins/" >/dev/null \
    && ok "rsync pull mirrors env/app into web/app, as before" \
    || bad "rsync pull mirrors env/app into web/app, as before" "$(cat "$CLI/rsync.log")"

# git quotes a non-ASCII path ("web/app/themes/caf\303\251/…") unless told not to,
# and a quoted path matched no prefix: the tracked theme went unprotected.
rsynced "web/app/themes/" "--exclude=/café" >/dev/null \
    && ok "a tracked theme with a non-ASCII name is excluded too" \
    || bad "a tracked theme with a non-ASCII name is excluded too" "$(grep themes "$CLI/rsync.log")"

# webroot "." over rsync: ./web/app is what git prints as web/app.
sed -i 's/webroot: web,/webroot: ".",/; s/^  content_dir: app/  content_dir: web\/app/' site.yml
: > "$CLI/rsync.log"; M _pull-plugins env=staging > /dev/null
rsynced "web/app/themes/" "--exclude=/mine" >/dev/null \
    && ok "with webroot . the tracked theme is still excluded" \
    || bad "with webroot . the tracked theme is still excluded" "$(grep themes "$CLI/rsync.log")"
cd "$P" || exit 1

echo
printf '%s passed, %s failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
