"""test_smoke_registry.py — the smoke registry, checked by bin/shakeout-check.py.

`specs/SMOKE.md` is the project-level index of read-only checks `make smoke env=E` runs
against a deployed site: `| surface | entry | test | first feature | verified |`. A row's
`test` is a committed spec tagged `@smoke` (fixture-free, no login, no writes); a row whose
entry is marked `auth` is listed for a later runner and owes no tag. A feature whose manifest
drove flows must leave at least one row — a shake-out that leaves no smoke check leaves the
deployed site unwatched.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent.parent / "bin" / "shakeout-check.py"

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 1200
MANIFEST = (
    "# Shake-out — feat\n\n| # | Flow | Layer | Verdict | Evidence |\n|---|---|---|---|---|\n"
    "| AF-1 | Agenda lists events | browser | pass | Browser: https://x.ddev.site/agenda/ · shakeout/af-1.png |\n"
)
HEAD = "# Smoke registry\n\n| surface | entry | test | first feature | verified |\n|---|---|---|---|---|\n"
ROW = "| /agenda/ | GET /agenda/ | tests/e2e/smoke/agenda.spec.ts | feat | a1b2c3d 2026-09-22 |\n"
AUTH_ROW = "| wp-admin Agenda | auth GET /wp/wp-admin/edit.php?post_type=event_studio | — | feat | a1b2c3d 2026-09-22 |\n"
SPEC = "import { test, expect } from '@playwright/test';\ntest('agenda renders @smoke', async ({ page }) => {});\n"


def _drive(registry: str | None, spec: str | None, manifest: str = MANIFEST) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as root:
        r = Path(root)
        feature = r / "specs" / "feat"
        (feature / "shakeout").mkdir(parents=True)
        (feature / "shakeout.md").write_text(manifest)
        (feature / "shakeout" / "af-1.png").write_bytes(PNG)
        if registry is not None:
            (r / "specs" / "SMOKE.md").write_text(registry)
        if spec is not None:
            p = r / "tests" / "e2e" / "smoke" / "agenda.spec.ts"
            p.parent.mkdir(parents=True)
            p.write_text(spec)
        proc = subprocess.run([sys.executable, str(CHECKER), str(feature)],
                              capture_output=True, text=True, timeout=15)
        return proc.returncode, proc.stdout + proc.stderr


def _case(desc, registry, spec, *, rc, has=(), lacks=(), manifest=MANIFEST):
    got, out = _drive(registry, spec, manifest)
    ok = got == rc and all(s in out for s in has) and not any(s in out for s in lacks)
    return ok, f"smoke {desc} (rc {got}, expected {rc})"


def run() -> list[tuple[bool, str]]:
    return [
        _case("(a) a driven feature with no registry row: FAIL, naming SMOKE.md",
              None, SPEC, rc=1, has=("smoke-registry", "SMOKE.md")),
        _case("(a') a registry that exists but names another feature only: FAIL",
              HEAD + ROW.replace("| feat |", "| other |"), SPEC, rc=1, has=("smoke-registry",)),
        _case("(b) a row whose test exists and is tagged @smoke: PASS",
              HEAD + ROW, SPEC, rc=0, has=("[smoke-registry] 1 row",)),
        _case("(c) a row whose test file is missing: FAIL, naming the path",
              HEAD + ROW, None, rc=1, has=("smoke-registry", "tests/e2e/smoke/agenda.spec.ts")),
        _case("(d) a test without the @smoke tag never runs under make smoke: FAIL",
              HEAD + ROW, SPEC.replace(" @smoke", ""), rc=1, has=("@smoke",)),
        _case("(e) an auth row lists the surface for a later runner and owes no tag",
              HEAD + ROW + AUTH_ROW, SPEC, rc=0, has=("2 rows",)),
        _case("(f) a manifest with no driven rows owes no registry row — but has no rows, so the manifest itself fails",
              None, None, rc=1, lacks=("smoke-registry",), manifest=MANIFEST.split("| AF-1")[0]),
    ]


if __name__ == "__main__":
    for passed, desc in run():
        print(("pass" if passed else "FAIL") + "\t" + desc)
