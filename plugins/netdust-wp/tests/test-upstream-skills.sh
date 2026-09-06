#!/usr/bin/env bash
# tests/test-upstream-skills.sh — bin/wp-upstream-skills.sh against a local fixture upstream.
# No network: a bare repo stands in for WordPress/agent-skills, a stub npx on PATH copies dirs.
set -u
cd "$(dirname "$0")" || exit 1
BIN=$(cd .. && pwd)/bin/wp-upstream-skills.sh
fail=0
ok()  { printf 'pass\t%s\n' "$1"; }
bad() { printf 'FAIL\t%s\n' "$1"; fail=1; }

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" XDG_CACHE_HOME="$TMP/cache"
mkdir -p "$HOME" "$TMP/bin"
CLONE="$XDG_CACHE_HOME/netdust/wp-upstream-skills"
SKILLS="wp-plugin-development wp-rest-api wp-wpcli-and-ops wp-phpstan"

git init -q -b trunk "$TMP/src"
for s in $SKILLS; do mkdir -p "$TMP/src/skills/$s"; echo "# $s" > "$TMP/src/skills/$s/SKILL.md"; done
git -C "$TMP/src" -c user.email=t@test -c user.name=t add -A
git -C "$TMP/src" -c user.email=t@test -c user.name=t commit -qm fixture
git clone -q --bare "$TMP/src" "$TMP/upstream.git"
PIN=$(git -C "$TMP/src" rev-parse HEAD)
export UPSTREAM="$TMP/upstream.git" PIN

cat > "$TMP/bin/npx" <<'SH'
#!/usr/bin/env bash
echo "$*" >> "$NPX_LOG"
[ "$1" = "-y" ] && shift
[ "$1 $2" = "skills add" ] || { echo "stub npx: unexpected $*" >&2; exit 9; }
src=$3; shift 3
names=()
while [ $# -gt 0 ]; do
  case $1 in
    -s) shift; while [ $# -gt 0 ] && [[ $1 != -* ]]; do names+=("$1"); shift; done ;;
    *) shift ;;
  esac
done
mkdir -p "$HOME/.claude/skills"
for n in "${names[@]}"; do rm -rf "${HOME:?}/.claude/skills/$n"; cp -r "$src/skills/$n" "$HOME/.claude/skills/$n"; done
SH
chmod +x "$TMP/bin/npx"
export PATH="$TMP/bin:$PATH" NPX_LOG="$TMP/npx.log"
touch "$NPX_LOG"

# (d) an unpinned run refuses before touching anything
out=$(PIN='' bash "$BIN" 2>&1); rc=$?
[ $rc -eq 2 ] && ok "PIN= exits 2" || bad "PIN= exit $rc (want 2): $out"
grep -q "refusing: no pin" <<<"$out" && ok "PIN= says refusing: no pin" || bad "PIN= output: $out"
[ ! -e "$CLONE" ] && ok "PIN= touched no clone" || bad "PIN= created $CLONE"

# a ref name is not a pin: PIN=trunk would fetch whatever trunk resolves to
out=$(PIN=trunk bash "$BIN" 2>&1); rc=$?
[ $rc -eq 2 ] && ok "PIN=trunk exits 2" || bad "PIN=trunk exit $rc (want 2): $out"
grep -q "refusing: no pin" <<<"$out" && ok "PIN=trunk says refusing: no pin" || bad "PIN=trunk output: $out"
[ ! -e "$CLONE" ] && ok "PIN=trunk touched no clone" || bad "PIN=trunk created $CLONE"

# (e) --dry-run prints the commands and touches nothing
out=$(bash "$BIN" --dry-run 2>&1); rc=$?
[ $rc -eq 0 ] && ok "--dry-run exits 0" || bad "--dry-run exit $rc: $out"
grep -q "git.* fetch .*$PIN" <<<"$out" && ok "--dry-run prints the fetch" || bad "--dry-run has no fetch line: $out"
grep -q "git.* checkout .*$PIN" <<<"$out" && ok "--dry-run prints the checkout" || bad "--dry-run has no checkout line: $out"
grep -q "skills add .* --copy" <<<"$out" && ok "--dry-run prints the skills add" || bad "--dry-run has no add line: $out"
[ ! -e "$CLONE" ] && [ ! -e "$HOME/.claude" ] && ok "--dry-run touched nothing" || bad "--dry-run created files"
[ ! -s "$NPX_LOG" ] && ok "--dry-run did not call npx" || bad "--dry-run called npx: $(cat "$NPX_LOG")"

# (a) install: clone at the pin, four dirs land
out=$(bash "$BIN" 2>&1); rc=$?
[ $rc -eq 0 ] && ok "install exits 0" || bad "install exit $rc: $out"
[ "$(git -C "$CLONE" rev-parse HEAD 2>/dev/null)" = "$PIN" ] && ok "clone checked out at PIN" || bad "clone not at PIN"
for s in $SKILLS; do
  [ -f "$HOME/.claude/skills/$s/SKILL.md" ] && ok "installed $s" || bad "missing $HOME/.claude/skills/$s/SKILL.md"
done
grep -q -- "-a claude-code -g -y --copy" "$NPX_LOG" && ok "npx add is global, copied, non-interactive" || bad "npx args: $(cat "$NPX_LOG")"
grep -q -- "skills add $CLONE " "$NPX_LOG" && ok "npx adds from the local clone" || bad "npx source: $(cat "$NPX_LOG")"

# a re-run reuses the clone and stays at the pin
out=$(bash "$BIN" 2>&1); rc=$?
[ $rc -eq 0 ] && [ "$(git -C "$CLONE" rev-parse HEAD)" = "$PIN" ] && ok "re-run exits 0 at PIN" || bad "re-run exit $rc: $out"

# a changed pin re-fetches: the clone moves and the new content lands
echo "# wp-phpstan v2" > "$TMP/src/skills/wp-phpstan/SKILL.md"
git -C "$TMP/src" -c user.email=t@test -c user.name=t commit -qam bump
git -C "$TMP/src" push -q "$TMP/upstream.git" trunk
PIN2=$(git -C "$TMP/src" rev-parse HEAD)
out=$(PIN="$PIN2" bash "$BIN" 2>&1); rc=$?
[ $rc -eq 0 ] && ok "changed pin: install exits 0" || bad "changed pin exit $rc: $out"
[ "$(git -C "$CLONE" rev-parse HEAD)" = "$PIN2" ] && ok "changed pin: clone moved to the new sha" || bad "clone still at $(git -C "$CLONE" rev-parse HEAD)"
[ "$(cat "$HOME/.claude/skills/wp-phpstan/SKILL.md")" = "# wp-phpstan v2" ] && ok "changed pin: new content landed" || bad "wp-phpstan content: $(cat "$HOME/.claude/skills/wp-phpstan/SKILL.md")"
out=$(PIN="$PIN2" bash "$BIN" --check 2>&1); rc=$?
[ $rc -eq 0 ] && [ "$(grep -c "^present" <<<"$out")" -eq 4 ] && ok "changed pin: --check four present" || bad "changed pin --check exit $rc: $out"
PIN=$(git -C "$TMP/src" rev-parse HEAD~1); export PIN

# (b) --check after install lists four, exit 0
out=$(bash "$BIN" --check 2>&1); rc=$?
[ $rc -eq 0 ] && ok "--check exits 0 when all present" || bad "--check exit $rc: $out"
grep -q "$PIN" <<<"$out" && ok "--check prints the pin" || bad "--check output lacks pin: $out"
[ "$(grep -c "^present" <<<"$out")" -eq 4 ] && ok "--check lists four present" || bad "--check output: $out"

# (c) one dir removed → --check exit 1 naming it
rm -rf "$HOME/.claude/skills/wp-rest-api"
out=$(bash "$BIN" --check 2>&1); rc=$?
[ $rc -eq 1 ] && ok "--check exits 1 when one is missing" || bad "--check exit $rc (want 1): $out"
grep -q "^missing.*wp-rest-api" <<<"$out" && ok "--check names wp-rest-api missing" || bad "--check output: $out"

# an unknown flag is refused
bash "$BIN" --bogus >/dev/null 2>&1; rc=$?
[ $rc -ne 0 ] && ok "unknown flag is refused" || bad "--bogus exited 0"

[ $fail -eq 0 ] && echo "test-upstream-skills: all passed" || echo "test-upstream-skills: FAILURES above"
exit $fail
