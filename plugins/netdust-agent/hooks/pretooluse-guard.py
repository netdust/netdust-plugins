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
import subprocess
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
     re.compile(rf"(?m){_SEP}git\s+push\b[^\n]*[\s+](?:\S*:|refs/heads/)?(?:main|master)(?=\s|$)", re.IGNORECASE)),

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


# ── The flow floor (harness-inversion FR-24, 2026-09-02) ─────────────────────
#
# On a project carrying `site.yml`, the Makefile's verbs are the only door to a rung
# branch (the branches site.yml binds to environments). Agents routed around the flow
# when a verb died on a git error, or simply skipped it; the last gate — the deploy
# gate — refused hours after a commit landed on the wrong rung. This floor denies the
# raw git writes that bypass the flow AT THE COMMAND, naming the make verb that does it
# right. `deny`, not `ask`, on the upstream-floor reasoning: the correction is
# agent-side and costs one tool call. `make …` commands are never inspected — the verbs
# are the door — except when input is PIPED into a confirming verb, which is the one
# way to run `make ship` without a human typing yes.
#
# Rung names: `scripts/site environments.<e>.branch` when that reader is present (the
# project's own truth), else a dependency-free read of `branch:` lines under
# `environments:` in site.yml, else the fleet defaults. No site.yml anywhere up to the
# git toplevel → not a flow project → this floor does not exist. Every tooling failure
# (git missing, unreadable cwd, a subprocess timeout) fails OPEN like the rest of the hook.

FLOW_DEFAULT_RUNGS = ("main", "master", "staging", "development")
FLOW_CONFIRMING_VERBS = r"(?:ship|release|promote|deploy)"
# A make invocation that reaches a confirming verb (the verb must END there —
# `deploy-test` is not `deploy`).
FLOW_MAKE_CONFIRM = re.compile(
    rf"\bmake\b(?:\s+[^\s|<>;&'\"]+)*\s+{FLOW_CONFIRMING_VERBS}(?=[\s'\";&|)]|$)", re.IGNORECASE)
# …with its stdin forged: a pipe into it, ANY `<` redirect/here-doc/here-string in the
# command, or a pty/shell wrapper. The Makefile's own `[ -t 0 ]` check is the closing
# fix (a forged stdin is not a terminal); this is the belt.
FLOW_STDIN_FORGERY = re.compile(
    r"(?:\|\s*(?:[^\s|]+\s+)*?make\b|<|\b(?:expect|script|unbuffer|socat)\b|\b(?:sh|bash|zsh|dash)\s+-[a-z]*c\b)",
    re.IGNORECASE)
# Where a git write may start: the line, a shell separator/grouping, a command
# substitution, a control keyword, a wrapper, or an env assignment.
_FLOW_SEP = (r"(?:^|[;&|(){}]\s*|\$\(\s*|`\s*|\b(?:then|do|else)\s+"
             r"|\b(?:command|time|nice|sudo|exec|env)\s+(?:\w+=\S*\s+)*|(?:\b\w+=\S*\s+)+)")
# `git` with any global options between it and the verb (`-C path`, `-c k=v`, `--no-pager`, `-P`),
# an escaped `\git`, and a quoted verb.
_FLOW_GIT = r"\\?git(?:\s+(?:-[cC]\s*\S+|-[pP]\b|--[\w-]+(?:=\S+)?))*\s+['\"]?"
FLOW_WRITE_ON_BRANCH = re.compile(
    rf"(?m){_FLOW_SEP}{_FLOW_GIT}(commit|merge|rebase|cherry-pick|am|revert|reset|"
    rf"checkout\s+-b|switch\s+-c|branch\s+(?:-f|--force|-M|-m)|update-ref|symbolic-ref|"
    rf"stash\s+(?:pop|apply))(?=[\s'\"]|$)", re.IGNORECASE)
FLOW_RESET_MOVES_REF = re.compile(r"--(?:hard|keep|merge|soft|mixed)\b|\bHEAD[~^]|@\{|\b[0-9a-f]{7,40}\b", re.IGNORECASE)
FLOW_PUSH = re.compile(rf"(?m){_FLOW_SEP}{_FLOW_GIT}push\b([^\n;&|]*)", re.IGNORECASE)
FLOW_FETCH = re.compile(rf"(?m){_FLOW_SEP}{_FLOW_GIT}fetch\b([^\n;&|]*)", re.IGNORECASE)
FLOW_BRANCH_DELETE = re.compile(
    rf"(?m){_FLOW_SEP}{_FLOW_GIT}branch\s+(?:-[dD]|--delete)(?:\s+(?:-f|--force))?\s+(\S+)", re.IGNORECASE)
# a ref write that NAMES a rung — denied from any branch, the current one is irrelevant
FLOW_REF_WRITE = re.compile(
    rf"(?m){_FLOW_SEP}{_FLOW_GIT}(?:branch\s+(?:-f|--force|-M|-m)\s+(\S+)|update-ref\s+(?:refs/heads/)?(\S+))",
    re.IGNORECASE)
FLOW_SWITCH_TO = re.compile(
    rf"(?m){_FLOW_SEP}{_FLOW_GIT}(?:checkout|switch)(?:\s+-(?![bBcC]\b|-orphan)[a-zA-Z-]+)*\s+(?!-)(\S+)", re.IGNORECASE)

FLOW_VERB_FOR = {
    "commit": "make feature name=<x> first (a rung is deploy-only), then commit there",
    "merge": "make finish (feature → integration, hotfix → production and back down) or make promote name=<x>",
    "rebase": "make finish — the rungs are merged --no-ff, never rebased",
    "cherry-pick": "make hotfix name=<x>, then make finish",
    "am": "make hotfix name=<x>, then make finish",
    "revert": "make hotfix name=<x> carrying the revert, then make finish",
    "reset": "make rollback env=<name> — a rung's history is the deploy ledger",
    "checkout -b": "make feature name=<x> / make hotfix name=<x> — they pick the right base from site.yml",
    "switch -c": "make feature name=<x> / make hotfix name=<x> — they pick the right base from site.yml",
    "branch -f": "make finish — a rung pointer moves only by a --no-ff merge through the flow",
    "update-ref": "make finish — a rung pointer moves only by a --no-ff merge through the flow",
    "symbolic-ref": "make feature name=<x> — never re-point HEAD at a rung by hand",
    "stash pop": "make feature name=<x>, then pop the stash there",
    "stash apply": "make feature name=<x>, then apply the stash there",
    "push": "make finish (it pushes the rung it merged into) or make deploy env=<name>",
    "fetch": "make finish — a rung is updated by merging through the flow, never by a fetch refspec",
    "branch -D": "make finish / make promote name=<x> — a rung is never deleted; the flow promotes through it",
}


def _rung_named(args: str, rungs: set[str]) -> str | None:
    """A rung named as a WHOLE ref token in push/fetch args: `development`,
    `HEAD:development`, `+development`, `refs/heads/development`, `:development`
    (delete) — never `feature/main-nav` or `hotfix/staging-fix`."""
    for b in rungs:
        if re.search(rf"(?:^|[\s:+])(?:refs/heads/)?{re.escape(b)}(?=\s|$)", args):
            return b
    return None


def _flow_project_root(cwd: str) -> Path | None:
    """The nearest ancestor of cwd (inclusive) carrying site.yml, stopping at the git
    toplevel or the filesystem root. None → not a flow project."""
    try:
        d = Path(cwd).resolve()
    except Exception:
        return None
    for p in (d, *d.parents):
        if (p / "site.yml").is_file():
            return p
        if (p / ".git").exists():
            return None
    return None


def _flow_rungs(root: Path) -> set[str]:
    """Branch names bound to environments. A dependency-free read of `branch:` lines
    under `environments:` in site.yml FIRST — this hook fires on every Bash call, and
    the reviewer measured ~160 ms per call when scripts/site ran N+1 interpreters;
    the regex costs nothing. `scripts/site` (the project's own reader) only when the
    regex finds nothing (an exotic YAML shape), then the fleet defaults."""
    try:
        text = (root / "site.yml").read_text()
        m = re.search(r"(?ms)^environments:\s*\n(.*?)(?=^\S|\Z)", text)
        if m:
            found = {v.strip("'\"") for v in re.findall(r"^\s+branch:\s*([^\s#]+)", m.group(1), re.M)}
            found.discard("")
            if found:
                return found
    except Exception as e:  # noqa: BLE001
        log(f"flow-floor site.yml read failed err={e}")
    reader = root / "scripts" / "site"
    if reader.is_file():
        try:
            envs = subprocess.run([sys.executable, str(reader), "environments"], cwd=root,
                                  capture_output=True, text=True, timeout=3)
            if envs.returncode == 0:
                out = set()
                for e in envs.stdout.split()[:12]:
                    r = subprocess.run([sys.executable, str(reader), f"environments.{e}.branch"],
                                       cwd=root, capture_output=True, text=True, timeout=3)
                    if r.returncode == 0 and r.stdout.strip():
                        out.add(r.stdout.strip())
                if out:
                    return out
        except Exception as e:  # noqa: BLE001 — fail open to the defaults
            log(f"flow-floor scripts/site failed err={e}")
    return set(FLOW_DEFAULT_RUNGS)


def _flow_current_branch(root: Path) -> str | None:
    try:
        r = subprocess.run(["git", "branch", "--show-current"], cwd=root,
                           capture_output=True, text=True, timeout=3)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception as e:  # noqa: BLE001
        log(f"flow-floor git failed err={e}")
        return None


def _flow_deny(what: str, verb: str, detail: str) -> dict:
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            f"netdust-agent flow floor: {what} bypasses the branch flow this project's "
            f"Makefile owns ({detail}). Use the verb instead: {verb}. The Makefile is the "
            f"only door to a rung branch; nothing reaches production that did not walk "
            f"feature → integration → review → production through it."),
    }}


def check_flow_floor(hook_input: dict) -> dict | None:
    """Return a deny decision for a raw git write that bypasses the flow, else None."""
    try:
        tool_input = hook_input.get("tool_input") or {}
        command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
        if not isinstance(command, str) or not command.strip():
            return None
        root = _flow_project_root(hook_input.get("cwd") or "")
        if root is None:
            return None

        m = FLOW_MAKE_CONFIRM.search(command)
        if m and FLOW_STDIN_FORGERY.search(command):
            return _flow_deny(f"forging stdin for `{m.group(0).strip()}`",
                              "run the verb and type the confirmation yourself — a confirming "
                              "verb is a human moment by design (the Makefile refuses a "
                              "non-terminal stdin too)",
                              "a typed confirmation is the operator's, never piped or redirected")

        rungs = _flow_rungs(root)
        current = _flow_current_branch(root)
        switches = FLOW_SWITCH_TO.findall(command)
        # the branch a write lands on: the LAST checkout/switch in the command, else current
        landing = switches[-1] if switches else current
        on_rung = landing in rungs
        where = f"on `{landing}`"

        m = FLOW_WRITE_ON_BRANCH.search(command)
        if m and on_rung:
            key = re.sub(r"\s+", " ", m.group(1).lower())
            if key == "reset" and not FLOW_RESET_MOVES_REF.search(command[m.end():m.end() + 200]):
                pass  # `git reset <paths>` unstages; the pointer does not move
            else:
                key = "branch -f" if key.startswith("branch") else key
                return _flow_deny(f"`git {key}` {where}", FLOW_VERB_FOR.get(key, "the make verb"),
                                  "a rung branch is deploy-only")

        m = FLOW_REF_WRITE.search(command)
        if m and any(t and t.split(":")[0] in rungs for t in m.groups()):
            key = "branch -f" if "branch" in m.group(0).lower() else "update-ref"
            return _flow_deny(f"`git {key}` re-pointing a rung", FLOW_VERB_FOR[key], "a rung pointer")

        m = FLOW_PUSH.search(command)
        if m:
            args = m.group(1)
            named = _rung_named(args, rungs)
            if named or re.search(r"--(?:all|mirror)\b", args) or (
                    on_rung and not re.search(r"\b(?:feature|hotfix)/", args)):
                return _flow_deny(f"`git push` of a rung branch {where}", FLOW_VERB_FOR["push"],
                                  "the flow pushes a rung only after it merged into it")

        m = FLOW_FETCH.search(command)
        if m:
            dest = re.findall(r"\S+:(?:refs/heads/)?(\S+)", m.group(1))
            if any(d in rungs for d in dest):
                return _flow_deny("`git fetch` with a refspec into a rung", FLOW_VERB_FOR["fetch"],
                                  "a rung pointer moved by a refspec")

        m = FLOW_BRANCH_DELETE.search(command)
        if m and m.group(1) in rungs:
            return _flow_deny(f"`git branch -D {m.group(1)}`", FLOW_VERB_FOR["branch -D"],
                              "a rung branch")
        return None
    except Exception as e:  # noqa: BLE001 — fail OPEN, always
        log(f"flow-floor error err={e}")
        return None


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

    flow = check_flow_floor(hook_input)   # FR-24 — deny, before the ask-tier denylist
    if flow is not None:
        log(f"deny reason=flow-floor cmd={command[:80]!r}")
        print(json.dumps(flow))
        return

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
