#!/usr/bin/env bash
# bin/wp-upstream-skills.sh — install the pinned WordPress/agent-skills set for Claude Code.
# `npx skills add` cannot pin a ref, so: shallow-fetch PIN into a local clone, add from that path.
set -euo pipefail

UPSTREAM="${UPSTREAM:-https://github.com/WordPress/agent-skills.git}"
PIN="${PIN-d87ee6916e740c7960b6959220c0481a41b320c7}"  # trunk, 2026-09-06
SKILLS="wp-plugin-development wp-rest-api wp-wpcli-and-ops wp-phpstan"
CLONE="${XDG_CACHE_HOME:-$HOME/.cache}/netdust/wp-upstream-skills"
NPX="${NPX:-npx}"
DRY=false

run() { if $DRY; then echo "+ $*"; else "$@"; fi; }

install() {
  if [ ! -d "$CLONE/.git" ]; then
    run git init -q "$CLONE"
    run git -C "$CLONE" remote add origin "$UPSTREAM"
  fi
  if [ "$(git -C "$CLONE" rev-parse HEAD 2>/dev/null || true)" != "$PIN" ]; then
    run git -C "$CLONE" fetch -q --depth 1 origin "$PIN"
    run git -C "$CLONE" checkout -q "$PIN"
  fi
  run "$NPX" -y skills add "$CLONE" -s $SKILLS -a claude-code -g -y --copy
}

check() {
  local rc=0 s
  echo "pin: $PIN"
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
