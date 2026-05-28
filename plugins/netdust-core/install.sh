#!/usr/bin/env bash
# install.sh — netdust-core, plugin-marketplace mode
#
# Registers netdust-core in Claude Code's local marketplace + enables the plugin.
# Skills/commands/agents/hooks/MCP load DIRECTLY from this dir via ${CLAUDE_PLUGIN_ROOT}.
# No symlinks. No copies. Edit in place — picked up on next session.
#
# Idempotent. Safe to re-run after harness updates.

set -euo pipefail

PLUGIN_DIR="$HOME/.claude/plugins/netdust-core"
MARKETPLACE_DIR="$HOME/.claude/plugins/marketplaces/netdust-local"
LOGS_DIR="$HOME/.claude/logs"
KM="$HOME/.claude/plugins/known_marketplaces.json"
IP="$HOME/.claude/plugins/installed_plugins.json"
SETTINGS="$HOME/.claude/settings.json"
DASHBOARD_MEMORY="$HOME/Sites/netdust-wp-manager/memory/projects"

if [[ ! -d "$PLUGIN_DIR" ]]; then
  echo "✗ $PLUGIN_DIR does not exist. Clone the harness first." >&2
  exit 1
fi

CHANGES=()

# ── 1. Local marketplace manifest (shared with netdust-wp etc.) ─────────────
mkdir -p "$MARKETPLACE_DIR/.claude-plugin"
MFEST="$MARKETPLACE_DIR/.claude-plugin/marketplace.json"

# Idempotent merge — add/update netdust-core entry without touching siblings.
python3 - "$MFEST" "$PLUGIN_DIR" <<'PY'
import json, sys
from pathlib import Path

mfest, plugin_dir = Path(sys.argv[1]), sys.argv[2]
existing = {}
if mfest.exists():
    try:
        existing = json.loads(mfest.read_text())
    except json.JSONDecodeError:
        existing = {}

base = {
    "name": "netdust-local",
    "owner": {"name": "Stefan Vermeulen", "email": "stefan@netdust.be"},
    "metadata": {"description": "Local marketplace for Netdust harness plugins", "version": "1.0.0"},
    "plugins": [],
}
existing = {**base, **existing}
existing.setdefault("plugins", [])

# Replace or append netdust-core entry
new_entry = {
    "name": "netdust-core",
    "source": {"source": "directory", "path": plugin_dir},
    "description": "Netdust harness core — memory, hooks, cross-stack skills, ploi MCP. Stack-agnostic.",
    "version": "0.1.0",
    "strict": False,
}
plugins = [p for p in existing["plugins"] if p.get("name") != "netdust-core"]
plugins.append(new_entry)
existing["plugins"] = plugins

mfest.write_text(json.dumps(existing, indent=2) + "\n")
print(f"  ✓ {mfest}: netdust-core entry written")
PY
CHANGES+=("updated marketplace manifest $MFEST")

# ── 2. Register marketplace + install + enable plugin ───────────────────────
python3 - "$KM" "$IP" "$SETTINGS" "$MARKETPLACE_DIR" "$PLUGIN_DIR" <<'PY'
import json, sys
from pathlib import Path
from datetime import datetime, timezone

km_path, ip_path, st_path, mp_dir, plugin_dir = (Path(p) for p in sys.argv[1:6])
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

# known_marketplaces.json
km = json.loads(km_path.read_text()) if km_path.exists() else {}
km["netdust-local"] = {
    "source": {"source": "directory", "path": str(mp_dir)},
    "installLocation": str(mp_dir),
    "lastUpdated": now,
}
km_path.write_text(json.dumps(km, indent=2) + "\n")
print(f"  ✓ {km_path.name}: netdust-local registered")

# installed_plugins.json
ip = json.loads(ip_path.read_text()) if ip_path.exists() else {"version": 2, "plugins": {}}
ip.setdefault("plugins", {})
key = "netdust-core@netdust-local"
if key not in ip["plugins"]:
    ip["plugins"][key] = [{
        "scope": "user",
        "installPath": str(plugin_dir),
        "version": "0.1.0",
        "installedAt": now,
        "lastUpdated": now,
    }]
    print(f"  ✓ {ip_path.name}: {key} installed")
else:
    ip["plugins"][key][0]["lastUpdated"] = now
    print(f"  ✓ {ip_path.name}: {key} updated")
ip_path.write_text(json.dumps(ip, indent=2) + "\n")

# settings.json — enable plugin
st = json.loads(st_path.read_text()) if st_path.exists() else {}
ep = st.setdefault("enabledPlugins", {})
if not ep.get(key):
    ep[key] = True
    st_path.write_text(json.dumps(st, indent=2) + "\n")
    print(f"  ✓ {st_path.name}: {key} enabled")
else:
    print(f"  ✓ {st_path.name}: {key} already enabled")
PY

# ── 3. Logs dir + hook scripts executable ───────────────────────────────────
mkdir -p "$LOGS_DIR"
touch "$LOGS_DIR/memory-hook.log"
if [[ -f "$PLUGIN_DIR/hooks/session-start.sh" ]]; then
  chmod +x "$PLUGIN_DIR/hooks/session-start.sh" "$PLUGIN_DIR/hooks/session-stop.py"
fi
CHANGES+=("ensured $LOGS_DIR + hook scripts executable")

# ── 4. Delete stale dashboard memory mirrors ────────────────────────────────
if [[ -d "$DASHBOARD_MEMORY" ]]; then
  count=$(find "$DASHBOARD_MEMORY" -name STATE.md -type f 2>/dev/null | wc -l)
  if [[ "$count" -gt 0 ]]; then
    find "$DASHBOARD_MEMORY" -name STATE.md -type f -delete
    CHANGES+=("deleted $count stale STATE.md from $DASHBOARD_MEMORY")
  fi
  lcount=$(find "$DASHBOARD_MEMORY" -name lessons.md -type f 2>/dev/null | wc -l)
  if [[ "$lcount" -gt 0 ]]; then
    find "$DASHBOARD_MEMORY" -name lessons.md -type f -delete
    CHANGES+=("deleted $lcount stale lessons.md from $DASHBOARD_MEMORY")
  fi
fi

echo ""
echo "netdust-core installed (plugin mode)."
for c in "${CHANGES[@]}"; do
  echo "  • $c"
done
echo ""
echo "Restart Claude Code to pick up the plugin."
echo "Stack-specific plugins (netdust-wp, future netdust-bun-react) layer on top."
