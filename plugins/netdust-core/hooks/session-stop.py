#!/usr/bin/env python3
"""
session-stop.py — netdust-core harness

Runs at every Claude Code session end (Stop hook).

Two-track memory extraction:

  Track A — DETERMINISTIC TAG SCANNER (always on, zero latency, zero cost)
    Scans the session transcript for tagged lines Claude wrote during the
    session and lifts them into memory files:
      • DECISION: <text>     → memory/STATE.md
      • RISK: <text>         → memory/STATE.md (as a risk bullet)
      • LESSON: <text>       → memory/lessons.md
      • TODO: <text>         → tasks/todo.md
      • SKILL-EDGE: <skill>: <text>  → skills/.../<skill>/lessons.md
    This means Claude (or Stefan via Claude) just writes "DECISION: ..." in
    the conversation and the hook captures it deterministically. No AI call.

  Track B — HAIKU SUMMARIZER (opt-in, only if ANTHROPIC_API_KEY is set)
    Calls the Anthropic API directly (not the slow `claude -p` CLI) to
    produce a richer PM-level state summary. Falls back silently if no key.

Either track may run. Both run if both are configured. Neither blocks the
session — entire hook runs in < 3s in deterministic-only mode.

Observability:
  • Every fire logs to ~/.claude/logs/memory-hook.log
  • No-op writes a visible marker to STATE.md (so you SEE the hook working)
  • Errors write a visible ⚠ marker to STATE.md
"""

import json
import re
import sys
import os
import hashlib
import subprocess
import tempfile
import urllib.request
import urllib.error
import traceback
from pathlib import Path
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────

HAIKU_MODEL = "claude-haiku-4-5-20251001"
HAIKU_TIMEOUT_SEC = 20              # API call (not CLI) — fast
MAX_TRANSCRIPT_LINES = 200          # lines of transcript to scan/summarize
MAX_LESSONS_FILE = 80               # warn if lessons.md exceeds this
MAX_EXISTING_STATE_LINES = 80       # context passed to Haiku to avoid redundancy
MAX_CONTINUATION_LINES = 10         # lines a single tag may consume past its head
MAX_CAPTURED_HASHES = 200           # cap on the sidecar dedup ring

SIDECAR_NAME = ".stop-hook-state.json"  # under memory/

LOG_PATH = Path.home() / ".claude" / "logs" / "memory-hook.log"
DASHBOARD_SYNC = Path.home() / "Sites" / "netdust-wp-manager" / "scripts" / "sync-from-site.sh"

# ── Logging ──────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    """Always write a line. Never raises."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        pass


# ── Transcript ───────────────────────────────────────────────────────────────

def read_transcript(path: str) -> list[dict]:
    try:
        messages = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return messages
    except Exception:
        return []


def slice_new_messages(messages: list[dict], last_uuid: str | None) -> list[dict]:
    """Return only the messages AFTER the one whose top-level uuid == last_uuid.

    Watermark semantics:
      • last_uuid is None  → first run, process everything.
      • last_uuid found    → process strictly the messages after it.
      • last_uuid missing  → can't trust the watermark (transcript replaced /
        compacted) → fall back to a full scan; the hash dedup is the backstop.
    """
    if not last_uuid:
        return messages
    for i, msg in enumerate(messages):
        if msg.get("uuid") == last_uuid:
            return messages[i + 1:]
    return messages  # uuid not found → full re-scan, hash dedup catches dupes


def last_message_uuid(messages: list[dict]) -> str | None:
    """The top-level uuid of the last message that carries one."""
    for msg in reversed(messages):
        u = msg.get("uuid")
        if u:
            return u
    return None


def extract_claude_text(messages: list[dict]) -> str:
    """All text Claude wrote in the given messages, joined."""
    parts = []
    for msg in messages:
        if msg.get("type") != "assistant":
            continue
        content = msg.get("message", {}).get("content", "")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
        elif isinstance(content, str):
            parts.append(content)
    return "\n".join(parts)


def format_transcript_for_haiku(messages: list[dict]) -> str:
    lines = []
    for msg in messages:
        role = msg.get("type", "")
        content = msg.get("message", {}).get("content", "")

        if role == "user" and isinstance(content, str) and content.strip():
            lines.append(f"USER: {content[:300]}")

        elif role == "assistant":
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text:
                            lines.append(f"CLAUDE: {text[:300]}")
            elif isinstance(content, str) and content.strip():
                lines.append(f"CLAUDE: {content[:300]}")

    recent = lines[-MAX_TRANSCRIPT_LINES:]
    return "\n".join(recent)


def read_existing_state(cwd: str) -> str:
    """Last N lines of project STATE.md, for Haiku context."""
    path = Path(cwd) / "memory" / "STATE.md"
    if not path.exists():
        return "(no existing STATE.md)"
    try:
        lines = path.read_text().splitlines()
        return "\n".join(lines[-MAX_EXISTING_STATE_LINES:])
    except Exception:
        return "(could not read existing STATE.md)"


# ── Track A: deterministic tag scanner ──────────────────────────────────────

# Head-line matchers. A tag captures its head line PLUS any continuation
# lines (indented, or starting with "- ") until a blank line or a new tag,
# capped at MAX_CONTINUATION_LINES — so a multi-line DECISION isn't truncated
# mid-sentence (the 2026-06-05 "This consolidates everything:" bug).
TAG_HEADS = {
    "decision":   re.compile(r"^\s*DECISION:\s*(.*)$",   re.IGNORECASE),
    "risk":       re.compile(r"^\s*RISK:\s*(.*)$",       re.IGNORECASE),
    "lesson":     re.compile(r"^\s*LESSON:\s*(.*)$",     re.IGNORECASE),
    "todo":       re.compile(r"^\s*TODO:\s*(.*)$",       re.IGNORECASE),
    # SKILL-EDGE: <skill-name>: <text>
    "skill_edge": re.compile(r"^\s*SKILL-EDGE:\s*([a-z0-9_-]+):\s*(.*)$", re.IGNORECASE),
}

# A line that continues the tag above it: indented, or a markdown bullet.
_CONTINUATION = re.compile(r"^(\s+\S|\s*-\s+)")

# Any line that opens a NEW tag (ends a continuation block).
_ANY_TAG_HEAD = re.compile(
    r"^\s*(DECISION|RISK|LESSON|TODO|SKILL-EDGE):", re.IGNORECASE
)


def _is_continuation(line: str) -> bool:
    return bool(line.strip()) and bool(_CONTINUATION.match(line)) and not _ANY_TAG_HEAD.match(line)


def scan_tags(text: str) -> dict:
    """Extract DECISION/RISK/LESSON/TODO/SKILL-EDGE entries from Claude's output.

    Each entry is the head line's text joined with its continuation lines
    (newline-separated), so multi-line tags survive intact. The scan walks
    line-by-line rather than per-line regex so it can consume continuations.
    """
    out = {"decisions": [], "risks": [], "lessons": [], "todos": [], "skill_edges": []}
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        matched_kind = None
        for kind, pat in TAG_HEADS.items():
            m = pat.match(line)
            if m:
                matched_kind = kind
                break
        if matched_kind is None:
            i += 1
            continue

        # Gather continuation lines (bounded).
        cont = []
        j = i + 1
        while j < n and len(cont) < MAX_CONTINUATION_LINES and _is_continuation(lines[j]):
            cont.append(lines[j].rstrip())
            j += 1

        if matched_kind == "skill_edge":
            skill = m.group(1).strip()
            head = m.group(2).strip()
            body = "\n".join([head] + cont).strip()
            out["skill_edges"].append((skill, body))
        else:
            head = m.group(1).strip()
            body = "\n".join([head] + cont).strip()
            key = {"decision": "decisions", "risk": "risks",
                   "lesson": "lessons", "todo": "todos"}[matched_kind]
            if body:
                out[key].append(body)

        i = j  # resume after the consumed continuation block

    return out


def has_tag_content(tags: dict) -> bool:
    return any(tags.values())


# ── Track B: Haiku via Anthropic API (opt-in) ───────────────────────────────

def call_haiku_api(summary: str, cwd: str, existing_state: str) -> tuple[dict | None, str]:
    """
    Direct Anthropic API call — fast (~2-5s), not the slow `claude -p` CLI.
    Returns (result_dict_or_None, status_msg).
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None, "skip:no-api-key"

    if not summary.strip():
        return None, "skip:no-content"

    prompt = f"""You are a memory extraction system for Stefan's Netdust WordPress sessions.

Working directory: {cwd}

EXISTING memory/STATE.md (last lines — do NOT restate these):
---
{existing_state}
---

Session transcript (recent exchanges):
{summary}

Decide what (if anything) is worth saving to project memory.

SAVE CRITERIA (be conservative but not silent):
- A decision was made that affects future sessions.
- A fragile spot, risk, or gotcha was found.
- A task completed that meaningfully changes project state.
- Context that would need re-explaining next session.

DO NOT save:
- Routine edits, content updates, anything derivable from git log.
- Anything already in the existing STATE.md above.
- Conversational chit-chat.

Output EXACTLY this JSON shape (no markdown, no prose around it):

{{
  "save": true | false,
  "state": "PM-level state update — what changed, current status, any new risks — or null",
  "todo": "open work to carry into next session — or null"
}}

If save=false, return null for state and todo."""

    payload = json.dumps({
        "model": HAIKU_MODEL,
        "max_tokens": 800,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=HAIKU_TIMEOUT_SEC) as resp:
            data = json.loads(resp.read())
            text = data["content"][0]["text"].strip()
            if text.startswith("```"):
                text = "\n".join(text.split("\n")[1:])
            if text.endswith("```"):
                text = "\n".join(text.split("\n")[:-1])
            if not text.startswith("{"):
                start = text.find("{")
                if start >= 0:
                    text = text[start:]
            try:
                return json.loads(text), "ok"
            except json.JSONDecodeError:
                return None, "error:json"
    except urllib.error.HTTPError as e:
        return None, f"error:http-{e.code}"
    except Exception as e:
        return None, f"error:other:{type(e).__name__}"


# ── Watermark sidecar (idempotency) ──────────────────────────────────────────

def sidecar_path(cwd: str) -> Path:
    return Path(cwd) / "memory" / SIDECAR_NAME


def read_sidecar(cwd: str) -> dict:
    """Load the watermark sidecar. Returns a well-formed default on any error."""
    default = {"transcript_path": None, "last_processed_uuid": None, "captured_hashes": []}
    path = sidecar_path(cwd)
    if not path.exists():
        return default
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            return default
        data.setdefault("transcript_path", None)
        data.setdefault("last_processed_uuid", None)
        hashes = data.get("captured_hashes")
        data["captured_hashes"] = hashes if isinstance(hashes, list) else []
        return data
    except Exception:
        return default


def write_sidecar_atomic(cwd: str, state: dict) -> None:
    """Write the sidecar via tmp file + os.replace so a crash never leaves a
    half-written watermark. Best-effort; never raises into the hook."""
    path = sidecar_path(cwd)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Cap the hash ring at the most recent N.
        state["captured_hashes"] = list(state.get("captured_hashes", []))[-MAX_CAPTURED_HASHES:]
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".stop-hook-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(state, f, indent=2)
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except Exception:
                pass
            raise
    except Exception as e:
        log(f"warn sidecar-write-failed cwd={cwd} err={type(e).__name__}:{e}")


def normalized_hash(text: str) -> str:
    """Stable hash of a tag's normalized text (whitespace-collapsed, lowercased)."""
    norm = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def dedup_against_hashes(items: list, captured: set, key_of) -> list:
    """Filter items whose normalized hash is already captured. Adds survivors'
    hashes to `captured` (mutated in place). key_of(item) -> the text to hash."""
    kept = []
    for item in items:
        h = normalized_hash(key_of(item))
        if h in captured:
            continue
        captured.add(h)
        kept.append(item)
    return kept


# ── File writers ─────────────────────────────────────────────────────────────

def append_state(cwd: str, body: str, date: str) -> None:
    path = Path(cwd) / "memory" / "STATE.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    header = f"\n---\n### {date}\n"
    with open(path, "a") as f:
        f.write(header + body.strip() + "\n")


def append_state_marker(cwd: str, line: str) -> None:
    """Single-line marker. Only annotates if memory/ already exists."""
    path = Path(cwd) / "memory" / "STATE.md"
    if not path.parent.exists():
        return
    try:
        with open(path, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def daily_marker_already_written(cwd: str, date: str) -> bool:
    """True if today's 'no significant changes' marker is already in STATE.md,
    so we write it at most once per calendar day."""
    path = Path(cwd) / "memory" / "STATE.md"
    if not path.exists():
        return False
    try:
        content = path.read_text()
    except Exception:
        return False
    return f"[{date}] — session ended (no significant changes captured)" in content


def append_state_from_tags(cwd: str, decisions: list[str], risks: list[str], date: str) -> bool:
    """Lift DECISION:/RISK: tags into a dated STATE.md section. Returns True if wrote."""
    if not decisions and not risks:
        return False
    path = Path(cwd) / "memory" / "STATE.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [f"\n---\n### {date} — tagged capture"]
    if decisions:
        body.append("\n**Decisions**")
        body.extend(f"- {d}" for d in decisions)
    if risks:
        body.append("\n**Risks**")
        body.extend(f"- {r}" for r in risks)
    body.append("")
    with open(path, "a") as f:
        f.write("\n".join(body))
    return True


def append_lessons_from_tags(cwd: str, lessons: list[str], date: str) -> bool:
    if not lessons:
        return False
    path = Path(cwd) / "memory" / "lessons.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [f"\n### {date}"]
    body.extend(f"- {l}" for l in lessons)
    body.append("")
    with open(path, "a") as f:
        f.write("\n".join(body))
    line_count = sum(1 for _ in open(path))
    if line_count > MAX_LESSONS_FILE:
        log(f"warn lessons-file-long path={path} lines={line_count}")
    return True


def append_todos_from_tags(cwd: str, todos: list[str], date: str) -> bool:
    if not todos:
        return False
    path = Path(cwd) / "tasks" / "todo.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = [f"\n---\n## Carried forward ({date})"]
    body.extend(f"- [ ] {t}" for t in todos)
    body.append("")
    with open(path, "a") as f:
        f.write("\n".join(body))
    return True


def _netdust_plugin_dirs() -> list[Path]:
    """
    Locate all installed netdust-* plugin dirs.

    Marketplace install layout (Claude Code 2.1+):
        ~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/

    Climbs from CLAUDE_PLUGIN_ROOT (this hook's own plugin install path) up
    two levels to reach the marketplace dir, then enumerates siblings.
    For each sibling, picks the latest-mtime version dir (proxy for "active").

    Falls back to globbing ~/.claude/plugins/netdust-* if env var is unset
    (legacy/dev layout). Returns absolute paths to the version dirs.
    """
    root_env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root_env:
        # cache/<marketplace>/<self-plugin>/<version> — climb to <marketplace>
        marketplace_dir = Path(root_env).parent.parent
        result = []
        for sibling in marketplace_dir.iterdir():
            if not sibling.is_dir() or not sibling.name.startswith("netdust-"):
                continue
            versions = [v for v in sibling.iterdir() if v.is_dir()]
            if not versions:
                continue
            latest = max(versions, key=lambda p: p.stat().st_mtime)
            result.append(latest)
        return result

    # Legacy fallback: pre-monorepo flat layout.
    plugins_root = Path.home() / ".claude" / "plugins"
    if not plugins_root.exists():
        return []
    return [p for p in plugins_root.glob("netdust-*") if p.is_dir()]


def append_skill_edge(skill: str, edge_case: str, date: str, source_project: str) -> bool:
    """
    Append a SKILL-EDGE entry to the named skill's lessons.md.
    Searches all installed netdust-* plugin dirs (core, wp, statamic, etc.).
    """
    for plugin_dir in _netdust_plugin_dirs():
        candidate = plugin_dir / "skills" / skill / "SKILL.md"
        if candidate.exists():
            lessons_path = candidate.parent / "lessons.md"
            lessons_path.touch(exist_ok=True)
            entry = f"\n### {date} — {edge_case}\n- Source: {source_project}\n"
            with open(lessons_path, "a") as f:
                f.write(entry)
            return True
    return False


# ── Git + dashboard ─────────────────────────────────────────────────────────

def _ensure_sidecar_gitignored(cwd: str) -> None:
    """The watermark sidecar is per-machine transient state, not memory
    content — keep it out of the project's git history."""
    entry = f"memory/{SIDECAR_NAME}"
    gitignore = Path(cwd) / ".gitignore"
    try:
        existing = gitignore.read_text() if gitignore.exists() else ""
        if entry in existing.splitlines():
            return
        with open(gitignore, "a") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(entry + "\n")
    except Exception as e:
        log(f"warn gitignore-write-failed cwd={cwd} err={type(e).__name__}:{e}")


def git_commit_memory(cwd: str) -> None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd, capture_output=True, text=True,
        )
        if result.returncode != 0:
            return

        _ensure_sidecar_gitignored(cwd)

        subprocess.run(
            ["git", "add", "memory/", "tasks/"],
            cwd=cwd, capture_output=True,
        )

        status = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=cwd, capture_output=True,
        )
        if status.returncode == 0:
            return  # Nothing staged

        project = Path(cwd).name
        subprocess.run(
            ["git", "commit", "-m", f"memory({project}): auto-capture session end"],
            cwd=cwd, capture_output=True,
        )
    except Exception as e:
        log(f"warn git-commit-failed cwd={cwd} err={type(e).__name__}:{e}")


def trigger_dashboard_sync(cwd: str) -> None:
    if not DASHBOARD_SYNC.exists():
        return
    try:
        subprocess.run([str(DASHBOARD_SYNC), cwd], capture_output=True, timeout=10)
    except Exception as e:
        log(f"warn dashboard-sync-failed cwd={cwd} err={type(e).__name__}:{e}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    try:
        raw = sys.stdin.read()
    except Exception:
        log("error stdin-read-failed")
        sys.exit(0)

    try:
        hook_input = json.loads(raw) if raw else {}
    except Exception:
        log(f"error stdin-json-parse raw_len={len(raw)}")
        sys.exit(0)

    transcript_path = hook_input.get("transcript_path", "")
    cwd = hook_input.get("cwd", os.getcwd())
    date = datetime.now().strftime("%Y-%m-%d")
    project = Path(cwd).name

    if not transcript_path:
        log(f"skip no-transcript-path cwd={cwd}")
        sys.exit(0)

    messages = read_transcript(transcript_path)
    if not messages:
        log(f"skip empty-transcript cwd={cwd}")
        sys.exit(0)

    # ── Idempotency watermark ────────────────────────────────────────────────
    # Read the sidecar, process ONLY messages after the last_processed_uuid
    # (full scan if the uuid is missing or the transcript path changed). The
    # hash dedup below is the belt-and-braces backstop for the full-scan case.
    sidecar = read_sidecar(cwd)
    same_transcript = sidecar.get("transcript_path") == transcript_path
    last_uuid = sidecar.get("last_processed_uuid") if same_transcript else None
    new_messages = slice_new_messages(messages, last_uuid)

    captured = set(sidecar.get("captured_hashes", []))

    # ── Track A: deterministic tag scan (only the new slice) ────────────────
    claude_text = extract_claude_text(new_messages)
    tags = scan_tags(claude_text)

    # Did this fire SEE any tags at all (pre-dedup)? Distinguishes a genuine
    # no-capture session (→ visibility marker) from a re-fire where tags were
    # found but already captured (→ no marker, it's not "no changes").
    tags_seen_pre_dedup = has_tag_content(tags)

    # Belt-and-braces hash dedup: drop any tag already captured in a prior fire.
    tags["decisions"] = dedup_against_hashes(tags["decisions"], captured, lambda x: x)
    tags["risks"]     = dedup_against_hashes(tags["risks"], captured, lambda x: x)
    tags["lessons"]   = dedup_against_hashes(tags["lessons"], captured, lambda x: x)
    tags["todos"]     = dedup_against_hashes(tags["todos"], captured, lambda x: x)
    tags["skill_edges"] = dedup_against_hashes(
        tags["skill_edges"], captured, lambda se: f"{se[0]}:{se[1]}"
    )

    written = []

    if tags["decisions"] or tags["risks"]:
        if append_state_from_tags(cwd, tags["decisions"], tags["risks"], date):
            written.append("STATE.md(tags)")

    if tags["lessons"]:
        if append_lessons_from_tags(cwd, tags["lessons"], date):
            written.append("lessons.md(tags)")

    if tags["todos"]:
        if append_todos_from_tags(cwd, tags["todos"], date):
            written.append("todo.md(tags)")

    for skill, edge in tags["skill_edges"]:
        if append_skill_edge(skill, edge, date, project):
            written.append(f"skill:{skill}/lessons.md")
        else:
            log(f"warn skill-edge-no-match skill={skill}")

    # ── Track B: Haiku via API (opt-in) ─────────────────────────────────────
    haiku_status = "skip:no-api-key"
    if os.environ.get("ANTHROPIC_API_KEY"):
        summary = format_transcript_for_haiku(messages)
        existing_state = read_existing_state(cwd)
        result, haiku_status = call_haiku_api(summary, cwd, existing_state)

        if haiku_status.startswith("error"):
            log(f"error haiku status={haiku_status} cwd={cwd}")
            # Only annotate STATE.md on persistent/auth errors. JSON parse fails
            # and transient errors stay in the log only — they'd otherwise pile up.
            if haiku_status in ("error:http-401", "error:http-403", "error:timeout"):
                append_state_marker(cwd, f"[{date}] — ⚠ memory hook (haiku) errored: {haiku_status}")
        elif haiku_status == "ok" and result and result.get("save"):
            if result.get("state"):
                append_state(cwd, result["state"], date)
                written.append("STATE.md(haiku)")
            if result.get("todo"):
                append_todos_from_tags(cwd, [result["todo"]], date)
                written.append("todo.md(haiku)")

    # ── Visibility marker ───────────────────────────────────────────────────
    # If nothing was written, append a one-line "session ended" marker so the
    # file's timestamp updates and you can SEE the hook running — but:
    #   • at most ONCE per calendar day (repeated no-tag stops don't pile up), and
    #   • NOT on a pure re-fire. A second Stop on the same transcript has an
    #     empty new-message slice (or fully-deduped tags); that session already
    #     captured its content, so claiming "no significant changes" would be a
    #     lie and would mutate STATE.md on a no-op fire.
    genuine_empty_session = bool(new_messages) and not tags_seen_pre_dedup
    if (not written and genuine_empty_session
            and not daily_marker_already_written(cwd, date)):
        marker = f"[{date}] — session ended (no significant changes captured)"
        append_state_marker(cwd, marker)

    # ── Advance the watermark (atomic, even on partial failure above) ───────
    new_uuid = last_message_uuid(messages) or sidecar.get("last_processed_uuid")
    write_sidecar_atomic(cwd, {
        "transcript_path": transcript_path,
        "last_processed_uuid": new_uuid,
        "captured_hashes": list(captured),
    })

    log(f"done cwd={cwd} tags=[{','.join(k for k,v in tags.items() if v)}] haiku={haiku_status} wrote=[{','.join(written)}]")

    git_commit_memory(cwd)
    trigger_dashboard_sync(cwd)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("error unhandled-exception\n" + traceback.format_exc())
        sys.exit(0)
