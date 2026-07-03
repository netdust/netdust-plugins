#!/usr/bin/env bash
# Sync netdust-plugins source-of-truth into the two Claude Code caches.
#
# WHY: Claude Code maintains two separate caches for an installed plugin:
#   1. ~/.claude/plugins/marketplaces/netdust-plugins/   (git clone of the marketplace repo)
#   2. ~/.claude/plugins/cache/netdust-plugins/<plugin>/<version>/   (extracted per-plugin install)
#
# `claude plugin marketplace update netdust-plugins` refreshes #1.
# `claude plugin update <name>@netdust-plugins` refreshes #2 — but only when
# the plugin's version number has bumped. During heavy iteration on the
# harness, we ship many commits at the same version (0.1.0), so the install
# cache silently stays stale.
#
# This script syncs both caches from the working tree in one shot.
# Idempotent; safe to run any time after a commit.
#
# Usage:
#   ./scripts/sync.sh
#
# Run AFTER `git push`. Pushes are what trigger the marketplace clone to
# fetch the new commits; without a push, this script will just refresh
# both caches to the latest pushed state, which may be older than your
# local working tree.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MARKETPLACE_NAME="netdust-plugins"
CACHE_ROOT="$HOME/.claude/plugins/cache/$MARKETPLACE_NAME"
INSTALLED_JSON="$HOME/.claude/plugins/installed_plugins.json"

# Authoritative map: plugin<TAB>installPath from Claude Code's own registry
# (fix 3, 2026-07-03 — `ls -1t` picked netdust-agent 0.2.1 over the installed
# 0.3.0 on a 4 ms mtime difference), same ACTIVE_MAP pattern as
# session-start.sh. Parsed ONCE here instead of spawning python3 per plugin
# per loop (sync loop + verify loop). Empty on any error → per-plugin
# mtime fallback in resolve_installed_dir below.
ACTIVE_MAP=""
if [[ -f "$INSTALLED_JSON" ]]; then
  ACTIVE_MAP=$(python3 - "$INSTALLED_JSON" <<'PY' 2>/dev/null || true
import json, sys
try:
    data = json.load(open(sys.argv[1]))
    lines = []
    for key, entries in data.get("plugins", {}).items():
        name = key.split("@", 1)[0]
        # registry lists one entry per key in practice; entries[0] is taken as active.
        if isinstance(entries, list) and entries:
            p = entries[0].get("installPath")
            if p:
                lines.append(f"{name}\t{p}")
    if lines:
        print("\n".join(lines))
except Exception:
    sys.exit(0)
PY
)
fi

# resolve_installed_dir <plugin_name>
# Echoes the plugin's ACTIVE cache dir. Pure bash/awk lookup against
# ACTIVE_MAP (parsed once above) — no more per-call python3 spawn. Falls
# back to newest-mtime (with a -d check, parity with the registry branch)
# when the registry misses the plugin. Echoes nothing if unresolvable.
# Must never return non-zero — set -euo pipefail is in effect and the
# empty/unresolved case is a normal, expected outcome for callers.
resolve_installed_dir() {
  local plugin_name="$1" active=""
  active=$(printf '%s\n' "$ACTIVE_MAP" | awk -F'\t' -v p="$plugin_name" '$1 == p { print $2; exit }')
  if [[ -n "$active" && -d "$active" ]]; then
    printf '%s\n' "$active"
    return 0
  fi
  local latest
  latest="$(ls -1t "$CACHE_ROOT/$plugin_name" 2>/dev/null | head -1)"
  if [[ -n "$latest" && -d "$CACHE_ROOT/$plugin_name/$latest" ]]; then
    printf '%s\n' "$CACHE_ROOT/$plugin_name/$latest"
  fi
  return 0
}

if [[ ! -d "$REPO_ROOT/plugins" ]]; then
  echo "ERROR: $REPO_ROOT does not look like the netdust-plugins repo (no plugins/ dir)." >&2
  exit 1
fi

echo "[1/3] Refreshing marketplace clone from GitHub..."
claude plugin marketplace update "$MARKETPLACE_NAME" 2>&1 | tail -2

echo ""
echo "[2/3] Syncing install caches from working tree..."
synced=0
for plugin_dir in "$REPO_ROOT/plugins"/*/; do
  plugin_name="$(basename "$plugin_dir")"
  # Find the installed version dir (assumes one version per plugin; picks the most recent if multiple).
  if [[ ! -d "$CACHE_ROOT/$plugin_name" ]]; then
    echo "  - $plugin_name: SKIP (not installed)"
    continue
  fi
  target="$(resolve_installed_dir "$plugin_name")"
  if [[ -z "$target" ]]; then
    echo "  - $plugin_name: SKIP (no installed version dir resolved)"
    continue
  fi
  version="$(basename "$target")"
  # Mirror the working tree into the cache. Use rsync if available for cleaner deletion of removed files.
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --exclude='.git' "$plugin_dir" "$target/"
  else
    rm -rf "$target"/*
    cp -a "$plugin_dir"/. "$target/"
  fi
  echo "  - $plugin_name@$version: synced"
  synced=$((synced + 1))
done

echo ""
echo "[3/3] Verifying sync..."
fail=0
for plugin_dir in "$REPO_ROOT/plugins"/*/; do
  plugin_name="$(basename "$plugin_dir")"
  [[ -d "$CACHE_ROOT/$plugin_name" ]] || continue
  target="$(resolve_installed_dir "$plugin_name")"
  [[ -n "$target" ]] || continue
  # Compare top-level skill SKILL.md count + command count as a smoke check.
  src_skills="$(find "$plugin_dir/skills" -maxdepth 2 -name 'SKILL.md' 2>/dev/null | wc -l)"
  dst_skills="$(find "$target/skills" -maxdepth 2 -name 'SKILL.md' 2>/dev/null | wc -l)"
  if [[ "$src_skills" != "$dst_skills" ]]; then
    echo "  ✗ $plugin_name: SKILL.md count mismatch (source=$src_skills, cache=$dst_skills)"
    fail=1
  fi
done

if [[ "$fail" -ne 0 ]]; then
  echo ""
  echo "Sync completed with verification warnings. Inspect manually."
  exit 1
fi

echo "  ✓ all plugins verified"
echo ""
echo "Done. $synced plugin(s) synced. Restart Claude Code to pick up SKILL/command changes in new sessions."
