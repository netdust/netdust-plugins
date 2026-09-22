#!/usr/bin/env python3
"""shakeout-check.py — the shake-out manifest gate.

    shakeout-check.py <feature dir>

Reads <feature dir>/shakeout.md and exits 0 only when every row passes on evidence a file can
prove, never on the verdict word: a `browser` row needs `Browser: <http url> · <png>` with a
real 1 KB–2 MB PNG under the feature dir; the whole file is scanned for credentials with no
override; only the human's `Accepted-by-human:` excuses a row. Bare python3.
"""
from __future__ import annotations

import re
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


# ── the smoke registry ────────────────────────────────────────────────────────
# `specs/SMOKE.md` indexes the read-only checks `make smoke env=E` runs against a
# deployed site: `| surface | entry | test | first feature | verified |`. A row's
# test is a committed spec tagged `@smoke`; an entry marked `auth` is listed for a
# later runner and owes no tag. A feature that drove flows leaves at least one row.
REGISTRY_COLUMNS = {"surface": "surface", "entry": "entry", "test": "test",
                    "feature": "first feature", "verified": "verified"}


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


def check_registry(spec_dir: Path, driven: int) -> list[Finding]:
    """The registry rows this feature owes and the tests those rows name."""
    registry = spec_dir.parent / "SMOKE.md"
    root = spec_dir.parent.parent
    feature = spec_dir.name
    rows = parse_registry(registry.read_text()) if registry.is_file() else []
    findings: list[Finding] = []
    for row in rows:
        if row["entry"].lower().startswith("auth"):
            continue
        test = row["test"].strip("`")
        path = root / test
        if not test or not path.is_file():
            findings.append(("fail", "smoke-registry",
                             f"{row['surface']}: test {test or '(none)'} does not exist — a registry row with no test checks nothing"))
            continue
        try:
            tagged = "@smoke" in path.read_text()
        except (OSError, ValueError):
            tagged = False
        if not tagged:
            findings.append(("fail", "smoke-registry",
                             f"{row['surface']}: {test} carries no @smoke tag — make smoke never runs it"))
    mine = [r for r in rows if r["feature"] == feature]
    if driven and not mine:
        findings.append(("fail", "smoke-registry",
                         f"{feature} drove {driven} flow(s) and left no row in specs/SMOKE.md — the deployed site would go unwatched"))
    if rows and not any(s == "fail" for s, _, _ in findings):
        findings.append(("pass", "smoke-registry", f"{len(rows)} row{'s' if len(rows) != 1 else ''}, every test present and tagged"))
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
        for i, ln in enumerate(text.splitlines(), 1) if CREDENTIAL.search(ln)]
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
    passed = sum(1 for row in rows if _row_problem(row, spec_dir) is None)
    findings += check_registry(spec_dir, passed)
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
