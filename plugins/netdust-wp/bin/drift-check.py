#!/usr/bin/env python3
"""
drift-check — the MECHANICAL half of NTDST framework conformance.

Every rule here is one a grep can decide. They used to live only as prose in
`ntdst-architecture/references/anti-patterns.md` and as an optional review
someone had to remember to invoke (`ntdst-drift-reviewer`). Measured across 13
consumer projects, that did not bind: 13/13 hand-roll `get_post_meta()`/
`get_posts()`, 11/13 hand-roll `ob_start()`, 5/13 call `register_taxonomy()`
directly, 4/13 register raw `wp_ajax_*` handlers — all while the framework
provided each one and the docs described it accurately.

Accuracy was never the binding constraint. Enforcement is. So:

    if a grep can decide it, it is a gate, not a paragraph.

Judgement calls are NOT here on purpose — "is this raw meta read a legitimate
batch path?" is not grep-decidable and stays in the skill, with its
rationalization table. This script only flags what is mechanically wrong.

USAGE
    drift-check.py                     # staged PHP files (pre-commit)
    drift-check.py --since HEAD~1      # files changed since a ref
    drift-check.py path/ file.php      # explicit scope
    drift-check.py --json              # machine-readable, for an agent/hook

EXIT CODES
    0  clean (or nothing in scope)
    1  findings present
    2  bad invocation

ESCAPE HATCH — deliberate, documented, greppable.
Put a pragma on the offending line or the line above it:

    // ntdst-allow: raw-meta — batch enrichment, N+1 otherwise (see lessons.md)

An allow WITHOUT a reason after the em-dash/hyphen is itself a finding: the
point is a reviewable justification, not a mute button.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

SKIP_DIRS = {"vendor", "node_modules", "wp", ".git", "dist", "build", "wp-content/uploads"}
SKIP_FILE_RE = re.compile(r"(^|/)(tests?|Tests?)/|Test\.php$|Cest\.php$|\.min\.php$")

# The framework itself is exempt from all of it. ntdst-core IS the implementation
# of the data layer, the router and the renderer — it necessarily calls
# get_post_meta(), register_post_type() and ob_start(), and flagging those would
# be flagging the correct answer. These rules govern CONSUMERS of the framework.
FRAMEWORK_RE = re.compile(r"(^|/)ntdst-core/")

# Files where a pattern is the CORRECT home rather than drift.
REPO_RE = re.compile(r"Repository\.php$")
CPT_RE = re.compile(r"(CPT|PostType)\.php$")

ALLOW_RE = re.compile(r"ntdst-allow:\s*([a-z0-9-]+)\s*(?:[—–-]\s*(.+))?", re.I)


class Check:
    def __init__(self, key, pattern, message, fix, exempt=None, flags=0, window=1, absolve=None):
        self.key = key
        self.re = re.compile(pattern, flags)
        self.message = message
        self.fix = fix
        self.exempt = exempt or (lambda path: False)
        # How many lines (including this one) to join before deciding. A call
        # split across lines is the normal formatting of a prepared query, and a
        # gate that cannot read it produces false positives — which is how gates
        # lose their credibility and get switched off.
        self.window = window
        # Given the joined window, return True when the hit is actually fine.
        self.absolve = absolve or (lambda text: False)


CHECKS = [
    Check(
        "repo-bypass",
        r"ntdst_data\(\)\s*->\s*get\s*\(",
        "CPT data access outside its repository",
        "inject the domain's Repository; ntdst_data()->get() belongs in exactly one file per post type",
        exempt=lambda p: bool(REPO_RE.search(p)),
    ),
    Check(
        "raw-meta",
        r"\b(get_post_meta|update_post_meta|add_post_meta|delete_post_meta)\s*\(",
        "raw post-meta call bypassing the Data layer",
        "use the model's field accessors via the repository (getField/findFields/update)",
        exempt=lambda p: bool(REPO_RE.search(p)),
    ),
    Check(
        "raw-post-write",
        r"\b(wp_insert_post|wp_update_post|wp_delete_post)\s*\(",
        "raw post write bypassing the Data layer",
        "use the model's create()/update()/delete() through the repository",
        exempt=lambda p: bool(REPO_RE.search(p)),
    ),
    Check(
        "raw-ajax",
        r"add_action\s*\(\s*['\"]wp_ajax(_nopriv)?_",
        "raw wp_ajax_* handler — bypasses nonce, origin, rate-limit and the capability floor",
        "register with ntdst_api_action($action, $handler, $opts)",
    ),
    Check(
        "raw-api-filter",
        r"add_filter\s*\(\s*['\"]ntdst/api_data/",
        "API action registered by raw filter — forfeits the declared capability floor and the public allow-list",
        "register with ntdst_api_action($action, $handler, $opts)",
    ),
    Check(
        "ob-start",
        r"\bob_start\s*\(",
        "hand-rolled output buffering for template rendering",
        "NTDST_Template_Loader::page() / ntdst_response()->render() / ->html()",
    ),
    Check(
        "raw-register-type",
        r"\b(register_post_type|register_taxonomy)\s*\(",
        "post type / taxonomy registered outside the Data layer wrapper",
        "ntdst_data()->register($name, $config) — taxonomies go in its `taxonomies` key",
        exempt=lambda p: bool(REPO_RE.search(p) or CPT_RE.search(p)),
    ),
    Check(
        "manual-template-include",
        r"add_filter\s*\(\s*['\"]template_include['\"]",
        "manual template_include filter bypassing the Router",
        "ntdst_router()->template()/single()/archive()",
    ),
    Check(
        "hardcoded-meta-prefix",
        r"['\"]_ntdst_[a-z0-9_]*['\"]",
        "hardcoded meta prefix",
        "read it from the model: $repo->getMetaPrefix() . 'field'",
        exempt=lambda p: bool(REPO_RE.search(p) or CPT_RE.search(p)),
    ),
    Check(
        "wp-column-vocabulary",
        r"['\"]post_(title|content|excerpt)['\"]\s*=>",
        "raw wp_posts column name passed to the Data API — silently dropped, may land in meta",
        "use the friendly vocabulary: title / content / excerpt",
        exempt=lambda p: bool(REPO_RE.search(p)),
    ),
    Check(
        "permission-true",
        r"['\"]permission_callback['\"]\s*=>\s*['\"]__return_true['\"]",
        "REST route open to everyone",
        "supply a real permission callback; a public-by-design route states its own explicit callable",
    ),
    Check(
        "unprepared-sql",
        r"\$wpdb\s*->\s*(query|get_results|get_row|get_var|get_col)\s*\(",
        "$wpdb call with no $wpdb->prepare() on it",
        "always $wpdb->prepare(); if the SQL is genuinely constant, annotate it",
        # A prepared query is routinely wrapped across lines; read the whole call
        # before judging it.
        window=3,
        absolve=lambda text: "->prepare(" in text,
    ),
]

CHECKS_BY_KEY = {c.key: c for c in CHECKS}


def in_scope(path: str) -> bool:
    if not path.endswith(".php"):
        return False
    parts = set(path.split(os.sep))
    if parts & SKIP_DIRS:
        return False
    if FRAMEWORK_RE.search(path.replace(os.sep, "/")):
        return False
    return not SKIP_FILE_RE.search(path)


def git_files(args) -> list[str]:
    if args.since:
        cmd = ["git", "diff", "--name-only", "--diff-filter=ACMR", args.since]
    else:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [f for f in out.splitlines() if f.strip()]


def collect(paths: list[str]) -> list[str]:
    found = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                found += [os.path.join(root, f) for f in files]
        else:
            found.append(p)
    return [f for f in found if in_scope(f) and os.path.isfile(f)]


def allowed(lines: list[str], idx: int, key: str):
    """Return (is_allowed, reason_or_None, malformed) for a pragma on this or the previous line."""
    for probe in (idx, idx - 1):
        if probe < 0:
            continue
        m = ALLOW_RE.search(lines[probe])
        if m and m.group(1).lower() == key:
            reason = (m.group(2) or "").strip()
            return True, reason or None, not reason
    return False, None, False


def scan(files: list[str]) -> list[dict]:
    findings = []
    for path in files:
        try:
            lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("*", "//", "#")):
                continue  # comments and docblocks are not code
            for chk in CHECKS:
                if chk.exempt(path) or not chk.re.search(line):
                    continue
                if chk.window > 1:
                    if chk.absolve(" ".join(lines[i:i + chk.window])):
                        continue
                ok, reason, malformed = allowed(lines, i, chk.key)
                if ok and not malformed:
                    continue
                findings.append({
                    "file": path,
                    "line": i + 1,
                    "check": chk.key,
                    "message": ("`ntdst-allow` with no reason — an allow needs a justification"
                                if malformed else chk.message),
                    "fix": chk.fix,
                    "code": stripped[:140],
                })
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Mechanical NTDST framework-drift gate.")
    ap.add_argument("paths", nargs="*", help="files or directories (default: staged PHP files)")
    ap.add_argument("--since", metavar="REF", help="scan files changed since REF instead of the index")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--list-checks", action="store_true", help="print check keys and exit")
    args = ap.parse_args()

    if args.list_checks:
        for c in CHECKS:
            print(f"{c.key:24} {c.message}")
        return 0

    files = collect(args.paths) if args.paths else collect(git_files(args))
    if not files:
        if args.json:
            print(json.dumps({"scanned": 0, "findings": []}))
        else:
            print("drift-check: nothing in scope.")
        return 0

    findings = scan(files)

    if args.json:
        print(json.dumps({"scanned": len(files), "findings": findings}, indent=2))
        return 1 if findings else 0

    if not findings:
        print(f"drift-check: {len(files)} file(s) scanned — clean.")
        return 0

    # Group by (check, message): a malformed `ntdst-allow` carries a different
    # message from a plain hit, and folding them under one header would print a
    # reason that does not apply to half the lines under it.
    by_check: dict[tuple[str, str], list[dict]] = {}
    for f in findings:
        by_check.setdefault((f["check"], f["message"]), []).append(f)

    print(f"drift-check: {len(findings)} finding(s) across {len(files)} file(s)\n")
    for (key, message), group in sorted(by_check.items(), key=lambda kv: -len(kv[1])):
        print(f"■ {key} — {message}")
        print(f"  → {group[0]['fix']}")
        for f in group[:12]:
            print(f"    {f['file']}:{f['line']}  {f['code']}")
        if len(group) > 12:
            print(f"    … and {len(group) - 12} more")
        print()

    print("If a hit is a deliberate, documented exception, annotate the line:")
    print("    // ntdst-allow: <check-key> — <why this is correct here>")
    print("An allow without a reason is itself a finding.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
