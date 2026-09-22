"""test_shakeout_check.py — the manifest gate. A pass is a property of a file, never of a
verdict word: browser evidence needs an http URL and a real PNG; the WHOLE file is scanned for
credentials with no override; only the human's `Accepted-by-human:` excuses a row."""
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent.parent / "bin" / "shakeout-check.py"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PNG = {"shakeout/af-1.png": PNG_MAGIC + bytes(1200)}

HEAD = "# Shake-out — audit screen\n\n| # | Flow | Layer | Verdict | Evidence |\n|---|---|---|---|---|\n"
WIRE_PASS = "| AF-2 | REST list returns the rows | wire | pass | curl -s https://x.ddev.site/wp-json/audit/v1/rows → 200, 3 items |\n"
EVIDENCE = "Browser: https://x.ddev.site/wp/wp-admin/admin.php?page=audit · shakeout/af-1.png"
BROWSER = "| AF-1 | Audit page lists the rows | browser | pass | {} |\n"
DRIVEN = HEAD + BROWSER.format(EVIDENCE) + WIRE_PASS
ACCEPTED = HEAD + BROWSER.format("Accepted-by-human: no browser on this box, driven by Stefan 09-06") + WIRE_PASS


def _drive(manifest, binaries=None, target="feat") -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as root:
        feature = Path(root) / "specs" / "feat"
        feature.mkdir(parents=True)
        if manifest is not None:
            (feature / "shakeout.md").write_text(manifest)
        for name, data in (binaries or {}).items():
            path = feature / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        # A complete close: the driven feature also left its smoke row and the tagged spec
        # (test_smoke_registry.py pins that rule; here it is background).
        (Path(root) / "specs").mkdir(exist_ok=True)
        (Path(root) / "specs" / "SMOKE.md").write_text(
            "| surface | entry | test | first feature | verified |\n|---|---|---|---|---|\n"
            "| audit | GET /wp/wp-admin/admin.php?page=audit | tests/e2e/smoke/audit.spec.ts | feat | 0000000 2026-09-06 |\n")
        spec = Path(root) / "tests" / "e2e" / "smoke" / "audit.spec.ts"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text("test('audit renders @smoke', async () => {});\n")
        proc = subprocess.run([sys.executable, str(CHECKER), str(Path(root) / "specs" / target)],
                              capture_output=True, text=True, timeout=15)
        return proc.returncode, proc.stdout + proc.stderr


def _case(desc, manifest, binaries=None, *, rc=1, has=(), lacks=(), target="feat"):
    got, out = _drive(manifest, binaries, target)
    ok = got == rc and all(s in out for s in has) and not any(s in out for s in lacks)
    return ok, f"{desc} (rc {got}, expected {rc})"


CREDENTIALS = {
    "curl -u user:pass": DRIVEN.replace("curl -s https://", "curl -u shakeout:s3cr3tPw https://"),
    "user: name:pass": DRIVEN.replace("curl -s https://", "user: shakeout:s3cr3tPw · curl -s https://"),
    "bare pwd=": DRIVEN.replace("curl -s https://", "pwd=s3cr3t, curl -s https://"),
    "bare password:": DRIVEN.replace("curl -s https://", "password: s3cr3t, curl -s https://"),
    "E2E_PASS=": DRIVEN.replace("curl -s https://", "E2E_PASS=abc123, curl -s https://"),
    "--user_pass=": DRIVEN.replace("curl -s https://", "curl --user_pass=x https://"),
    "-u no space": DRIVEN.replace("curl -s https://", "curl -ushakeout:pw https://"),
    "Authorization: Bearer": DRIVEN.replace("curl -s https://", "curl -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiJ9' https://"),
    "bare Basic": DRIVEN.replace("curl -s https://", "sent Basic c2hha2VvdXQ6czNjcjN0UHc= to https://"),
    "wp-login.php?": ACCEPTED.replace("Stefan 09-06", "Stefan 09-06 via https://x.ddev.site/wp/wp-login.php?redirect_to=%2Fwp-admin%2F"),
    "magic link": ACCEPTED.replace("Stefan 09-06", "Stefan 09-06 via https://x.ddev.site/3f9a1c2b/7a3c1d9e2f-b41c8d7e-9f0a2b3c4d"),
    "application-password": DRIVEN.replace("curl -s https://", "wp user application-password create shakeout shakeout --porcelain, then curl -s https://"),
    "6x4 app password": DRIVEN.replace("curl -s https://", "minted AbCd EfGh IjKl MnOp QrSt UvWx, curl -s https://"),
    "basic auth in URL": DRIVEN.replace("https://x.ddev.site/wp-json", "https://shakeout:s3cr3tPw@x.ddev.site/wp-json"),
    "--user=": DRIVEN.replace("curl -s https://", "curl --user=shakeout:s3cr3tPw https://"),
    "session cookie": DRIVEN.replace("curl -s https://", "curl -b wordpress_logged_in_0123456789abcdef0123456789abcdef=shakeout https://"),
    "storage_state": DRIVEN.replace("curl -s https://", "storage_state=auth.json · curl -s https://"),
    "pwd= POST body": DRIVEN.replace("curl -s https://", "curl -d 'log=shakeout&pwd=s3cr3tPw' https://x.ddev.site/wp/wp-login.php, then curl -s https://"),
    "bare Bearer": DRIVEN.replace("curl -s https://", "Bearer 4f9a2b7c1d8e3f6a5b4c9d0e1f2a3b4c · curl -s https://"),
    "bare JWT": DRIVEN.replace("curl -s https://", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.abc · curl -s https://"),
    "JSON token": DRIVEN.replace("→ 200, 3 items", '→ 200 {"access_token": "4f9a2b7c1d8e"}'),
}

NOT_CREDENTIALS = {
    "_wpnonce=": DRIVEN.replace("page=audit", "page=audit&_wpnonce=abc123"),
    "prose": DRIVEN.replace("→ 200, 3 items", "→ 200, the password reset flow renders"),
    "six short words": DRIVEN.replace("→ 200, 3 items", "→ 200, this page does show some rows"),
    "verdict word pass:": DRIVEN.replace("→ 200, 3 items", "→ 200; pass: body has 3 rows"),
    "--url= flag": DRIVEN.replace("curl -s https://x.ddev.site/wp-json/audit/v1/rows → 200, 3 items",
                                  "ddev wp --url=https://x.ddev.site option get siteurl → https://x.ddev.site"),
    "pop-up: prose": DRIVEN.replace("→ 200, 3 items", "→ 200, the pop-up: closes on Escape"),
}


def run() -> list[tuple[bool, str]]:
    r = [
        # Review Focus 1 — a missing, empty or rowless manifest never passes vacuously
        _case("no manifest → FAIL", None, has=("no shakeout.md",)),
        _case("empty manifest → FAIL", "", has=("no rows",)),
        _case("header-only table → FAIL", HEAD, has=("no rows",)),
        _case("a directory that does not exist → FAIL", None, target="missing", has=("not a directory",)),
        # the happy path and the browser evidence rules
        _case("driven browser row + PNG on disk → PASS", DRIVEN, PNG, rc=0,
              has=("2 rows, 1 browser rows driven", "SHAKEOUT: PASS")),
        _case("browser row with no `Browser:` evidence → FAIL naming AF-1",
              HEAD + BROWSER.format("looked at it, table renders") + WIRE_PASS, has=("AF-1: browser row without",)),
        _case("no http url (`Browser: not-reached · png`) → FAIL", DRIVEN.replace("https://x.ddev.site/wp/wp-admin/admin.php?page=audit", "not-reached"),
              PNG, has=("http url",)),
        _case("evidence names a PNG that is not on disk → FAIL", DRIVEN, has=("shakeout/af-1.png", "not found")),
        # Review Focus 2 — the screenshot cannot escape or be faked
        _case("traversal out of the feature dir → FAIL", DRIVEN.replace("shakeout/af-1.png", "shakeout/../../escape.png"),
              {"../escape.png": PNG_MAGIC + bytes(1200)}, has=("not found under the feature dir",)),
        _case("a PNG under 1 KB → FAIL", DRIVEN, {"shakeout/af-1.png": PNG_MAGIC + bytes(10)}, has=("bytes",)),
        _case("not a PNG → FAIL", DRIVEN, {"shakeout/af-1.png": b"GIF89a" + bytes(1200)}, has=("PNG magic",)),
        _case("`unverified-no-browser` on a browser row → FAIL", DRIVEN.replace("| pass |", "| unverified-no-browser |", 1), PNG),
        # rows the plan no longer classifies: the manifest's own Layer must be valid
        _case("a blank Layer cell → FAIL", DRIVEN.replace("| browser |", "|  |", 1), PNG, has=("not one of",)),
        _case("a `wire` row `fail` → FAIL naming AF-2", DRIVEN.replace(WIRE_PASS, "| AF-2 | REST list | wire | fail | curl → 500 |\n"), PNG, has=("AF-2",)),
        _case("a `wire` row `pass` alone → PASS", HEAD + WIRE_PASS, rc=0, has=("1 rows, 0 browser rows driven",)),
        _case("a fenced sample row is not read", "```\n| AF-9 | sample | browser | pass | none |\n```\n" + DRIVEN, PNG, rc=0, has=("2 rows",)),
        # fix pass — only `pass` passes; no row can hide from the check
        _case("a `wire` row `not-reachable` alone → FAIL", HEAD + WIRE_PASS.replace("| pass |", "| not-reachable |"),
              has=("AF-2", "not a pass")),
        _case("a `wire` row with a blank verdict → FAIL", HEAD + WIRE_PASS.replace("| pass |", "|  |"), has=("AF-2",)),
        _case("a `cli` row `pending` → FAIL", HEAD + WIRE_PASS.replace("| wire | pass |", "| cli | pending |"), has=("not a pass",)),
        _case("a failing row after a blank line is not hidden → FAIL", DRIVEN + "\n| AF-3 | late | browser | fail | x |\n",
              PNG, has=("outside the table",)),
        _case("a row with a blank # cell is not dropped → FAIL", HEAD + WIRE_PASS + "|  | nameless | wire | pass | curl → 200 |\n",
              has=("row without a # cell",)),
        # Review Focus 3 — only the human's token excuses a row
        _case("`Accepted-by-human:` excuses the row → PASS", ACCEPTED, rc=0,
              has=("[shakeout-accepted] AF-1: accepted by the human", "no browser on this box")),
        _case("old `Ruling:` token fails", ACCEPTED.replace("Accepted-by-human:", "Ruling:"),
              has=("AF-1: browser row without",), lacks=("shakeout-accepted",)),
        _case("accepted with a credential is reported, never echoed",
              ACCEPTED.replace("Stefan 09-06", "Stefan 09-06 via https://x.ddev.site/3f9a1c2b/7a3c1d9e2f-b41c8d7e-9f0a2b3c4d"),
              has=("[shakeout-accepted] AF-1: accepted by the human", "✗ [shakeout-credential]"), lacks=("3f9a1c2b",)),
        _case("a fenced curl transcript below the table fails naming its line",
              DRIVEN + "\n## How I logged in\n\n```\ncurl -u shakeout:s3cr3tPw https://x.ddev.site/wp-json/\n```\n",
              PNG, has=("✗ [shakeout-credential] line 11:",)),
    ]
    r += [_case(f"credential `{label}` → FAIL shakeout-credential", m, PNG, has=("✗ [shakeout-credential]",))
          for label, m in CREDENTIALS.items()]
    r += [_case(f"`{label}` is not a credential", m, PNG, rc=0, lacks=("shakeout-credential",))
          for label, m in NOT_CREDENTIALS.items()]
    return r
