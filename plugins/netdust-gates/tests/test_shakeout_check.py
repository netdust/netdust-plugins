"""test_shakeout_check.py — the manifest gate. A pass is a property of a file, never of a
verdict word: browser evidence needs an http URL and a real PNG; every browser and wire row names
its one test (`Test: <path> :: <title>`) and a NEW test is proven by its revert log showing an
assertion failure on the base; the WHOLE file and every revert log are scanned for credentials
with no override; only the human's `Accepted-by-human:` excuses a row."""
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).resolve().parent.parent / "bin" / "shakeout-check.py"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
PNG = {"shakeout/af-1.png": PNG_MAGIC + bytes(1200)}

TEST_B = "Test: tests/e2e/audit.spec.ts :: Audit page lists the rows"
TEST_W = "Test: tests/integration/AuditRestTest.php :: testListReturnsRows"
STEM_B = "tests__e2e__audit.spec.ts--audit-page-lists-the-rows"
STEM_W = "tests__integration__AuditRestTest.php--testlistreturnsrows"
# The same title test_revert_run.py pins: the stem is one rule in two languages.
ODD_TITLE, ODD_STEM = "Crédits: 2 × 3 @e2e", "tests__e2e__x.spec.ts--cr-dits-2-3-e2e"
HEAD = "# Shake-out — audit screen\n\n| # | Flow | Layer | Verdict | Evidence |\n|---|---|---|---|---|\n"
WIRE_PASS = f"| AF-2 | REST list returns the rows | wire | pass | {TEST_W} · curl -s https://x.ddev.site/wp-json/audit/v1/rows → 200, 3 items |\n"
EVIDENCE = f"{TEST_B} · Browser: https://x.ddev.site/wp/wp-admin/admin.php?page=audit · shakeout/af-1.png"
BROWSER = "| AF-1 | Audit page lists the rows | browser | pass | {} |\n"
TALLY = "Hunt: 2 charters · 0 confirmed · 0 not ours · 1 rejected"
HUNT = (f"\n{TALLY}\n- charter: the audit page as a first-time visitor\n- charter: the audit rows after a reload\n"
        "- rejected: rows sort by id | seed data has no dates\n")
NO_HUNT = "\nHunt: 0 charters — no browser on this box\n"
UNHUNTED = HEAD + BROWSER.format(EVIDENCE) + WIRE_PASS
DRIVEN = UNHUNTED + HUNT
ACCEPTED = HEAD + BROWSER.format("Accepted-by-human: no browser on this box, driven by Stefan 09-06") + WIRE_PASS + NO_HUNT
HUNT_TABLE = "\n## Hunt\n\n| charter | outcome |\n|---|---|\n| the audit page, first-time visitor | rejected: seed data |\n"

REGISTRY_HEAD = "| surface | tier | entry | test | first feature | verified |\n|---|---|---|---|---|---|\n"
REGISTRY = (REGISTRY_HEAD
            + "| audit | smoke | GET /audit/ | tests/e2e/smoke/audit.spec.ts | feat | 0000000 2026-09-06 |\n"
            + "| audit rows | e2e | /wp/wp-admin/admin.php?page=audit | tests/e2e/audit.spec.ts | feat | 0000000 2026-09-06 |\n")
PRODUCTIONS = "".join(f"| production {i} | e2e | /voorstellingen/{i}/ | `tests/e2e/productions.spec.ts` | productions | 6920cb9 2026-10-17 |\n"
                      for i in range(1, 6))
P_TITLES = [f"production {i} shows its facts @e2e" for i in range(1, 6)]
P_ROWS = "".join(f"| P-{i} | production {i} | browser | pass | Test: tests/e2e/productions.spec.ts :: {t} · "
                 f"Browser: https://x.ddev.site/voorstellingen/{i}/ · shakeout/p-{i}.png |\n" for i, t in enumerate(P_TITLES, 1))
P_PNGS = {f"shakeout/p-{i}.png": PNG_MAGIC + bytes(1200) for i in range(1, 6)}
NEW_TITLE = "a production shows its credits @e2e"
NEW_STEM = "tests__e2e__productions.spec.ts--a-production-shows-its-credits-e2e"
NEW_ROW = (f"| AF-6 | credits | browser | pass | Test: tests/e2e/productions.spec.ts :: {NEW_TITLE} · "
           "Browser: https://x.ddev.site/voorstellingen/6/ · shakeout/af-1.png |\n")
SPEC_FIVE = "".join(f"test('{t}', async ({{ page }}) => {{}});\n" for t in P_TITLES)
SPEC_SIX = SPEC_FIVE + f"test('{NEW_TITLE}', async ({{ page }}) => {{}});\n"


def _log(cls="assertion-failed", command="npx playwright test tests/e2e/audit.spec.ts --grep 'Audit page lists the rows'"):
    return (f"revert-run: {cls}\nfeature: feat\ntest: tests/e2e/audit.spec.ts :: Audit page lists the rows\nbase: 0000000 (main)\n"
            f"swapped: web/app/mu-plugins/audit/screen.php (M)\ncommand: {command}\nexit: {0 if cls == 'passed' else 1}\n"
            "--- output: 3 lines, excerpt 1-3 ---\nError: expect(locator).toBeVisible() failed\nExpected: visible\n"
            "Received: <element(s) not found>\n")


LOGS = {f"shakeout/{STEM_B}.revert.txt": _log(), f"shakeout/{STEM_W}.revert.txt": _log()}


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=T", *args],
                   capture_output=True, text=True, check=True)


def _drive(manifest, binaries=None, target="feat", *, registry=REGISTRY, logs=LOGS, texts=None, base=None,
           files=None) -> tuple[int, str]:
    """A feature dir under a project root. `files` are root-relative project files; the root is a
    git repo only when `base` names files to commit on main before the feature commit (the
    mixed-file rule reads the base's copy)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if base is not None:
            _git(root, "init", "-q", "-b", "main", ".")
            for rel, text in base.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text)
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "base")
            _git(root, "checkout", "-qb", "feature/feat")
        for rel, text in (files or {}).items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text)
        feature = root / "specs" / "feat"
        feature.mkdir(parents=True)
        if manifest is not None:
            (feature / "shakeout.md").write_text(manifest)
        for name, data in {**(binaries or {}), **{k: v.encode() for k, v in {**(logs or {}), **(texts or {})}.items()}}.items():
            path = feature / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        # A complete close: the driven feature also left its registry rows and every test they
        # name, tagged for its tier (test_checks_registry.py pins that rule; here it is background).
        (root / "specs" / "CHECKS.md").write_text(registry)
        for ln in registry.splitlines()[2:]:
            cells = [c.strip().strip("`") for c in ln.strip().strip("|").split("|")]
            if len(cells) < 4 or cells[1] not in ("e2e", "smoke"):
                continue
            spec = root / cells[3]
            if not spec.exists():
                spec.parent.mkdir(parents=True, exist_ok=True)
                spec.write_text(f"test('{cells[0]} @{cells[1]}', async () => {{}});\n")
        if base is not None:
            _git(root, "add", "-A")
            _git(root, "commit", "-qm", "feature")
        proc = subprocess.run([sys.executable, str(CHECKER), str(root / "specs" / target)],
                              capture_output=True, text=True, timeout=30)
        return proc.returncode, proc.stdout + proc.stderr


def _case(desc, manifest, binaries=None, *, rc=1, has=(), lacks=(), target="feat", **kw):
    got, out = _drive(manifest, binaries, target, **kw)
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

# ── the revert proof (R2): a new browser or wire row names its test and owns a log that failed on an assertion
PW_PATH = "tests/e2e/app-password.spec.ts"
PW_EVIDENCE = EVIDENCE.replace("tests/e2e/audit.spec.ts", PW_PATH)
PW_LOGS = {f"shakeout/tests__e2e__app-password.spec.ts--audit-page-lists-the-rows.revert.txt": _log(), **{k: v for k, v in LOGS.items() if STEM_W in k}}
ODD_EVIDENCE = EVIDENCE.replace("tests/e2e/audit.spec.ts :: Audit page lists the rows", f"tests/e2e/x.spec.ts :: {ODD_TITLE}")
ODD_LOGS = {f"shakeout/{ODD_STEM}.revert.txt": _log(), **{k: v for k, v in LOGS.items() if STEM_W in k}}
MIXED_REGISTRY = (REGISTRY + PRODUCTIONS
                  + f"| credits | e2e | /voorstellingen/<slug>/ | tests/e2e/productions.spec.ts | feat | 0000000 2026-11-06 |\n")
MIXED = HEAD + BROWSER.format(EVIDENCE) + P_ROWS + NEW_ROW + HUNT
MIXED_LOGS = {**LOGS, f"shakeout/{NEW_STEM}.revert.txt": _log()}
MIXED_PNGS = {**PNG, **P_PNGS}
BASE_FIVE = {"tests/e2e/productions.spec.ts": SPEC_FIVE, "src/page.php": "<h1>Title</h1>\n"}
ON_BRANCH = {"tests/e2e/productions.spec.ts": SPEC_SIX}


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
        _case("a `wire` row `fail` → FAIL naming AF-2", DRIVEN.replace(WIRE_PASS, f"| AF-2 | REST list | wire | fail | {TEST_W} · curl → 500 |\n"), PNG, has=("AF-2",)),
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
        # the hunt is recorded under the table as plain lines, even when it found nothing
        _case("a browser manifest with no `Hunt:` line → FAIL", UNHUNTED, PNG, has=("✗ [shakeout-hunt]",)),
        _case("a fenced `Hunt:` line is not read → FAIL", UNHUNTED + "```\n" + HUNT + "```\n", PNG,
              has=("✗ [shakeout-hunt]",)),
        _case("the hunt's tally is echoed → PASS", DRIVEN, PNG, rc=0, has=(f"✓ [shakeout-hunt] {TALLY}",)),
        _case("a hunt that could not run names why → PASS", UNHUNTED + NO_HUNT, PNG, rc=0,
              has=("✓ [shakeout-hunt] Hunt: 0 charters — no browser on this box",)),
        _case("a bare `Hunt: 3 charters` → FAIL", UNHUNTED + "\nHunt: 3 charters\n", PNG, has=("✗ [shakeout-hunt]",)),
        _case("`Hunt: 0 charters` with no reason → FAIL", UNHUNTED + "\nHunt: 0 charters\n", PNG, has=("✗ [shakeout-hunt]",)),
        _case("an indented tally is not read, as the trial's grep would not → FAIL", UNHUNTED + f"\n  {TALLY}\n", PNG,
              has=("✗ [shakeout-hunt]",)),
        _case("a credential-shaped tally is reported, never echoed",
              UNHUNTED + "\nHunt: 0 charters — no browser, password: s3cr3t\n", PNG,
              has=("✓ [shakeout-hunt] Hunt line recorded", "✗ [shakeout-credential]"), lacks=("s3cr3t",)),
        _case("a wire-only manifest owes no hunt → PASS", HEAD + WIRE_PASS, rc=0, lacks=("shakeout-hunt",)),
        _case("the hunt's record as a table → FAIL", DRIVEN + HUNT_TABLE, PNG, has=("outside the table",)),
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
              PNG, has=("✗ [shakeout-credential] line 16:",)),
        # Review Focus 2 (R2) — the revert proof: a new row owns a log that failed on an assertion
        _case("test_new_browser_row_with_assertion_failed_log_passes", DRIVEN, PNG, rc=0,
              has=("✓ [shakeout-revert]", "2 new row")),
        _case("test_new_wire_row_without_test_marker_fails", HEAD + WIRE_PASS.replace(f"{TEST_W} · ", ""),
              has=("✗ [shakeout-revert] AF-2: no `Test: <path> :: <title>`",)),
        _case("test_new_row_without_its_log_fails", DRIVEN, PNG, logs={k: v for k, v in LOGS.items() if STEM_W in k},
              has=(f"✗ [shakeout-revert] AF-1: no revert log at shakeout/{STEM_B}.revert.txt",)),
        _case("test_error_log_does_not_prove_a_row", DRIVEN, PNG, logs={**LOGS, f"shakeout/{STEM_B}.revert.txt": _log("error")},
              has=("✗ [shakeout-revert] AF-1:", "error run")),
        _case("test_passed_log_does_not_prove_a_row", DRIVEN, PNG, logs={**LOGS, f"shakeout/{STEM_B}.revert.txt": _log("passed")},
              has=("✗ [shakeout-revert] AF-1:", "passing on the base")),
        _case("test_two_new_rows_cannot_share_one_key: two new rows on one file and title fail, naming both",
              UNHUNTED + BROWSER.format(EVIDENCE).replace("AF-1", "AF-3") + HUNT, PNG,
              has=("✗ [shakeout-revert] AF-3 and AF-1: two new rows share one test",)),
        _case("test_redriven_rows_may_share_a_file: five re-driven rows on a file of an earlier feature pass with no log",
              HEAD + BROWSER.format(EVIDENCE) + P_ROWS + HUNT, MIXED_PNGS, rc=0, registry=REGISTRY + PRODUCTIONS,
              has=("✓ [shakeout-revert]", "5 re-driven")),
        _case("test_new_test_in_an_older_file_needs_its_proof: a file registered under an older feature AND this one is new",
              HEAD + BROWSER.format(EVIDENCE) + NEW_ROW + HUNT, PNG, registry=MIXED_REGISTRY,
              has=(f"✗ [shakeout-revert] AF-6: no revert log at shakeout/{NEW_STEM}.revert.txt",)),
        _case("test_redriven_row_in_a_mixed_file_is_exempt_by_git: five titles in the base's copy are re-driven, the sixth owes its proof → PASS",
              MIXED, MIXED_PNGS, rc=0, registry=MIXED_REGISTRY, logs=MIXED_LOGS, base=BASE_FIVE, files=ON_BRANCH,
              has=("✓ [shakeout-revert]", "2 new row", "5 re-driven")),
        _case("…and without the sixth's log only AF-6 is refused",
              MIXED, MIXED_PNGS, registry=MIXED_REGISTRY, logs=LOGS, base=BASE_FIVE, files=ON_BRANCH,
              has=("✗ [shakeout-revert] AF-6: no revert log",), lacks=("P-1:", "P-2:", "P-3:", "P-4:", "P-5:")),
        _case("test_redriven_is_read_from_the_registry_not_the_word: `Re-driven` in Evidence excuses nothing",
              DRIVEN.replace(TEST_B, f"Re-driven · {TEST_B}"), PNG, logs={k: v for k, v in LOGS.items() if STEM_W in k},
              has=("✗ [shakeout-revert] AF-1: no revert log",)),
        _case("test_unregistered_test_counts_as_new", HEAD + WIRE_PASS.replace("AuditRestTest.php", "OtherTest.php"),
              has=("✗ [shakeout-revert] AF-2: no revert log at shakeout/tests__integration__OtherTest.php--testlistreturnsrows.revert.txt",)),
        _case("test_test_marker_survives_accepted_by_human_order: Test: first, the human's reason is only his words",
              HEAD + BROWSER.format(f"{TEST_B} · Accepted-by-human: no browser on this box") + WIRE_PASS + NO_HUNT, rc=0,
              has=("[shakeout-accepted] AF-1: accepted by the human — no browser on this box",), lacks=("— Test:",)),
        _case("test_password_in_a_test_file_name_is_not_a_credential", DRIVEN.replace(EVIDENCE, PW_EVIDENCE), PNG, rc=0,
              logs=PW_LOGS, lacks=("shakeout-credential",)),
        _case("test_accepted_by_human_excuses_a_missing_revert",
              HEAD + BROWSER.format(f"{TEST_B} · Accepted-by-human: schema changed, the base cannot seed") + WIRE_PASS + NO_HUNT, rc=0,
              logs={k: v for k, v in LOGS.items() if STEM_W in k}, lacks=("✗ [shakeout-revert]",)),
        _case("test_cli_row_needs_no_revert", HEAD + "| AF-2 | wp cli lists | cli | pass | ddev wp audit list → 3 rows |\n", rc=0,
              logs={}, lacks=("shakeout-revert",)),
        _case("test_credential_in_a_revert_log_fails", DRIVEN, PNG,
              logs={**LOGS, f"shakeout/{STEM_B}.revert.txt": _log(command="E2E_PASS=s3cr3tPw npx playwright test")},
              has=("✗ [shakeout-credential]", f"{STEM_B}.revert.txt"), lacks=("s3cr3tPw",)),
        _case("test_stem_is_shared_with_revert_run: the checker derives the name the script writes", DRIVEN.replace(EVIDENCE, ODD_EVIDENCE),
              PNG, rc=0, logs=ODD_LOGS, has=("✓ [shakeout-revert]",)),
        # R9 — a PIN (green before this feature): only `shakeout/<name>.png` is a screenshot path
        _case("test_scratchpad_screenshot_path_fails",
              DRIVEN.replace("shakeout/af-1.png", "/tmp/claude-1000/-home-x/abc/scratchpad/af-1.png"), PNG,
              has=("must be `shakeout/<name>.png`",)),
    ]
    r += [_case(f"credential `{label}` → FAIL shakeout-credential", m, PNG, has=("✗ [shakeout-credential]",))
          for label, m in CREDENTIALS.items()]
    r += [_case(f"`{label}` is not a credential", m, PNG, rc=0, lacks=("shakeout-credential",))
          for label, m in NOT_CREDENTIALS.items()]
    return r
