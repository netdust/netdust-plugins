#!/usr/bin/env bash
# netdust × spec-kit — per-project setup.
#
# Installs spec-kit's .specify/ into the target project, then layers the netdust
# gate-bearing override templates on top. Idempotent: re-running refreshes the overrides
# without re-initializing spec-kit.
#
# Decision (ADR 2026-06-17): the OVERRIDE templates are BUNDLED in netdust-agent (this dir);
# spec-kit CORE is installed PER-PROJECT here. So projects share one gate definition while
# spec-kit itself can be pinned/updated per project.
#
# Usage:
#   plugins/netdust-agent/spec-kit/setup.sh [PROJECT_ROOT]   # defaults to $PWD
#
# Env overrides:
#   SPECIFY_REF        spec-kit git ref to install        (default: main — PIN THIS in prod)
#   SPECIFY_INIT_CMD   full init command, if flags differ (default: see below)
#   SKIP_SPECIFY_INIT  set to 1 to only (re)copy overrides

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERRIDES_SRC="${SCRIPT_DIR}/overrides"
PROJECT_ROOT="${1:-$PWD}"
SPECIFY_REF="${SPECIFY_REF:-main}"

say() { printf '  %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[ -d "$OVERRIDES_SRC" ] || die "override templates not found at $OVERRIDES_SRC"
[ -d "$PROJECT_ROOT" ]  || die "project root does not exist: $PROJECT_ROOT"

echo "netdust × spec-kit setup"
say "project : $PROJECT_ROOT"
say "overrides: $OVERRIDES_SRC"
say "spec-kit ref: $SPECIFY_REF"

# 1. Install spec-kit core (.specify/) if not already present.
if [ "${SKIP_SPECIFY_INIT:-0}" != "1" ] && [ ! -d "$PROJECT_ROOT/.specify" ]; then
  command -v uvx >/dev/null 2>&1 || die "uvx not found — install uv (https://docs.astral.sh/uv/) or set SKIP_SPECIFY_INIT=1 and init spec-kit manually."
  DEFAULT_INIT="uvx --from git+https://github.com/github/spec-kit.git@${SPECIFY_REF} specify init --here --ai claude"
  INIT_CMD="${SPECIFY_INIT_CMD:-$DEFAULT_INIT}"
  echo "==> initializing spec-kit:"
  say "$INIT_CMD"
  ( cd "$PROJECT_ROOT" && eval "$INIT_CMD" ) || die "spec-kit init failed. If the CLI flags differ, set SPECIFY_INIT_CMD to the correct command and re-run."
  [ -d "$PROJECT_ROOT/.specify" ] || die "spec-kit init ran but .specify/ was not created — check the init command."
else
  say ".specify/ present (or SKIP_SPECIFY_INIT=1) — skipping init"
fi

# 2. Layer the netdust gate-bearing overrides (highest-priority template resolution).
DEST="$PROJECT_ROOT/.specify/templates/overrides"
mkdir -p "$DEST"
echo "==> installing netdust override templates → $DEST"
for f in spec-template.md plan-template.md tasks-template.md; do
  [ -f "$OVERRIDES_SRC/$f" ] || die "missing override: $OVERRIDES_SRC/$f"
  cp "$OVERRIDES_SRC/$f" "$DEST/$f"
  say "✓ $f"
done

# 3. Constitution: leave a pointer; the real generation is the constitution-bridge skill.
mkdir -p "$PROJECT_ROOT/.specify/memory"
CONST="$PROJECT_ROOT/.specify/memory/constitution.md"
if [ ! -f "$CONST" ]; then
  cat > "$CONST" <<'EOF'
<!-- PLACEHOLDER — run the netdust-agent:constitution-bridge skill to generate this file
     as a VIEW over RULES.md + SOUL.md + ARCHITECTURE-INVARIANTS.md.
     Do NOT author governance here; it lives in those sources. -->
# Project Constitution (not yet generated)

Run: invoke the `constitution-bridge` skill (or `/speckit.constitution` is REPLACED by it).
EOF
  say "✓ constitution placeholder written → run constitution-bridge to populate"
else
  say "constitution.md present — leaving as-is (regenerate via constitution-bridge)"
fi

echo "Done. Next:"
say "1. Run the constitution-bridge skill to generate the constitution from RULES/SOUL/invariants."
say "2. Use /speckit.specify → /speckit.clarify → /speckit.plan → /speckit.tasks."
say "3. Hand tasks.md to harnessed-development Stage 2. NEVER run /speckit.implement."
