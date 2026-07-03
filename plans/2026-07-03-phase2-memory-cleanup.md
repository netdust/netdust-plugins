# Phase 2 — Memory-System Frozen-Damage Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the frozen damage the pre-fix Stop hook left behind (duplicate capture blocks + ~1,220 noise lines across 17 memory files), delete dead artifacts, and clean the netdust-core plugin of its dead hook copies, stale docs, and version drift.

**Architecture:** Three independent phases. Phase A runs ONE audited Python routine (dry-run → backup → apply → verify → commit-where-tracked) over every fleet memory file. Phase B is three targeted deletions/migrations. Phase C is a netdust-plugins branch that deletes core's dead hooks, ports the two core-only test modules to netdust-agent (where the live hooks live), fixes doc drift, and ships 0.2.3.

**Tech Stack:** Python 3 (cleanup script + existing test harness), bash, git, `claude plugin` CLI.

**Classification:** Class A (multi-task cleanup bundle). Phase 1 (netdust-agent 0.3.1 / netdust-core 0.2.2 hook fixes) is live — hooks now dedup against target-file content and honor `.no-auto-memory`, so cleaned files stay clean.

## Global Constraints

- Cleanup touches ONLY: (a) lines exactly matching `[YYYY-MM-DD] — session ended (no significant changes captured)`, (b) 2nd+ occurrences of exact-duplicate `### YYYY-MM-DD …` blocks. Nothing else, ever.
- Every modified memory file gets a timestamped backup in `/tmp/claude-1000/-home-ntdst/phase2-memory-backups/<ts>/` (NOT next to the file) BEFORE the write. Do not reboot before Phase A verification; git-tracked files have git history as second safety net.
- Where a memory file is git-tracked, commit with exactly: `chore(memory): strip stop-hook noise (phase-2 cleanup)` — commit ONLY the memory path(s), never `git add -A` (several trees are dirty). Commit on whatever branch is checked out. Do NOT push site repos.
- netdust-plugins working tree is dirty (` M .gitignore`, untracked `memory/`) — pre-existing, leave both untouched and uncommitted.
- `bash plugins/netdust-agent/tests/run.sh` must be green at every Phase C commit. Baseline recorded 2026-07-03: agent 9/9 modules, core 5/5 (one skip-neutralized).
- netdust-core must remain installable after hooks/ deletion (precedent: netdust-wp and netdust-statamic ship no hooks/ dir at all).

## Gate record (planner, 2026-07-03)

- **1a Threat model — does NOT fire.** Trigger list walked literally: no user-controlled URLs, no auth/session/token surface, no untrusted parsing (all inputs are our own hook-generated files on local disk), no BYOK credentials, no tenancy boundary, no outbound request to a user-supplied address. Deletions, dedup of our own text, doc corrections, version bump.
- **1b Architecture invariants — does NOT fire.** No convergence point touched; no ARCHITECTURE-INVARIANTS.md exists in netdust-plugins and this cleanup is not the occasion to author one.
- **1g Feature acceptance — n/a.** No user-facing feature.
- **1c Ground-truthing — DONE 2026-07-03 ~14:00**; all counts/claims below are re-verified against disk (drift vs. the morning audit is flagged inline in each task).
- **doubting-decisions — not fired.** The core approach (one audited script, dry-run+backup+counts) is user-approved and mechanical; the only judgment calls (retire core tests after porting two modules; wp-manager STATE.md → header not delete) are argued inline in Tasks 3 and 7.

## Ground-truth deltas vs. the morning audit (premise drift)

1. **cargo STATE.md noise is 11, not ~122** (237 total lines).
2. **stride grew today**: 739 lines / 460 noise (was ~715/460); reshape worktree copy is 714/459 — both git-tracked, both committed clean, on different branches (`main` vs `feat/ntdst-output-layer`), content already diverged with REAL divergent material. They are independent tracked files; clean and commit each on its own branch (identical noise lines vanish from both, which shrinks future merge-conflict surface).
3. **Sweep found 8 additional noisy files** beyond the listed ones: netdust-plugins (1/7), atelier296 (1/70), bavi-jersey (2/14), bavi-sponsoring-vault (1/1), rossi (2/2), todai-client-form-intake (2/96), todai-client (9/207), vad-website (8/61).
4. **Duplicate `### … — tagged capture` blocks exist ONLY in `/home/ntdst/memory/STATE.md` (5×) and `/home/ntdst/memory/lessons.md` (5×)** — fleet-wide detector confirmed no other file has exact-dup blocks. Home `~/memory/` is NOT a git repo.
5. **Home STATE.md already got today's noise line** (`[2026-07-03] — session ended…`) — no real content appended today; safe to clean.
6. **bavi-jersey `tasks/lessons.md` holds FOUR hand-written lessons (all 2026-06-11), not one.** Migrate all four.
7. **stridelms `tasks/lessons.md` is UNtracked; ntdst-starter's is tracked** (byte-identical 767-byte templates).
8. **README.md "byte-identical" claim is at line 12, not ~L429** — README was rewritten to 188 lines in phase 1. Claim now doubly false: core and agent hook scripts DIFFER (agent's got the phase-1 fixes; core's are frozen).
9. **All five core test modules subprocess-run core's own hooks/** (`test_session_start.py`, `test_session_start_budget.py`, `test_pretooluse_guard.py`, `test_tag_scanner.py` [skip-neutralized at line 201 in phase 1], `test_stop_hook_idempotency.py`). Agent's 9-module suite already covers budget/idempotency/tag-scanner/dedup/no-auto-memory/subagent-stop/standards-gate — but has NO equivalent of `test_pretooluse_guard.py` or the general `test_session_start.py`. Those two must be PORTED to agent (they contain no `netdust-core` string assertions and use no fixtures; the guard-script diff vs agent is cosmetic name-strings only).
10. **Track B / Haiku is GONE from the live (agent) session-stop.py** (0 references; core's dead copy has 22). CLAUDE.md's Track B section describes a feature that no longer exists anywhere live → delete the section, don't repoint it.
11. **Versions confirmed:** marketplace core 0.2.2 / wp 0.4.1; installed core 0.2.2 / wp **0.4.0** (drift confirmed) / agent 0.3.1.
12. **`~/Sites/netdust-wp-manager/.no-auto-memory` exists at project root** (not inside memory/). `~/Sites/netdust-wp-manager/memory/GLOBAL.md` exists (4.4 KB) — the correct pattern-miner target.
13. **Hook .baks are unreferenced** (the only settings.local.json `.bak` mention is a different skills backup, timestamp 114244). Symlink `~/.claude/skills/create-agent-adapter` confirmed broken.
14. **Core has no install.sh**; the only normative hooks references are CLAUDE.md + README.md (docs/HANDOFF.md, docs/harness-engineering-*.md are historical records — leave them; `skills/research/SKILL.md`'s "hooks/" match is a wordpress.org URL, not ours).

---

## PHASE A — memory-file noise cleanup

### Task 1: Write the cleanup routine + fleet-wide dry-run

**Files:**
- Create: `/tmp/claude-1000/-home-ntdst/phase2-memory-backups/phase2-memory-cleanup.py` (tool script, lives outside all repos)

**Interfaces:**
- Produces: script with `--dry-run` (default) and `--apply` modes; Task 2 runs `--apply`.

**Test tier:** `no unit test: Tier B, one-shot data-cleanup tool; its gate is the dry-run diff below plus the backup + before/after counts recorded at apply time.`

- [ ] **Step 1: Write the script exactly as follows**

```python
#!/usr/bin/env python3
"""phase2-memory-cleanup.py — strip stop-hook noise + collapse exact-duplicate capture blocks.

Modes:
  (default)   dry-run: report per-file lines_before / noise / dup_blocks / lines_after; NO writes
  --apply     back up each changed file to BACKUP_DIR/<ts>/, then rewrite it

Only ever removes:
  1. lines exactly matching the stop-hook noise pattern
  2. the 2nd+ occurrence of an exact-duplicate '### YYYY-MM-DD ...' block
"""
import re, shutil, sys, time
from glob import glob
from pathlib import Path

NOISE = re.compile(r'^\[\d{4}-\d{2}-\d{2}\] — session ended \(no significant changes captured\)\s*$')
HEADER = re.compile(r'^### \d{4}-\d{2}-\d{2}')
BACKUP_DIR = Path('/tmp/claude-1000/-home-ntdst/phase2-memory-backups')
# netdust-wp-manager/memory/STATE.md is replaced wholesale by Task 3 — never script-edit it.
EXCLUDE = {Path('/home/ntdst/Sites/netdust-wp-manager/memory/STATE.md')}


def targets():
    pats = [
        '/home/ntdst/Sites/*/memory/STATE.md', '/home/ntdst/Sites/*/memory/lessons.md',
        '/home/ntdst/Projects/*/memory/STATE.md', '/home/ntdst/Projects/*/memory/lessons.md',
        '/home/ntdst/memory/STATE.md', '/home/ntdst/memory/lessons.md',
    ]
    found = sorted({p for pat in pats for p in glob(pat)})
    return [Path(p) for p in found if Path(p) not in EXCLUDE]


def clean(text):
    lines = text.split('\n')
    kept = [l for l in lines if not NOISE.match(l)]
    noise = len(lines) - len(kept)
    starts = [i for i, l in enumerate(kept) if HEADER.match(l)]
    if not starts:
        return '\n'.join(kept), noise, 0
    # a '---' separator directly above a header (blank lines between allowed) belongs to that block
    for idx in range(len(starts)):
        j = starts[idx] - 1
        while j >= 0 and kept[j].strip() == '':
            j -= 1
        if j >= 0 and kept[j].strip() == '---' and (idx == 0 or j > starts[idx - 1]):
            starts[idx] = j
    pre = kept[:starts[0]]
    blocks = [kept[starts[i]:(starts[i + 1] if i + 1 < len(starts) else len(kept))]
              for i in range(len(starts))]
    seen, out, dropped = set(), [], 0
    for b in blocks:
        key = '\n'.join(l.rstrip() for l in b if l.strip() and l.strip() != '---')
        if key in seen:
            dropped += 1
        else:
            seen.add(key)
            out.append(b)
    return '\n'.join(pre + [l for b in out for l in b]), noise, dropped


def main():
    apply = '--apply' in sys.argv
    ts = time.strftime('%Y%m%d-%H%M%S')
    changed = total_noise = total_dups = 0
    print(f"{'file':<68} before noise dups after")
    for f in targets():
        text = f.read_text()
        new, noise, dropped = clean(text)
        if noise == 0 and dropped == 0:
            continue
        changed += 1
        total_noise += noise
        total_dups += dropped
        print(f"{str(f):<68} {len(text.splitlines()):>5} {noise:>5} {dropped:>4} {len(new.splitlines()):>5}")
        if apply:
            bdir = BACKUP_DIR / ts
            bdir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, bdir / str(f).strip('/').replace('/', '__'))
            f.write_text(new)
    mode = 'APPLIED' if apply else 'DRY-RUN'
    print(f"\n[{mode}] files: {changed}  noise lines removed: {total_noise}  duplicate blocks dropped: {total_dups}")
    if apply:
        print(f"backups: {BACKUP_DIR / ts}")


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Dry-run**

Run: `mkdir -p /tmp/claude-1000/-home-ntdst/phase2-memory-backups && python3 /tmp/claude-1000/-home-ntdst/phase2-memory-backups/phase2-memory-cleanup.py`

Expected: ~17 changed files. Verify against this ground-truth table (counts as of 2026-07-03 ~14:00 — a session Stop between plan and execution may add ±1-2 noise lines per file; noise may only ever be HIGHER than listed, never lower; `dups` must be 0 everywhere except the two home files):

| file | before | noise | dups |
|---|---|---|---|
| /home/ntdst/memory/STATE.md | 40 | 10 | 4 |
| /home/ntdst/memory/lessons.md | 15 | 0 | 4 |
| /home/ntdst/Sites/stride/memory/STATE.md | 739 | 460 | 0 |
| /home/ntdst/Sites/stride-output-reshape/memory/STATE.md | 714 | 459 | 0 |
| /home/ntdst/Sites/todai/memory/STATE.md | 230 | 122 | 0 |
| /home/ntdst/Sites/cargo/memory/STATE.md | 237 | 11 | 0 |
| /home/ntdst/Sites/vad-vormingen/memory/STATE.md | 35 | 34 | 0 |
| /home/ntdst/Sites/fuse/memory/STATE.md | 13 | 12 | 0 |
| /home/ntdst/Projects/folio/memory/STATE.md | 328 | 77 | 0 |
| /home/ntdst/Projects/netdust-plugins/memory/STATE.md | 7 | 1 | 0 |
| /home/ntdst/Sites/atelier296/memory/STATE.md | 70 | 1 | 0 |
| /home/ntdst/Sites/bavi-jersey/memory/STATE.md | 14 | 2 | 0 |
| /home/ntdst/Sites/bavi-sponsoring-vault/memory/STATE.md | 1 | 1 | 0 |
| /home/ntdst/Sites/rossi/memory/STATE.md | 2 | 2 | 0 |
| /home/ntdst/Sites/todai-client/memory/STATE.md | 207 | 9 | 0 |
| /home/ntdst/Sites/todai-client-form-intake/memory/STATE.md | 96 | 2 | 0 |
| /home/ntdst/Sites/vad-website/memory/STATE.md | 61 | 8 | 0 |

(netdust-wp-manager 9/9 is EXCLUDED here — Task 3 replaces it wholesale.)

- [ ] **Step 3: STOP-condition check.** If any file shows `dups > 0` outside the two home files, or noise LOWER than the table, or an unexpected file with dups: STOP, diff that file by hand before applying. Do not weaken the script.

### Task 2: Apply, verify, commit where tracked

**Files:**
- Modify: the ~17 files from the Task 1 dry-run table

**Interfaces:**
- Consumes: `phase2-memory-cleanup.py --apply` from Task 1.

**Test tier:** `no unit test: Tier B, data cleanup; gate = backup existence + zero-noise grep + line-count math recorded below.`

- [ ] **Step 1: Apply**

Run: `python3 /tmp/claude-1000/-home-ntdst/phase2-memory-backups/phase2-memory-cleanup.py --apply`
Expected: same table as dry-run + `backups: /tmp/claude-1000/-home-ntdst/phase2-memory-backups/<ts>` line. Record the full output in the task report.

- [ ] **Step 2: Verify backups + zero residual noise + content preservation**

```bash
ls /tmp/claude-1000/-home-ntdst/phase2-memory-backups/*/ | wc -l   # expect ≈ changed-file count
grep -rl "session ended (no significant changes captured)" /home/ntdst/memory /home/ntdst/Sites/*/memory /home/ntdst/Projects/*/memory 2>/dev/null
# expect: NO output (wp-manager still pending Task 3 — it will appear until Task 3 runs; that one path is acceptable here)
grep -c "Tier 1.5 fixes" /home/ntdst/memory/STATE.md    # expect: 1 (was 5)
grep -c "under-triggers" /home/ntdst/memory/lessons.md  # expect: 1 (was 5)
head -30 /home/ntdst/Sites/stride/memory/STATE.md       # expect: real roadmap content intact, no noise lines
```

- [ ] **Step 3: Commit in each repo where the file is git-tracked** (ground-truthed list; commit ONLY the memory path, on the checked-out branch, no push):

```bash
for d in /home/ntdst/Sites/stride /home/ntdst/Sites/stride-output-reshape /home/ntdst/Sites/todai \
         /home/ntdst/Sites/vad-vormingen /home/ntdst/Projects/folio /home/ntdst/Sites/todai-client \
         /home/ntdst/Sites/todai-client-form-intake; do
  git -C "$d" add memory/STATE.md
  git -C "$d" commit -m "chore(memory): strip stop-hook noise (phase-2 cleanup)"
done
```

Branches (verified): stride=main, stride-output-reshape=feat/ntdst-output-layer, todai=master, vad-vormingen=staging, folio=feature/fleet-telemetry-sync, todai-client=feat/homepage-yootheme-rebuild, todai-client-form-intake=feat/form-intake-api.
Untracked or repo-less (backup-then-edit only, NO commit): home ~/memory (not a repo), cargo, bavi-jersey, atelier296 (no repo); fuse, vad-website, rossi, bavi-sponsoring-vault, netdust-plugins (file untracked).

- [ ] **Step 4: Verify each commit touched exactly one file**: `git -C <d> show --stat HEAD` per repo — expect `1 file changed`, deletions only.

### Task 3: netdust-wp-manager STATE.md → Layer-B header

**Decision (argued):** keep the file, don't delete. It is git-tracked on master (deleting churns history and invites a future hook/agent to recreate it blank); the dir is Layer-B manual-only and root-marker-protected (`.no-auto-memory` verified at project root). A 7-line pointer header makes the convention self-documenting.

**Files:**
- Modify: `/home/ntdst/Sites/netdust-wp-manager/memory/STATE.md` (tracked, branch master)

**Test tier:** `no unit test: Tier B, single-file content replacement; gate = marker check + committed diff.`

- [ ] **Step 1: Verify marker + back up**

```bash
ls /home/ntdst/Sites/netdust-wp-manager/.no-auto-memory   # must exist
cp /home/ntdst/Sites/netdust-wp-manager/memory/STATE.md /tmp/claude-1000/-home-ntdst/phase2-memory-backups/netdust-wp-manager__STATE.md.pre-task3
```

- [ ] **Step 2: Replace the whole file with exactly:**

```markdown
# Fleet memory — Layer B (manual only)

This directory is the manually-maintained fleet/business brain (Layer B).
No Stop hook writes here (project-root `.no-auto-memory`). Fleet state lives in:

- `GLOBAL.md` — cross-project rules and priorities
- `projects/<site>/STATE.md` — per-site fleet view

This file intentionally carries no state.
```

- [ ] **Step 3: Commit**

```bash
git -C /home/ntdst/Sites/netdust-wp-manager add memory/STATE.md
git -C /home/ntdst/Sites/netdust-wp-manager commit -m "chore(memory): strip stop-hook noise (phase-2 cleanup)"
```

- [ ] **Step 4: Fleet-wide zero-noise gate (Phase A integration gate)**

Run: `grep -rl "session ended (no significant changes captured)" /home/ntdst/memory /home/ntdst/Sites/*/memory /home/ntdst/Projects/*/memory 2>/dev/null; echo "exit=$?"`
Expected: no paths, `exit=1`.

**Integration gate (Phase A):** zero-noise grep above passes; apply-run table + backup path recorded in report; 8 site commits exist, each `1 file changed`.

`── REVIEW GATE ── (tier: LIGHT — data hygiene, verifiable by counts and grep; no code surface)`

---

## PHASE B — dead artifacts

### Task 4: Delete inert hook backups

**Files:**
- Delete: `/home/ntdst/.claude/hooks/session-start.sh.bak.20260517-112937`, `/home/ntdst/.claude/hooks/session-stop.py.bak.20260517-112937`

**Test tier:** `no unit test: Tier B, file deletion; gate = pre-delete reference grep + post-delete ls.`

- [ ] **Step 1: Re-confirm zero references (already ground-truthed, cheap to re-run):**
`grep -rn "bak.20260517-112937" /home/ntdst/.claude/settings.json /home/ntdst/.claude/settings.local.json` → expect no output.
- [ ] **Step 2:** `rm /home/ntdst/.claude/hooks/session-start.sh.bak.20260517-112937 /home/ntdst/.claude/hooks/session-stop.py.bak.20260517-112937`
- [ ] **Step 3:** `ls /home/ntdst/.claude/hooks/` → expect empty dir (these were its only two entries).

### Task 5: Stale tasks/lessons.md copies

**Files:**
- Delete: `/home/ntdst/Sites/stridelms/tasks/lessons.md` (UNtracked — plain rm)
- Delete: `/home/ntdst/Sites/ntdst-starter/tasks/lessons.md` (tracked — git rm + commit)
- Modify: `/home/ntdst/Sites/bavi-jersey/memory/lessons.md` (append), then delete `/home/ntdst/Sites/bavi-jersey/tasks/lessons.md` (no repo)

**Test tier:** `no unit test: Tier B, deletions + one content migration; gate = migrated text present via grep, sources gone.`

- [ ] **Step 1:** `rm /home/ntdst/Sites/stridelms/tasks/lessons.md`
- [ ] **Step 2:**

```bash
git -C /home/ntdst/Sites/ntdst-starter rm tasks/lessons.md
git -C /home/ntdst/Sites/ntdst-starter commit -m "chore: remove stale lessons.md template (phase-2 cleanup, wrongly titled 'Stride LMS')"
```

- [ ] **Step 3: Migrate ALL FOUR bavi-jersey lessons** (drift: audit said one; there are four, all hand-written 2026-06-11). Append to `/home/ntdst/Sites/bavi-jersey/memory/lessons.md`:

```markdown

### 2026-06-11 (migrated from tasks/lessons.md, phase-2 cleanup)
- **Match rendering realism, not just controls.** When cloning a visual tool
  (proline mockups), the photoreal garment render IS the product — a flat SVG with the same
  panels/tabs reads as a different tool. Before building, identify what makes the reference
  *sell* visually and plan that pipeline first. Fix: composite AI-generated fabric-shading
  (white garment photo → multiply blend) over the flat design layer, clipped to the design
  silhouette, so design stays vector/print-exact while preview looks like a photo.
- **Browser-automation page captures can send wheel/scroll events** into a
  canvas that implements wheel-zoom → screenshots show a "shrunken" app that users never see.
  Reset app zoom via eval before judging layout from automated screenshots.
- **"The design" meant the club's orange kit, not the WIP.** When a user says
  "get it back", confirm via the most recently *named* artifact, not the most recent edit.
- **Routine operations must be one command.** Pushing a saved design is one
  curl; don't wrap it in re-verification ceremony every time. Max effort ≠ max steps.
```

- [ ] **Step 4:** `rm /home/ntdst/Sites/bavi-jersey/tasks/lessons.md`
- [ ] **Step 5: Verify:** `grep -c "2026-06-11" /home/ntdst/Sites/bavi-jersey/memory/lessons.md` → ≥1; all three deleted paths return `ls: cannot access`.

### Task 6: Remove broken symlink

**Files:**
- Delete: `/home/ntdst/.claude/skills/create-agent-adapter` (symlink → gone target `/home/ntdst/Projects/kobe/paperclip/skills/create-agent-adapter`)

**Test tier:** `no unit test: Tier B, symlink removal; gate = post-delete ls.`

- [ ] **Step 1:** `test -e /home/ntdst/.claude/skills/create-agent-adapter || echo STILL-BROKEN` → expect `STILL-BROKEN` (re-confirm before deleting).
- [ ] **Step 2:** `rm /home/ntdst/.claude/skills/create-agent-adapter`
- [ ] **Step 3:** `ls -la /home/ntdst/.claude/skills/ | grep create-agent-adapter` → expect no output.

**Integration gate (Phase B):** all five artifact paths gone; ntdst-starter commit exists; bavi-jersey memory/lessons.md contains the migrated block.

`── REVIEW GATE ── (tier: LIGHT — tiny deletion/migration cluster; per plan brief this may be reviewed together with Phase A's cluster)`

---

## PHASE C — netdust-plugins repo bundle (branch off main)

All commands below run in `/home/ntdst/Projects/netdust-plugins`. Do NOT stage `.gitignore` or `memory/` (pre-existing dirt).

### Task 7: Port core-only tests to netdust-agent, delete core hooks/ + tests/

**Decision (argued):** core's five test modules all subprocess-run core's OWN dead hook copies. Agent's suite already covers budget/idempotency/tag-scanner (plus phase-1 dedup/no-auto-memory), but has NO pretooluse-guard test and NO general session-start test — those two are live-behavior coverage that must survive. So: port those two modules to agent (they reference hooks via relative `parent.parent/"hooks"`, contain no `netdust-core` string assertions, use no fixtures), then retire core's hooks/ AND tests/ entirely. Core keeps no executable code (skills/commands/MCP config only) → nothing left to test; run.sh is retired WITH the suite, justified. Deleting the whole `hooks/` dir (incl. `hooks.json`) is safe: netdust-wp and netdust-statamic ship no hooks/ dir and install fine.

**Files:**
- Create branch: `chore/phase2-repo-cleanup` off `main`
- Create: `plugins/netdust-agent/tests/test_pretooluse_guard.py`, `plugins/netdust-agent/tests/test_session_start.py` (copies of core's, docstring header s/netdust-core/netdust-agent/ only)
- Delete: `plugins/netdust-core/hooks/` (hooks.json, session-start.sh, session-stop.py, pretooluse-guard.py, __pycache__), `plugins/netdust-core/tests/` (all)

**Interfaces:**
- Produces: agent suite = 11 modules; Tasks 8–10 build on this branch.

**Test tier:** `Tier A — test contract: bash plugins/netdust-agent/tests/run.sh green at 11 modules, where the ported test_pretooluse_guard.py asserts the DENIAL path (destructive command blocked by the live agent guard) and test_session_start.py asserts the hook-fire log line is written even when memory files are missing.`

- [ ] **Step 1: Branch**

```bash
git -C /home/ntdst/Projects/netdust-plugins checkout -b chore/phase2-repo-cleanup main
```

- [ ] **Step 2: Port the two modules (RED-first equivalent — they run against agent's LIVE hooks before anything is deleted)**

```bash
cp plugins/netdust-core/tests/test_pretooluse_guard.py plugins/netdust-agent/tests/test_pretooluse_guard.py
cp plugins/netdust-core/tests/test_session_start.py    plugins/netdust-agent/tests/test_session_start.py
```

Then edit ONLY comment/docstring occurrences of "netdust-core" in the two new files (grep first: `grep -n "netdust-core" plugins/netdust-agent/tests/test_pretooluse_guard.py plugins/netdust-agent/tests/test_session_start.py` — ground truth says zero matches; if so, no edit needed). The `HOOK = Path(__file__).parent.parent / "hooks" / ...` lines resolve to agent's hooks automatically.

- [ ] **Step 3: Run agent suite — the ported tests must pass against the LIVE hooks**

Run: `bash plugins/netdust-agent/tests/run.sh`
Expected: `Modules passed: 11`, `Modules failed: 0`.
Known-safe drift: agent's pretooluse-guard.py differs from core's only in name strings (verified by diff); agent's session-start.sh gained the installed_plugins.json ACTIVE_MAP logic in phase 1 but the ported test asserts generic behavior (memory injection + log line). **If any ported test fails: STOP — superpowers:systematic-debugging; do not weaken assertions. A failure means live-hook behavior drifted from what phase-0 tests guarded, which is a finding, not a test bug. Escalation note: a failure here on the guard (a security-adjacent surface) promotes this cluster's review tier to FULL.**

- [ ] **Step 4: Delete core hooks + tests**

```bash
git -C /home/ntdst/Projects/netdust-plugins rm -r plugins/netdust-core/hooks plugins/netdust-core/tests
rm -rf plugins/netdust-core/hooks plugins/netdust-core/tests   # clears untracked __pycache__ leftovers
```

- [ ] **Step 5: Re-run agent suite**

Run: `bash plugins/netdust-agent/tests/run.sh` → `Modules passed: 11`. Also: `ls plugins/netdust-core/hooks plugins/netdust-core/tests 2>&1` → both "No such file or directory".

- [ ] **Step 6: Commit**

```bash
git -C /home/ntdst/Projects/netdust-plugins add plugins/netdust-agent/tests/test_pretooluse_guard.py plugins/netdust-agent/tests/test_session_start.py
git -C /home/ntdst/Projects/netdust-plugins commit -m "chore(core): retire dead hook copies + core test suite; port guard/session-start tests to netdust-agent

netdust-agent owns the live hooks since 0.3.x; core's copies were frozen
pre-phase-1 duplicates registered nowhere (hooks.json was {}). The two
core-only test modules move to netdust-agent where the hooks they exercise
live. Core keeps no executable code, so its test runner retires with it."
```

### Task 8: Fix core doc drift (CLAUDE.md, README.md, plugin.json description)

**Files:**
- Modify: `plugins/netdust-core/CLAUDE.md` (lines 9–10, 37, 39, 51–52)
- Modify: `plugins/netdust-core/README.md` (line 12 table row)
- Modify: `plugins/netdust-core/.claude-plugin/plugin.json` (description only; version waits for Task 10)

**Test tier:** `no unit test: Tier B, documentation; gate = drift-grep below returns clean.`

- [ ] **Step 1: CLAUDE.md line 9** — replace the "Memory + observability" bullet with:

```markdown
- **Memory + observability** — the per-project `memory/STATE.md` + `lessons.md` convention and its discipline. The live hooks that load and capture memory (SessionStart injector, Stop-hook `DECISION:`/`RISK:`/`LESSON:`/`TODO:` tag scanner, PreToolUse destructive-command guard) live in **netdust-agent** — core defines the memory convention; agent runs it. Every hook fire logs to `~/.claude/logs/memory-hook.log`.
```

- [ ] **Step 2: CLAUDE.md line 10** — delete the whole "Destructive-command guard" bullet (the guard is agent's; it is now named in the line-9 bullet).

- [ ] **Step 3: CLAUDE.md line 37** — replace the sentence opener `The SessionStart hook (`hooks/session-start.sh`) injects `memory/STATE.md`, `memory/lessons.md`, `tasks/todo.md`, the harness-level `GLOBAL.md` (which lives in netdust-agent, whose SessionStart hook is the live injector), and the site.yml summary` with:

```markdown
netdust-agent's SessionStart hook injects `memory/STATE.md`, `memory/lessons.md`, `tasks/todo.md`, the harness-level `GLOBAL.md`, and the site.yml summary
```

(rest of the paragraph unchanged).

- [ ] **Step 4: CLAUDE.md line 39** — replace `The Stop hook (`hooks/session-stop.py`) then captures memory` with `netdust-agent's Stop hook then captures memory` (rest unchanged). Also change the heading `**Track A — tagged capture (always on, deterministic, zero cost)**` to `**Tagged capture (always on, deterministic, zero cost)**` since Track B disappears next step.

- [ ] **Step 5: CLAUDE.md lines 51–52** — DELETE the entire "Track B — Haiku summary (opt-in)" heading + paragraph. Ground truth: the live agent session-stop.py has zero Haiku references; the feature no longer exists — do not repoint, remove.

- [ ] **Step 6: README.md line 12** — replace the "Memory + hooks" table row with:

```markdown
| **Memory + hooks** | Per-project `memory/STATE.md` + `lessons.md` + `tasks/todo.md` convention and memory discipline. The live hooks — SessionStart loader, Stop-hook `DECISION:`/`RISK:`/`LESSON:`/`TODO:` tag scanner, PreToolUse destructive-command guard — live in **netdust-agent** (registration AND scripts). Core ships no hook scripts. |
```

- [ ] **Step 7: plugin.json description** — in `plugins/netdust-core/.claude-plugin/plugin.json`, replace the description's opening clause `per-project memory (SessionStart load + Stop-hook DECISION:/RISK:/LESSON:/TODO: tag capture), the destructive-command PreToolUse guard,` with `the per-project memory convention (STATE/lessons/todo — live hooks in netdust-agent),` (rest of description unchanged).

- [ ] **Step 8: Drift-grep gate**

```bash
grep -rn "hooks/session-start\|hooks/session-stop\|hooks/pretooluse\|byte-identical\|Track B\|Haiku" \
  plugins/netdust-core/CLAUDE.md plugins/netdust-core/README.md plugins/netdust-core/.claude-plugin/plugin.json
```

Expected: no output. (docs/HANDOFF.md + docs/harness-engineering-*.md are historical records — intentionally NOT swept; see Sibling-site audit.)

- [ ] **Step 9: Commit** — `git add plugins/netdust-core/CLAUDE.md plugins/netdust-core/README.md plugins/netdust-core/.claude-plugin/plugin.json && git commit -m "docs(core): netdust-agent owns the live hooks — fix CLAUDE/README/plugin.json drift, drop dead Track B section"`

### Task 9: Repoint pattern-miner GLOBAL.md reference (both copies)

**Files:**
- Modify: `plugins/netdust-core/commands/pattern-miner.md:10`
- Modify: `plugins/netdust-agent/commands/pattern-miner.md:10`

**Ground truth:** the command mines `~/Sites/*/memory/{STATE,lessons}.md` for promotable patterns; its "new entry in GLOBAL.md" output target `~/.claude/plugins/netdust-wp/memory/GLOBAL.md` never existed. The correct target is the Layer-B fleet file `~/Sites/netdust-wp-manager/memory/GLOBAL.md` (exists, 4.4 KB — cross-project rules, exactly what mined patterns are). Line 40's bare "add to GLOBAL.md" mention is contextual and correct once line 10 defines the path. The two file copies DIFFER elsewhere — edit only line 10 in each, do not sync the files.

**Test tier:** `no unit test: Tier B, doc/command copy fix; gate = grep below.`

- [ ] **Step 1:** In BOTH files, replace line 10 `- A new entry in `~/.claude/plugins/netdust-wp/memory/GLOBAL.md`` with:

```markdown
- A new entry in `~/Sites/netdust-wp-manager/memory/GLOBAL.md` (the manually-maintained Layer-B fleet memory)
```

- [ ] **Step 2: Gate:** `grep -rn "netdust-wp/memory" plugins/` → expect no output.
- [ ] **Step 3: Commit** — `git add plugins/netdust-core/commands/pattern-miner.md plugins/netdust-agent/commands/pattern-miner.md && git commit -m "fix(commands): pattern-miner GLOBAL.md target never existed — repoint to Layer-B fleet file"`

### Task 10: Version bump 0.2.3, ship, clear netdust-wp drift

**Files:**
- Modify: `plugins/netdust-core/.claude-plugin/plugin.json` (`"version": "0.2.2"` → `"0.2.3"`)
- Modify: `.claude-plugin/marketplace.json` (netdust-core entry: `"version": "0.2.2"` → `"0.2.3"`; ALSO update its `description` field's opening clause `per-project memory (load + tag-capture hooks), destructive-command guard,` → `the per-project memory convention (live hooks in netdust-agent),`)

**Test tier:** `no unit test: Tier B, config/delivery; gate = installed_plugins.json shows core 0.2.3 AND wp 0.4.1 after update.`

- [ ] **Step 1:** Make both version edits + the marketplace description edit.
- [ ] **Step 2: Commit + merge + push**

```bash
git add plugins/netdust-core/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore(release): netdust-core 0.2.3 — dead hooks removed, docs repointed"
git checkout main && git merge --no-ff chore/phase2-repo-cleanup -m "merge: phase-2 memory-cleanup repo bundle (core 0.2.3)"
git push
```

(Confirm `git status` afterwards still shows ONLY ` M .gitignore` + `?? memory/` + `?? plans/…` — nothing of ours left unstaged.)

- [ ] **Step 3: Update installed plugins**

```bash
claude plugin update netdust-core@netdust-plugins
claude plugin update netdust-wp@netdust-plugins   # clears pre-existing 0.4.0 → 0.4.1 drift; no repo change
```

- [ ] **Step 4: Verify**

```bash
python3 -c "
import json
d = json.load(open('/home/ntdst/.claude/plugins/installed_plugins.json'))
for k, v in d['plugins'].items():
    if 'netdust' in k:
        print(k, '->', v[0]['version'])
"
```

Expected: `netdust-core -> 0.2.3`, `netdust-wp -> 0.4.1`, agent 0.3.1 and statamic 0.1.1 unchanged. Also `ls <core installPath>/hooks 2>&1` → "No such file or directory" (confirms the installed copy really lost the dead hooks) and a fresh `claude` session in any project still fires memory injection (agent hooks) — spot-check the log: `tail -3 ~/.claude/logs/memory-hook.log` after opening one session.

**Integration gate (Phase C):** agent suite 11/11 green on main after merge; installed versions verified; hook log still receiving fires (live behavior unbroken by core deletion).

`── REVIEW GATE ── (tier: STANDARD — multi-file behavior-adjacent deletions in a shipped plugin + delivery; no 1a surface. Escalation: any Step-3 guard-test failure in Task 7 promotes to FULL.)`

---

## Sibling-site audit

- **pattern-miner.md exists in TWO commands dirs** (core + agent, contents differ) — Task 9 edits line 10 in BOTH; the gate grep is repo-wide so a missed sibling fails loudly.
- **Hook references in core docs**: normative sites (CLAUDE.md, README.md, plugin.json, marketplace.json) are all swept by Tasks 8/10 with a closing grep. `docs/HANDOFF.md`, `docs/harness-engineering-course-eval.md`, `docs/harness-engineering-hardening-plan.md` reference hooks/ as HISTORICAL records of past states — intentionally excluded (rewriting history docs falsifies them). `skills/research/SKILL.md`'s match is a wordpress.org URL — not ours.
- **Noise pattern sites**: the script's glob (Sites/* + Projects/* + home, both STATE.md and lessons.md) is the sibling sweep for item-A; the Phase-A closing grep covers the same span.
- **"byte-identical" claim**: single site (README L12), swept Task 8 with grep.

## Self-review record (writing-plans checklist)

- Spec coverage: items 1–10 of the brief map to Tasks 1–3 (items 1–3), 4–6 (items 4–6), 7–10 (items 7–10). Gates 1a/1c/1d/1f/1g addressed in the Gate record + per-task tier lines + review markers.
- Placeholders: none — script code, replacement texts, and commands are complete.
- Consistency: script path, backup dir, branch name, and commit messages are used identically across tasks.
