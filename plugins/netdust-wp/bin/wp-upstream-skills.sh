#!/usr/bin/env bash
# bin/wp-upstream-skills.sh — install the pinned WordPress/agent-skills set for Claude Code.
# `npx skills add` cannot pin a ref, so: shallow-fetch PIN into a local clone, add from that path.
set -euo pipefail

UPSTREAM="${UPSTREAM:-https://github.com/WordPress/agent-skills.git}"
PIN="${PIN-eff3785fc28c4380d172094518c66a6a997c95d4}"  # trunk, 2026-10-28
SKILLS_CLI_VERSION=1.7.4  # npm view skills version, 2026-10-28
SKILLS="wp-plugin-development wp-rest-api wp-wpcli-and-ops wp-phpstan wp-abilities-api wp-abilities-audit wp-abilities-verify"
CLONE="${XDG_CACHE_HOME:-$HOME/.cache}/netdust/wp-upstream-skills"
DRY=false

run() { if $DRY; then echo "+ $*"; else "$@"; fi; }

install() {
  local s
  if [ ! -d "$CLONE/.git" ]; then
    run git init -q "$CLONE"
    run git -C "$CLONE" remote add origin "$UPSTREAM"
  fi
  if [ "$(git -C "$CLONE" rev-parse HEAD 2>/dev/null || true)" != "$PIN" ]; then
    run git -C "$CLONE" fetch -q --depth 1 origin "$PIN"
    run git -C "$CLONE" checkout -q "$PIN"
  fi
  if ! $DRY; then
    for s in $SKILLS; do
      [ -f "$CLONE/skills/$s/SKILL.md" ] || { echo "missing at pin: $s" >&2; exit 1; }
    done
  fi
  run npx -y skills@"$SKILLS_CLI_VERSION" add "$CLONE" -s $SKILLS -a claude-code -g -y --copy
}

check() {
  local rc=0 s
  echo "pin: $PIN"
  echo "skills-cli: $SKILLS_CLI_VERSION"
  for s in $SKILLS; do
    if [ -f "$HOME/.claude/skills/$s/SKILL.md" ]; then echo "present: $s"; else echo "missing: $s"; rc=1; fi
  done
  return $rc
}

[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo "refusing: no pin" >&2; exit 2; }
case "${1:-}" in
  '') install ;;
  --dry-run) DRY=true; install ;;
  --check) check ;;
  *) echo "usage: $0 [--check|--dry-run]" >&2; exit 64 ;;
esac
