#!/usr/bin/env python3
"""shakeout-check.py — the shake-out manifest gate.

    shakeout-check.py <feature dir>

Reads <feature dir>/shakeout.md and exits 0 only when every row passes on evidence a file can
prove, never on the verdict word: a `browser` row needs `Browser: <http url> · <png>` with a
real 1 KB–2 MB PNG under the feature dir; every `browser` and `wire` row names its one test,
`Test: <path> :: <title>`, first in Evidence, and a NEW test is proven by its revert log
(`shakeout/<stem>.revert.txt`, revert-run's own output: its `test:` line is the row's test, its
`base:` the current merge-base, `assertion-failed` with a non-zero `exit:`); a manifest with a
browser row records its hunt (`Hunt: <n> charters …`, or `Hunt: deferred — …` on an intermediate
slice); the whole file (the `Test:` path excepted) and every revert log's command and excerpt are
scanned for credentials with no override; only the human's `Accepted-by-human:` excuses a row.

New or re-driven is decided by git, never by a word in the row: a title the base's copy of the file
(`git show <base>:<path>`) already carries as a test call — `test(`, `it(`, their modifiers, a PHPUnit
method — is re-driven and exempt, every other title is new, and a file absent from the base makes
every row new. Only a root that is not a repository falls back to `specs/CHECKS.md`: a file named
only by rows of earlier features is re-driven, any other file new. Bare python3.
"""
from __future__ import annotations

import functools
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

BROWSER_EVIDENCE = re.compile(r"Browser:\s*(?P<url>https?://\S+)\s*·\s*(?P<path>\S+)")
ACCEPTED = re.compile(r"Accepted-by-human:\s*(?P<reason>.+)")
# The words the plan names, then every value the recipe or a session can mint: app
# passwords (the command, the 6×4 value — case-sensitive so six short words are not one),
# basic auth in a flag or a URL, the WP session cookie, a password in a POST body or env,
# bearer/JWT/JSON tokens, the login page, and `wp login create`'s magic link
# (`/<8 hex>/<6-10 hex>-<6-10 hex>-<6-10 hex>`, per aaemnnosttv/wp-cli-login-command).
CREDENTIAL = re.compile(
    r"login=|token=|app(?:lication)?[-_ ]?password|storage[_-]?state"
    r"|(?-i:(?![a-z ]{29})\b(?:[A-Za-z0-9]{4} ){5}[A-Za-z0-9]{4}\b)"
    r"|(?<![\w-])(?:-u|--user)[\s=]*\S+:\S+|\buser(?:name)?:\s*\S+:\S+|https?://[^\s/@|]+:[^\s/@|]+@"
    r"|wordpress(?:_logged_in|_sec)?_[0-9a-f]{32}"
    r"|\b(?:pwd|passw(?:or)?d|user_pass|[A-Z0-9_]*_PASS(?:WORD)?)\s*[=:]\s*\S+"
    r"|Authorization:\s*(?:Basic|Bearer)\s+\S+|\bBasic\s+[A-Za-z0-9+/=]{16,}"
    r"|\bBearer\s+[A-Za-z0-9._~+/-]{20,}|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"
    r"|\"?(?:access_)?token\"?\s*:\s*\"?\S+"
    r"|wp-login\.php\?[^ |]*"
    r"|https?://\S+/[0-9a-f]{8}/[0-9a-f]{6,10}-[0-9a-f]{6,10}-[0-9a-f]{6,10}\b",
    re.IGNORECASE)
LAYERS = ("browser", "wire", "cli")
COLUMNS = {"n": "#", "flow": "Flow", "layer": "Layer", "verdict": "Verdict", "evidence": "Evidence"}
TABLE_ROW = re.compile(r"^\s*\|(?P<cells>.*\|)\s*$")
TABLE_SEPARATOR = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
SCREENSHOT_BYTES = (1024, 2 * 1024 * 1024)
HUNT = re.compile(r"^Hunt: (?:0 charters [—-] \S|deferred [—-] \S|[1-9]\d* charters? · \d+ confirmed · \d+ not ours · \d+ rejected\b)")

Finding = tuple[str, str, str]  # (status, check, detail)


def _unfenced(text: str) -> list[str]:
    out, in_fence = [], False
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            out.append(ln)
    return out


def _cells(line: str) -> list[str] | None:
    m = TABLE_ROW.match(line)
    return [c.strip() for c in m.group("cells").rstrip("|").split("|")] if m else None


def parse_rows(text: str) -> list[dict]:
    """Rows of the first pipe table whose header names a `#` column."""
    lines = _unfenced(text)
    index, rows = None, []
    for i, ln in enumerate(lines):
        if TABLE_SEPARATOR.match(ln):
            continue
        cells = _cells(ln)
        if index is None:
            if cells and "#" in cells and i + 1 < len(lines) and TABLE_SEPARATOR.match(lines[i + 1]):
                names = [c.lower() for c in cells]
                index = {k: names.index(h.lower()) if h.lower() in names else None
                         for k, h in COLUMNS.items()}
            continue
        if cells is None:
            break
        rows.append({k: (cells[j] if j is not None and j < len(cells) else "")
                     for k, j in index.items()})
    return [r for r in rows if any(r.values())]


def _table_rows(text: str) -> int:
    """Data rows of every pipe table in the file, header lines excluded."""
    cells = [c for c in (_cells(ln) for ln in _unfenced(text) if not TABLE_SEPARATOR.match(ln)) if c is not None]
    return sum(1 for c in cells if "#" not in c)


def _screenshot_problem(path: str, spec_dir: Path) -> str | None:
    if not (path.startswith("shakeout/") and path.endswith(".png")):
        return f"screenshot `{path}` must be `shakeout/<name>.png`"
    try:
        target = (spec_dir / path).resolve()
        if not (target.is_file() and target.is_relative_to(spec_dir.resolve())):
            return f"screenshot `{path}` not found under the feature dir"
        size = target.stat().st_size
        if not SCREENSHOT_BYTES[0] <= size <= SCREENSHOT_BYTES[1]:
            return f"screenshot `{path}` is {size} bytes — a viewport PNG is 1 KB to 2 MB"
        with target.open("rb") as fh:
            magic = fh.read(8)
    except (OSError, ValueError) as e:
        return f"screenshot `{path!r}` could not be read ({e.__class__.__name__})"
    return None if magic == PNG_MAGIC else f"screenshot `{path}` does not open with the PNG magic"


def _row_problem(row: dict, spec_dir: Path) -> str | None:
    layer, verdict, evidence = row["layer"].lower(), row["verdict"].lower(), row["evidence"]
    if not row["n"]:
        return "row without a # cell"
    if layer not in LAYERS:
        return f"layer `{row['layer']}` is not one of {', '.join(LAYERS)}"
    if layer != "browser":
        return None if verdict == "pass" else f"{layer} row verdict `{row['verdict']}` — not a pass"
    if verdict != "pass":
        return f"browser row verdict `{row['verdict']}` — not driven"
    m = BROWSER_EVIDENCE.search(evidence)
    if not m:
        return "browser row without `Browser: <http url> · <screenshot path>` evidence"
    return _screenshot_problem(m.group("path"), spec_dir)


def _hunt_finding(text: str, rows: list[dict]) -> Finding | None:
    """A manifest with a browser row records its hunt: the tally, or why it could not run."""
    if not any(row["layer"].lower() == "browser" for row in rows):
        return None
    tally = next((ln.rstrip() for ln in _unfenced(text) if HUNT.match(ln)), None)
    if tally is None:
        return ("fail", "shakeout-hunt", "browser rows but no hunt line at the start of a line under the table — "
                                         "`Hunt: <n> charters · <c> confirmed · <x> not ours · <r> rejected`, "
                                         "or `Hunt: 0 charters — <why>`")
    return ("pass", "shakeout-hunt", "Hunt line recorded" if CREDENTIAL.search(tally) else tally)


# ── the checks registry ───────────────────────────────────────────────────────
# `specs/CHECKS.md` indexes what the shake-outs left to run on a deployed site:
# `| surface | tier | entry | test | first feature | verified |`. Tier `e2e` is a
# driven flow tagged `@e2e` (make e2e, staging only); `smoke` is read-only and
# tagged `@smoke` (make smoke, production too); `auth` is listed for a later runner
# and owes no test. A feature that drove flows leaves an e2e row and a smoke row.
REGISTRY_COLUMNS = {"surface": "surface", "tier": "tier", "entry": "entry", "test": "test",
                    "feature": "first feature", "verified": "verified"}
TIER_TAG = {"e2e": "@e2e", "smoke": "@smoke"}
TIERS = (*TIER_TAG, "auth")


def parse_registry(text: str) -> list[dict]:
    lines = _unfenced(text)
    index, rows = None, []
    for i, ln in enumerate(lines):
        if TABLE_SEPARATOR.match(ln):
            continue
        cells = _cells(ln)
        if index is None:
            if cells and "surface" in [c.lower() for c in cells] and i + 1 < len(lines) \
                    and TABLE_SEPARATOR.match(lines[i + 1]):
                names = [c.lower() for c in cells]
                index = {k: names.index(h) if h in names else None for k, h in REGISTRY_COLUMNS.items()}
            continue
        if cells is None:
            break
        rows.append({k: (cells[j] if j is not None and j < len(cells) else "")
                     for k, j in index.items()})
    return [r for r in rows if any(r.values())]


def _registry_row_problem(row: dict, root: Path) -> str | None:
    tier = row["tier"].lower()
    if tier not in TIERS:
        return f"tier {row['tier'] or '(none)'} is not one of {', '.join(TIERS)}"
    if tier == "auth":
        return None
    test = row["test"].strip("`")
    path = root / test
    if not test or not path.is_file():
        return f"test {test or '(none)'} does not exist — a registry row with no test checks nothing"
    try:
        tagged = TIER_TAG[tier] in path.read_text()
    except (OSError, ValueError):
        tagged = False
    if not tagged:
        return f"{test} carries no {TIER_TAG[tier]} tag — make {tier} never runs it"
    return None


def _registry_rows(spec_dir: Path) -> list[dict]:
    registry = spec_dir.parent / "CHECKS.md"
    return parse_registry(registry.read_text()) if registry.is_file() else []


def check_registry(spec_dir: Path, driven: int, rows: list[dict]) -> list[Finding]:
    """The registry rows this feature owes and the tests those rows name."""
    findings: list[Finding] = []
    for row in rows:
        problem = _registry_row_problem(row, spec_dir.parent.parent)
        if problem:
            findings.append(("fail", "checks-registry", f"{row['surface']}: {problem}"))
    if driven:
        mine = {r["tier"].lower() for r in rows if r["feature"] == spec_dir.name}
        for tier in TIER_TAG:
            if tier not in mine:
                findings.append(("fail", "checks-registry",
                                 f"{spec_dir.name} drove {driven} flow(s) and left no {tier} row in specs/CHECKS.md"
                                 f" — make {tier} would not watch it after a deploy"))
    if rows and not any(s == "fail" for s, _, _ in findings):
        findings.append(("pass", "checks-registry",
                         f"{len(rows)} row{'s' if len(rows) != 1 else ''}, every test present and tagged for its tier"))
    return findings


# ── the revert proof ──────────────────────────────────────────────────────────
# `Test: <path> :: <title>` keys a row to its one test; its log is derived, never pointed at.
TEST = re.compile(r"Test:\s*(?P<path>\S+)\s*::\s*(?P<title>[^·]+?)\s*(?:·|$)")
TEST_PATH = re.compile(r"(Test:\s*)\S+")
LOG_VERDICT = {"assertion-failed": None,
               "passed": "shows the test passing on the base (`revert-run: passed`) — it cannot fail without the feature",
               "error": "is an error run (`revert-run: error`: a timeout, an unmatched locator, a login or a seeding error), not an assertion failure"}


def stem(path: str, title: str) -> str:
    """The log name revert-run writes: the path with / as __, then --, then the title slugged."""
    slug = re.sub(r"[^a-z0-9]+", "-", re.sub(r"[A-Z]", lambda m: m.group(0).lower(), title))
    return f"{path.replace('/', '__')}--{slug}"


def _git(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


@functools.lru_cache(maxsize=None)
def _base(root: Path) -> str | None:
    """The merge-base of HEAD with production's branch, resolved as revert-run resolves it."""
    site, branch = root / "scripts" / "site", None
    if os.access(site, os.X_OK):
        try:
            branch = subprocess.run([str(site), "environments.production.branch"], cwd=root,
                                    capture_output=True, text=True, timeout=30).stdout.strip() or None
        except (OSError, subprocess.SubprocessError):
            branch = None
    for b in (branch, "main", "master"):
        for ref in ((f"origin/{b}", b) if b else ()):
            if _git(root, "rev-parse", "-q", "--verify", f"{ref}^{{commit}}") is not None:
                out = _git(root, "merge-base", ref, "HEAD")
                return out.strip() if out else None
    return None


@functools.lru_cache(maxsize=None)
def _base_copy(root: Path, path: str) -> str | None:
    base = _base(root)
    return _git(root, "show", f"{base}:{path}") if base else None


def _test_call(title: str) -> re.Pattern:
    """The title as a test call: `test(`, `it(` and their modifiers (never `describe`), or a PHPUnit method."""
    t = re.escape(title)
    return re.compile(rf"\b(?:test|it)(?:\.(?!describe\b)\w+)*\s*\(\s*['\"`]{t}['\"`]|\bfunction\s+{t}\s*\(")


def row_is_redriven(root: Path, path: str, title: str, registry: list[dict], feature: str) -> bool:
    """Git decides whenever it holds the base: a title the base's copy of the file already carries as
    a test call is re-driven, any other title is new, a file absent from the base is all new. Only
    without a repository does the registry decide: a file registered under earlier features alone."""
    if _base(root) is None:
        features = {r["feature"] for r in registry if r["test"].strip("`") == path}
        return bool(features) and feature not in features
    text = _base_copy(root, path)
    return bool(text) and _test_call(title).search(text) is not None


def _log_head(lines: list[str]) -> dict[str, str]:
    """The `key: value` lines above `--- output:`, the first of each key."""
    head: dict[str, str] = {}
    for ln in lines:
        if ln.startswith("--- output:"):
            break
        key, sep, value = ln.partition(":")
        if sep:
            head.setdefault(key, value.strip())
    return head


def log_problem(spec_dir: Path, root: Path, path: str, title: str) -> str | None:
    """Why the row's revert log proves nothing, or None. The log is revert-run's own output: its
    `test:` line is this row's test, its `base:` the current merge-base, `assertion-failed` ends
    with a non-zero `exit:` — a copied or hand-written log fails here."""
    log = spec_dir / "shakeout" / f"{stem(path, title)}.revert.txt"
    if not log.is_file():
        return f"no revert log at shakeout/{log.name} — run revert-run for `{path} :: {title}`"
    try:
        lines = log.read_text().splitlines()
    except (OSError, ValueError) as e:
        return f"{log.name} could not be read ({e.__class__.__name__})"
    head = _log_head(lines)
    cls = head.get("revert-run", "")
    if not lines or not lines[0].startswith("revert-run: ") or cls not in LOG_VERDICT:
        return f"{log.name} has no `revert-run: <class>` first line"
    if head.get("test") != f"{path} :: {title}":
        return f"{log.name} is the log of `{head.get('test', '?')}`, not of `{path} :: {title}` — a proof is revert-run's own output"
    base, logged = _base(root), head.get("base", "").split(" ")[0]
    if base and not (len(logged) >= 7 and base.startswith(logged)):
        return f"{log.name} was run on base {logged or '?'}, the merge-base is now {base[:7]} — run revert-run again"
    if LOG_VERDICT[cls]:
        return f"{log.name} {LOG_VERDICT[cls]}"
    if head.get("exit", "0") == "0":
        return f"{log.name} says assertion-failed with exit 0 — not revert-run's output"
    return None


def _unescaped(words: str) -> str:
    try:
        return " ".join(shlex.split(words))
    except ValueError:
        return words


def _log_credential_lines(lines: list[str]) -> list[int]:
    """The lines of a revert log that carry a credential: the command, un-escaped from revert-run's
    `%q`, and the output excerpt — never the header's paths (the manifest scan covers the title)."""
    hits, in_output = [], False
    for i, ln in enumerate(lines, 1):
        if ln.startswith("--- output:"):
            in_output = True
        elif ln.startswith("command:"):
            ln = _unescaped(ln[len("command:"):])
        elif not in_output:
            continue
        if CREDENTIAL.search(ln):
            hits.append(i)
    return hits


def check_logs(spec_dir: Path) -> list[Finding]:
    """Every revert log is committed, so every one is scanned — a row's or an orphan's."""
    shakeout = spec_dir / "shakeout"
    findings: list[Finding] = []
    for log in sorted(shakeout.glob("*.revert.txt")) if shakeout.is_dir() else []:
        try:
            lines = log.read_text().splitlines()
        except (OSError, ValueError):
            continue
        findings += [("fail", "shakeout-credential", f"{log.name} line {i}: carries a credential — the log is committed")
                     for i in _log_credential_lines(lines)]
    return findings


def check_revert(spec_dir: Path, rows: list[dict], registry: list[dict]) -> list[Finding]:
    """Every browser and wire row names its test; each new one owns an assertion-failed revert log."""
    root = spec_dir.parent.parent
    findings: list[Finding] = []
    keys: dict[tuple[str, str], str] = {}
    new = redriven = 0
    for row in rows:
        n = row["n"] or "?"
        if row["layer"].lower() not in ("browser", "wire") or ACCEPTED.search(row["evidence"]):
            continue
        m = TEST.search(row["evidence"])
        if not m:
            findings.append(("fail", "shakeout-revert",
                             f"{n}: no `Test: <path> :: <title>` in Evidence — every browser and wire row names its one test, first"))
            continue
        path, title = m.group("path").strip("`"), m.group("title").strip()
        if CREDENTIAL.search(title):
            findings.append(("fail", "shakeout-revert", f"{n}: the test title carries a credential — rename the test (the title is the log's name)"))
            continue
        if row_is_redriven(root, path, title, registry, spec_dir.name):
            redriven += 1
            continue
        new += 1
        if (path, title) in keys:
            findings.append(("fail", "shakeout-revert", f"{n} and {keys[path, title]}: two new rows share one test `{path} :: {title}`"))
            continue
        keys[path, title] = n
        problem = log_problem(spec_dir, root, path, title)
        if problem:
            findings.append(("fail", "shakeout-revert", f"{n}: {problem}"))
    if (new or redriven) and not any(s == "fail" and c == "shakeout-revert" for s, c, _ in findings):
        findings.append(("pass", "shakeout-revert", f"{new} new row(s) proven on the base, {redriven} re-driven"))
    return findings


def check(spec_dir: Path) -> list[Finding]:
    if not spec_dir.is_dir():
        return [("fail", "shakeout-manifest", f"{spec_dir} is not a directory")]
    manifest = spec_dir / "shakeout.md"
    if not manifest.exists():
        return [("fail", "shakeout-manifest", "no shakeout.md — a user-facing change owes a manifest")]
    try:
        text = manifest.read_text()
    except (OSError, ValueError) as e:
        return [("fail", "shakeout-manifest", f"shakeout.md could not be read ({e.__class__.__name__})")]
    findings: list[Finding] = [
        ("fail", "shakeout-credential", f"line {i}: carries a credential — the whole file is committed")
        for i, ln in enumerate(text.splitlines(), 1) if CREDENTIAL.search(TEST_PATH.sub(r"\1", ln))]
    rows = parse_rows(text)
    if not rows:
        return findings + [("fail", "shakeout-manifest",
                            "shakeout.md has no rows — a manifest that lists no flow proves nothing")]
    outside = _table_rows(text) - len(rows)
    if outside > 0:
        findings.append(("fail", "shakeout-manifest",
                         f"{outside} table row(s) outside the table shakeout.md's header opens — every flow row sits in one table"))
    driven = 0
    for row in rows:
        problem = _row_problem(row, spec_dir)
        accepted = ACCEPTED.search(row["evidence"])
        if accepted:
            reason = "" if CREDENTIAL.search(row["evidence"]) else f" — {accepted.group('reason').strip()}"
            findings.append(("pass", "shakeout-accepted", f"{row['n']}: accepted by the human{reason}"))
        elif problem:
            findings.append(("fail", "shakeout-manifest", f"{row['n'] or '?'}: {problem}"))
        driven += row["layer"].lower() == "browser" and problem is None
    findings.append(("pass", "shakeout-manifest", f"shakeout: {len(rows)} rows, {driven} browser rows driven"))
    registry = _registry_rows(spec_dir)
    findings += check_revert(spec_dir, rows, registry) + check_logs(spec_dir)
    hunt = _hunt_finding(text, rows)
    if hunt:
        findings.append(hunt)
    passed = sum(1 for row in rows if _row_problem(row, spec_dir) is None)
    findings += check_registry(spec_dir, passed, registry)
    return findings


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: shakeout-check.py <feature dir>", file=sys.stderr)
        return 2
    findings = check(Path(argv[0]))
    for status, name, detail in findings:
        print(f"  {'✓' if status == 'pass' else '✗'} [{name}] {detail}")
    failed = any(s == "fail" for s, _, _ in findings)
    print(f"\nSHAKEOUT: {'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
