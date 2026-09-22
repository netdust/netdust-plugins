"""test_checks_registry.py — the checks registry (specs/CHECKS.md), checked by bin/shakeout-check.py.

`specs/CHECKS.md` indexes what the shake-outs left to run on a deployed site:
`| surface | tier | entry | test | first feature | verified |`.

- `e2e`   — the flow the shake-out drove, tagged `@e2e`; `make e2e env=staging` runs it
            (seeds, logs in, writes — never production).
- `smoke` — fixture-free and read-only, tagged `@smoke`; `make smoke env=E` runs it,
            production included.
- `auth`  — a surface listed for a later runner; owes no test.

A feature whose manifest drove flows leaves at least one e2e row and one smoke row.
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
HEAD = "# Checks\n\n| surface | tier | entry | test | first feature | verified |\n|---|---|---|---|---|---|\n"
SMOKE_ROW = "| /agenda/ | smoke | GET /agenda/ | tests/e2e/smoke/agenda.spec.ts | feat | a1b2c3d 2026-09-22 |\n"
E2E_ROW = "| /agenda/ filters | e2e | /agenda/?type&when | tests/e2e/agenda.spec.ts | feat | a1b2c3d 2026-09-22 |\n"
AUTH_ROW = "| wp-admin Agenda | auth | GET /wp/wp-admin/edit.php?post_type=event_studio | — | feat | a1b2c3d 2026-09-22 |\n"
SMOKE_SPEC = "test('agenda renders @smoke', async ({ page }) => {});\n"
E2E_SPEC = "test('agenda filters @e2e', async ({ page }) => {});\n"


def _drive(registry, smoke_spec, e2e_spec, manifest):
    with tempfile.TemporaryDirectory() as root:
        r = Path(root)
        feature = r / "specs" / "feat"
        (feature / "shakeout").mkdir(parents=True)
        (feature / "shakeout.md").write_text(manifest)
        (feature / "shakeout" / "af-1.png").write_bytes(PNG)
        if registry is not None:
            (r / "specs" / "CHECKS.md").write_text(registry)
        for rel, text in (("tests/e2e/smoke/agenda.spec.ts", smoke_spec), ("tests/e2e/agenda.spec.ts", e2e_spec)):
            if text is not None:
                p = r / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
        proc = subprocess.run([sys.executable, str(CHECKER), str(feature)],
                              capture_output=True, text=True, timeout=15)
        return proc.returncode, proc.stdout + proc.stderr


def _case(desc, registry, *, rc, has=(), lacks=(), smoke_spec=SMOKE_SPEC, e2e_spec=E2E_SPEC, manifest=MANIFEST):
    got, out = _drive(registry, smoke_spec, e2e_spec, manifest)
    ok = got == rc and all(s in out for s in has) and not any(s in out for s in lacks)
    return ok, f"checks {desc} (rc {got}, expected {rc})"


def run() -> list[tuple[bool, str]]:
    both = HEAD + SMOKE_ROW + E2E_ROW
    return [
        _case("(a) a driven feature with no registry: FAIL, naming CHECKS.md",
              None, rc=1, has=("checks-registry", "CHECKS.md")),
        _case("(a2) a registry naming another feature only: FAIL",
              both.replace("| feat |", "| other |"), rc=1, has=("checks-registry",)),
        _case("(a3) a smoke row but no e2e row: FAIL, the driven flows were left nowhere to re-run",
              HEAD + SMOKE_ROW, rc=1, has=("e2e row",)),
        _case("(a4) an e2e row but no smoke row: FAIL",
              HEAD + E2E_ROW, rc=1, has=("smoke row",)),
        _case("(b) an e2e row and a smoke row, tests present and tagged: PASS",
              both, rc=0, has=("[checks-registry] 2 rows",)),
        _case("(c) a row whose test file is missing: FAIL, naming the path",
              both, rc=1, smoke_spec=None, has=("tests/e2e/smoke/agenda.spec.ts",)),
        _case("(d) a smoke test without @smoke never runs under make smoke: FAIL",
              both, rc=1, smoke_spec=SMOKE_SPEC.replace(" @smoke", ""), has=("@smoke",)),
        _case("(d2) an e2e test without @e2e never runs under make e2e: FAIL",
              both, rc=1, e2e_spec=E2E_SPEC.replace(" @e2e", ""), has=("@e2e",)),
        _case("(e) an auth row is listed for a later runner and owes no test",
              both + AUTH_ROW, rc=0, has=("3 rows",)),
        _case("(e2) a row with an unknown tier: FAIL, naming the tiers",
              both + SMOKE_ROW.replace("| smoke |", "| quick |"), rc=1, has=("tier",)),
        _case("(f) a manifest with no rows fails on its own and owes no registry row",
              None, rc=1, lacks=("checks-registry",), manifest=MANIFEST.split("| AF-1")[0]),
    ]


if __name__ == "__main__":
    for passed, desc in run():
        print(("pass" if passed else "FAIL") + "\t" + desc)
