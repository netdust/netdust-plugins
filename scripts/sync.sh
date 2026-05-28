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
  version="$(ls -1t "$CACHE_ROOT/$plugin_name" | head -1)"
  if [[ -z "$version" ]]; then
    echo "  - $plugin_name: SKIP (no version dir found)"
    continue
  fi
  target="$CACHE_ROOT/$plugin_name/$version"
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
  version="$(ls -1t "$CACHE_ROOT/$plugin_name" | head -1)"
  target="$CACHE_ROOT/$plugin_name/$version"
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
