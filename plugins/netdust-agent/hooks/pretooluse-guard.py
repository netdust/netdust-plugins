#!/usr/bin/env python3
"""
pretooluse-guard.py — netdust-agent harness

PreToolUse hook. Fires before a tool call executes. For Bash commands it
pattern-matches a conservative denylist of destructive actions and asks for
human confirmation before they run.

Purpose:
  Every other netdust-agent guardrail is post-hoc (SubagentStop catches "you
  didn't test" after the code exists). NOTHING intercepts `rm -rf`,
  `git push --force`, a direct push to main, `DROP TABLE`, or a prod cache
  flush BEFORE it runs. CLAUDE.md / RULES.md encode the intent, but that is
  advice the model can skip — not an enforced invariant. This hook makes the
  highest-risk irreversible actions surface a permission prompt deterministically,
  regardless of what the model intends. It is the execution-time Control floor
  named in the harness-completeness plan (Item 2) and its parked threat model
  (docs/harness-engineering-hardening-plan.md).

Decision policy (v1 — conservative, favor `ask` over `deny`):
  • A matched destructive pattern → permissionDecision "ask" (surface the
    literal command to a human; the model's stated intent is NOT trusted).
  • Everything else, any non-Bash tool, any parse failure → no output
    (passthrough): the call proceeds through the normal permission flow.
  v1 deliberately uses `ask` for ALL Bash patterns, never `deny` — a hard deny
  risks blocking legit work, and `ask` already stops the autonomous/injected
  case (a human sees the literal command).
  The ONE deny tier (2026-08-10): the upstream-invocation floor on Write —
  creating specs/<f>/spec.md (plan.md, tasks.md) without the corresponding
  superpowers skill invoked in this session's transcript. Deny is right there
  because the correction is agent-side and costs one tool call; it fails OPEN
  on every tooling problem and never applies to edits of existing files.

CRITICAL — fails OPEN. Per the Claude Code hook contract, exit 2 is the only
exit code that blocks a tool on the hook's own authority; any other exit code
(incl. crashes) lets the tool proceed. This script therefore wraps everything
in try/except and ALWAYS exits 0 — a malformed payload, an unexpected tool
shape, or an internal bug can never brick a session by blocking every call.
The guard adds friction on matched patterns; it never removes the ability to
work.

Output contract (when a pattern matches):
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "ask",
                          "permissionDecisionReason": "<why>"}}

Logs to ~/.claude/logs/memory-hook.log (shared with the other hooks).
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

LOG_PATH = Path.home() / ".claude" / "logs" / "memory-hook.log"


def log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a") as f:
            f.write(f"[{ts}] pretooluse-guard: {msg}\n")
    except Exception:
        pass


# Denylist v1. Each entry: (label, compiled regex). The regex matches the
# command STRING. Patterns are anchored to command position where it matters
# so that a literal substring inside a quoted argument (grep 'DROP TABLE',
# echo 'rm -rf /') does NOT trip the guard — the dominant false-positive class.
#
# `(?m)` + a command-boundary prefix `(?:^|[;&|]\s*|\b(?:then|do|else)\s+)` lets
# us catch a destructive command at the start of the line OR after a shell
# separator (`;`, `&&`, `||`, `|`) or a control keyword, while a leading
# `echo`/`grep`/`cat`/`#` keeps the literal-in-argument cases out.
_SEP = r"(?:^|[;&|]\s*|\b(?:then|do|else)\s+)"

DENYLIST: list[tuple[str, re.Pattern]] = [
    # Attack 1 — rm with BOTH recursive and force flags, as an actual command:
    # combined (-rf / -fr / -Rf) or separate (-r -f / -f -r), either order.
    # `rm -r` alone (recursive, not forced) is intentionally NOT in v1 — the
    # irreversible-without-prompt case is the force flag.
    ("rm -rf (recursive force delete)",
     re.compile(
         rf"(?m){_SEP}rm\s+(?:"
         r"-\S*r\S*f\S*|-\S*f\S*r\S*"
         r"|-[A-Za-z]*r[A-Za-z]*\s+-[A-Za-z]*f[A-Za-z]*"
         r"|-[A-Za-z]*f[A-Za-z]*\s+-[A-Za-z]*r[A-Za-z]*"
         r")",
         re.IGNORECASE)),

    # Attack 2 — git force-push, +refspec, or direct push to main/master.
    ("git force-push or +refspec",
     re.compile(rf"(?m){_SEP}git\s+push\b.*(?:--force(?:-with-lease)?|\s-[A-Za-z]*f|\s\+\S+:)", re.IGNORECASE)),
    # main/master must be a WHOLE ref argument (optionally a refspec destination
    # `HEAD:main` or a fully-qualified `refs/heads/main`) — a branch name that
    # merely contains the word (`feature/main-nav`) must not trip the guard.
    ("git push directly to main/master",
     re.compile(rf"(?m){_SEP}git\s+push\b[^\n]*\s(?:\S*[:/])?(?:main|master)(?=\s|$)", re.IGNORECASE)),

    # Attack 5 — destructive SQL as an executed statement (mysql -e '...', psql -c).
    ("destructive SQL (DROP/TRUNCATE)",
     re.compile(r"(?:-e|-c|--execute|--command)\s*[\"'][^\"']*\b(?:DROP\s+(?:TABLE|DATABASE|SCHEMA)|TRUNCATE)\b", re.IGNORECASE)),

    # Destructive WP-CLI db subcommands.
    ("destructive wp-cli db (reset/drop)",
     re.compile(rf"(?m){_SEP}wp\s+(?:.*\s)?db\s+(?:reset|drop)\b", re.IGNORECASE)),

    # RULES.md rule 10 — cache/redis flush (destroys VAD's LMS cache exclusions).
    ("redis/cache flush (RULES.md rule 10)",
     re.compile(rf"(?m){_SEP}(?:redis-cli\s+(?:.*\s)?FLUSH(?:ALL|DB)|wp\s+(?:.*\s)?cache\s+flush)\b", re.IGNORECASE)),
]


# ── The upstream-invocation floor (2026-08-10) ────────────────────────────────
#
# Superpowers is the workhorse; the netdust overlays add gates around it. That
# architecture held in prose and failed in practice three sessions running:
# specs and plans were authored without ever loading the upstream skill. This
# floor makes the invocation mechanical: CREATING a seam artifact requires its
# upstream superpowers skill to appear as a Skill tool_use in the session
# transcript. The decision is `deny` (not `ask`) BY DESIGN — the correction is
# agent-side and costs one tool call (invoke the named skill, retry); no human
# needs to arbitrate. Editing existing artifacts is free (Class B freshness
# reviews, ledger ticks), a waiver comment in the content bypasses, and every
# tooling failure (no transcript_path, unreadable file) fails OPEN like the
# rest of this hook. Limit stated honestly: this proves the skill was LOADED
# (its discipline in context), not followed — that half stays with review.

UPSTREAM_FLOOR: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?:^|/)specs/[^/]+/spec\.md$"), "superpowers:brainstorming"),
    (re.compile(r"(?:^|/)specs/[^/]+/(?:plan|tasks)\.md$"), "superpowers:writing-plans"),
]
UPSTREAM_WAIVER = "<!-- upstream: waived"


def transcript_has_skill(transcript_path: str, skill: str) -> bool:
    """True if the session transcript records a Skill tool_use for `skill`.
    Line-prefiltered so a multi-MB transcript costs one pass, JSON-confirmed so
    a prose mention of the skill name never counts as an invocation."""
    with open(transcript_path, errors="ignore") as f:
        for line in f:
            if skill not in line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = (entry.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and block.get("name") == "Skill"
                        and (block.get("input") or {}).get("skill") == skill):
                    return True
    return False


def check_upstream_floor(hook_input: dict) -> dict | None:
    """Return a deny decision when a seam artifact is being CREATED without its
    upstream superpowers skill in the transcript; None to pass through."""
    tool_input = hook_input.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None
    file_path = tool_input.get("file_path", "")
    if not isinstance(file_path, str) or not file_path:
        return None
    needed = None
    for pat, skill in UPSTREAM_FLOOR:
        if pat.search(file_path):
            needed = skill
            break
    if needed is None:
        return None  # not a seam artifact
    if Path(file_path).exists():
        return None  # editing, not creating — Class B / ledger ticks stay free
    content = tool_input.get("content", "")
    if isinstance(content, str) and UPSTREAM_WAIVER in content:
        log(f"upstream-floor waived path={file_path!r}")
        return None
    transcript_path = hook_input.get("transcript_path", "")
    if not isinstance(transcript_path, str) or not transcript_path:
        log("upstream-floor passthrough reason=no-transcript-path (fail open)")
        return None
    try:
        if transcript_has_skill(transcript_path, needed):
            return None  # upstream skill loaded — floor satisfied
    except OSError:
        log(f"upstream-floor passthrough reason=transcript-unreadable path={transcript_path!r} (fail open)")
        return None
    reason = (
        f"netdust-agent upstream-invocation floor: you are creating "
        f"{Path(file_path).name} but this session never invoked `{needed}` — "
        f"superpowers is the workhorse and the overlay only adds gates around it "
        f"(planning Stage {'0' if needed.endswith('brainstorming') else '1'}). "
        f"Invoke Skill(\"{needed}\") first, then retry this Write. Genuine "
        f"exceptions state `{UPSTREAM_WAIVER} — <reason> -->` in the file."
    )
    log(f"deny reason=upstream-floor missing={needed!r} path={file_path!r}")
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def match_denylist(command: str) -> tuple[str, str] | None:
    """Return (label, matched_text) for the first denylist hit, else None.
    A command that begins with a read-only echo/grep/cat is treated as inert
    (the destructive token is data, not an executed command)."""
    if not command or not command.strip():
        return None
    for label, pat in DENYLIST:
        m = pat.search(command)
        if m:
            return label, m.group(0).strip()
    return None


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        log("passthrough reason=empty-stdin")
        return  # exit 0, no output → proceed

    try:
        hook_input = json.loads(raw)
    except json.JSONDecodeError:
        log(f"passthrough reason=stdin-json-parse-failed raw_len={len(raw)}")
        return  # fail OPEN

    tool_name = hook_input.get("tool_name", "")
    if tool_name == "Write":
        decision = check_upstream_floor(hook_input)
        if decision is not None:
            print(json.dumps(decision))
        return
    if tool_name != "Bash":
        # Bash denylist + the Write upstream floor are the guard's two jobs.
        return  # passthrough

    tool_input = hook_input.get("tool_input") or {}
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
    if not isinstance(command, str) or not command.strip():
        return  # nothing to match → passthrough

    hit = match_denylist(command)
    if not hit:
        return  # benign → passthrough (normal permission flow decides)

    label, matched = hit
    reason = (
        f"netdust-agent guard: this command matches a destructive pattern "
        f"({label}). The harness asks for explicit confirmation before "
        f"irreversible actions (rm -rf, force-push / push-to-main, DROP/"
        f"TRUNCATE, db reset/drop, cache flush) — regardless of stated intent. "
        f"Matched: {matched!r}. Confirm only if you intend exactly this."
    )
    decision = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }
    log(f"ask reason={label!r} matched={matched!r}")
    print(json.dumps(decision))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Fail OPEN: never block a tool call because the guard itself broke.
        log(f"unhandled-exception err={e} (failing open)")
    sys.exit(0)
