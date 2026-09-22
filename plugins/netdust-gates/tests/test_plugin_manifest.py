"""test_plugin_manifest.py — the plugin is installable: manifest, marketplace entry, growth rule."""
import json
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
REPO = PLUGIN.parent.parent


def _entry():
    catalog = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
    return next((p for p in catalog["plugins"] if p["name"] == "netdust-gates"), None)


def run() -> list[tuple[bool, str]]:
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text())
    entry = _entry()
    claude_md = (PLUGIN / "CLAUDE.md").read_text()
    return [
        (manifest["name"] == "netdust-gates" and re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]) is not None,
         f"plugin.json names netdust-gates with a semver version (got {manifest['name']} {manifest['version']})"),
        (entry is not None and entry["source"] == "./plugins/netdust-gates"
         and (REPO / entry["source"]).is_dir() and entry["version"] == manifest["version"],
         "marketplace.json carries a netdust-gates entry whose source exists and whose version matches plugin.json"),
        ("Never as a new plan field" in claude_md and "gate tier" in claude_md and "eval case" in claude_md,
         "CLAUDE.md states the growth rule (R9)"),
        ("netdust-agent" in claude_md and "never both" in claude_md.lower(),
         "CLAUDE.md says never enable netdust-agent beside it"),
    ]
