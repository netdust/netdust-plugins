"""
test_skill_audit_glob.py — verifies skill-audit and red-test command globs
actually match real skill directories.

The audit found that `/skill-audit` and `/red-test` referenced the glob
`~/.claude/plugins/netdust-wp/skills/_*/*/` — a glob that matched ZERO
directories on this machine (the `_*` was a typo or legacy convention,
real skill dirs have no underscore prefix). The commands had been silently
broken since they were written.

This test reads the command markdown files, extracts the globs they
document, runs each glob, and asserts it expands to a non-empty list.
"""

import glob
import os
import re
from pathlib import Path

COMMANDS_DIR = Path(__file__).parent.parent / "commands"


def _extract_skill_globs(md_text: str) -> list[str]:
    """Pull every shell-style glob path that mentions a netdust plugin's
    skills directory. Matches both ~/.claude/... and ${HOME}/.claude/...
    forms. Returns unique paths."""
    pattern = re.compile(
        r"(?:~|\$\{?HOME\}?)/\.claude/plugins/netdust[a-z0-9*-]*/skills/[^\s`)\"\']+/?"
    )
    found = pattern.findall(md_text)
    # Strip trailing punctuation / markdown that the regex might pick up
    cleaned = []
    for g in found:
        g = g.rstrip(".,)")
        cleaned.append(g)
    return list(dict.fromkeys(cleaned))


def _expand(g: str) -> list[str]:
    """Tilde- and env-expand a glob, then return matched paths."""
    expanded = os.path.expandvars(os.path.expanduser(g))
    return glob.glob(expanded)


def test_skill_audit_glob_matches_real_skills() -> tuple[bool, str]:
    path = COMMANDS_DIR / "skill-audit.md"
    if not path.exists():
        return False, "skill-audit.md not found"

    globs = _extract_skill_globs(path.read_text())
    if not globs:
        return False, "skill-audit.md: no skill-dir globs found in body"

    failures = []
    successes = []
    for g in globs:
        matches = _expand(g)
        if not matches:
            failures.append(f"glob '{g}' matched 0 dirs")
        else:
            successes.append(f"{g} → {len(matches)} matches")

    if failures:
        return False, "skill-audit: " + "; ".join(failures)
    return True, f"skill-audit: {len(successes)} glob(s) all expand. {successes[0]}"


def test_red_test_glob_matches_real_skills() -> tuple[bool, str]:
    path = COMMANDS_DIR / "red-test.md"
    if not path.exists():
        return False, "red-test.md not found"

    globs = _extract_skill_globs(path.read_text())
    if not globs:
        return False, "red-test.md: no skill-dir globs found in body"

    failures = []
    # red-test globs use <skill-name> placeholder — substitute a known
    # real skill before expanding
    real_skill = "wp-security"
    for g in globs:
        concrete = g.replace("<skill-name>", real_skill)
        # Skip if no substitution happened AND the literal glob has no
        # wildcard that would match a real skill (it'd be aspirational text)
        if "<skill-name>" in g and concrete == g:
            continue
        matches = _expand(concrete)
        if not matches:
            failures.append(f"glob '{concrete}' matched 0 paths")

    if failures:
        return False, "red-test: " + "; ".join(failures)
    return True, f"red-test: globs expand against real skill '{real_skill}'"


def test_glob_covers_all_three_plugins() -> tuple[bool, str]:
    """Sanity check: the audit's fix was to change netdust-wp/... to
    netdust-*/... so the glob covers core, wp, and statamic. Verify the
    skill-audit glob, when expanded, finds skills from at least 2 plugins."""
    path = COMMANDS_DIR / "skill-audit.md"
    if not path.exists():
        return False, "skill-audit.md not found"

    globs = _extract_skill_globs(path.read_text())
    plugins_seen = set()
    for g in globs:
        for match in _expand(g):
            parts = Path(match).parts
            for p in parts:
                if p.startswith("netdust-"):
                    plugins_seen.add(p)

    if len(plugins_seen) < 2:
        return False, (
            f"cross-plugin: only found skills in {plugins_seen}. "
            f"Expected ≥2 of netdust-core/-wp/-statamic. "
            f"Globs were: {globs}"
        )
    return True, f"cross-plugin: globs cover {sorted(plugins_seen)}"


def run() -> list[tuple[bool, str]]:
    return [
        test_skill_audit_glob_matches_real_skills(),
        test_red_test_glob_matches_real_skills(),
        test_glob_covers_all_three_plugins(),
    ]
