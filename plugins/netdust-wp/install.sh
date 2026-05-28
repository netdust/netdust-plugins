#!/usr/bin/env bash
# install.sh — netdust-wp, plugin-marketplace mode
#
# Layers on top of netdust-core. Warns if core is not installed/enabled, then
# registers + enables this plugin via the shared local marketplace.
#
# Skills/commands/templates load DIRECTLY from this dir via ${CLAUDE_PLUGIN_ROOT}.
# No symlinks. No copies. Edit in place — picked up on next session.
#
# Idempotent. Safe to re-run after harness updates.

set -euo pipefail

PLUGIN_DIR="$HOME/.claude/plugins/netdust-wp"
CORE_DIR="$HOME/.claude/plugins/netdust-core"
MARKETPLACE_DIR="$HOME/.claude/plugins/marketplaces/netdust-local"
KM="$HOME/.claude/plugins/known_marketplaces.json"
IP="$HOME/.claude/plugins/installed_plugins.json"
SETTINGS="$HOME/.claude/settings.json"

if [[ ! -d "$PLUGIN_DIR" ]]; then
  echo "✗ $PLUGIN_DIR does not exist. Clone the plugin first." >&2
  exit 1
fi

# ── 0. Soft dep on netdust-core ─────────────────────────────────────────────
if [[ ! -d "$CORE_DIR" ]]; then
  echo "⚠ netdust-core is not installed at $CORE_DIR" >&2
  echo "  netdust-wp depends on it for memory, hooks, /deploy, secure-server, ploi, etc." >&2
  echo "  Install netdust-core first: bash $CORE_DIR/install.sh" >&2
  echo "  Continuing anyway — WP skills will work but the harness will be incomplete." >&2
  echo "" >&2
fi

CHANGES=()

# ── 1. Marketplace manifest (add/update netdust-wp entry without touching siblings) ─
mkdir -p "$MARKETPLACE_DIR/.claude-plugin"
MFEST="$MARKETPLACE_DIR/.claude-plugin/marketplace.json"
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

new_entry = {
    "name": "netdust-wp",
    "source": {"source": "directory", "path": plugin_dir},
    "description": "Netdust WordPress plugin — WP discipline, WP reference, ntdst-core framework, WP commands. Layers on netdust-core.",
    "version": "0.2.0",
    "strict": False,
}
plugins = [p for p in existing["plugins"] if p.get("name") != "netdust-wp"]
plugins.append(new_entry)
existing["plugins"] = plugins

mfest.write_text(json.dumps(existing, indent=2) + "\n")
print(f"  ✓ {mfest}: netdust-wp entry written")
PY
CHANGES+=("updated marketplace manifest $MFEST")

# ── 2. Register marketplace + install + enable plugin ───────────────────────
python3 - "$KM" "$IP" "$SETTINGS" "$MARKETPLACE_DIR" "$PLUGIN_DIR" <<'PY'
import json, sys
from pathlib import Path
from datetime import datetime, timezone

km_path, ip_path, st_path, mp_dir, plugin_dir = (Path(p) for p in sys.argv[1:6])
now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

km = json.loads(km_path.read_text()) if km_path.exists() else {}
if "netdust-local" not in km:
    km["netdust-local"] = {
        "source": {"source": "directory", "path": str(mp_dir)},
        "installLocation": str(mp_dir),
        "lastUpdated": now,
    }
    km_path.write_text(json.dumps(km, indent=2) + "\n")
    print(f"  ✓ {km_path.name}: netdust-local registered")
else:
    print(f"  ✓ {km_path.name}: netdust-local already registered")

ip = json.loads(ip_path.read_text()) if ip_path.exists() else {"version": 2, "plugins": {}}
ip.setdefault("plugins", {})
key = "netdust-wp@netdust-local"
if key not in ip["plugins"]:
    ip["plugins"][key] = [{
        "scope": "user",
        "installPath": str(plugin_dir),
        "version": "0.2.0",
        "installedAt": now,
        "lastUpdated": now,
    }]
    print(f"  ✓ {ip_path.name}: {key} installed")
else:
    ip["plugins"][key][0]["lastUpdated"] = now
    ip["plugins"][key][0]["version"] = "0.2.0"
    print(f"  ✓ {ip_path.name}: {key} updated to 0.2.0")
ip_path.write_text(json.dumps(ip, indent=2) + "\n")

st = json.loads(st_path.read_text()) if st_path.exists() else {}
ep = st.setdefault("enabledPlugins", {})
if not ep.get(key):
    ep[key] = True
    st_path.write_text(json.dumps(st, indent=2) + "\n")
    print(f"  ✓ {st_path.name}: {key} enabled")
else:
    print(f"  ✓ {st_path.name}: {key} already enabled")
PY

echo ""
echo "netdust-wp installed (plugin mode)."
for c in "${CHANGES[@]}"; do
  echo "  • $c"
done
echo ""
echo "Restart Claude Code to pick up the plugin."
echo "Requires netdust-core for memory, hooks, /deploy, secure-server, ploi, etc."
