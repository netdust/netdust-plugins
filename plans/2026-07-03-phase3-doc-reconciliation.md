# Phase 3 — Reconcile Docs with Reality — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Stefan's global CLAUDE.md and the netdust-plugins repo docs factually match the post-phase-1/2 reality (netdust-agent 0.3.1 owns all live hooks, netdust-core 0.2.3 is hook-less, `.no-auto-memory` marker exists, dead install.sh flow removed).

**Architecture:** Pure documentation reconciliation, three independent parts: (A) minimal factual edits to the untracked user-global `~/.claude/CLAUDE.md` (backup-before-edit), (B) close the Class E audit finding — half no-op with evidence, half a one-line planner.md fix + version bump, (C) stale-reference sweep across plugin READMEs/CLAUDE.md in this repo (ride-along commit, no version bump).

**Tech Stack:** Markdown, grep, git. No runtime code changes except `agents/planner.md` persona text (Part B).

**Work class:** A (multi-task, multi-part change with its own plan and review clusters).

## Global Constraints

- **Scope guard (Part A):** fix factual drift ONLY in `~/.claude/CLAUDE.md` — no rewriting of working rules, tone, or structure; every edit is a minimal string replacement.
- `~/.claude/CLAUDE.md` is NOT git-tracked (verified: no repo at `~/.claude`) → backup before first edit, phase-2 pattern.
- Part C is a ride-along docs commit in `/home/ntdst/Projects/netdust-plugins` — **NO version bumps** for Part C.
- Part B's planner.md edit changes agent-persona behavior text → **netdust-agent 0.3.1 → 0.3.2** in BOTH `plugins/netdust-agent/.claude-plugin/plugin.json:3` AND `.claude-plugin/marketplace.json:23` (cache dirs are version-keyed — verified `~/.claude/plugins/cache/netdust-plugins/netdust-agent/{0.2.0,0.2.1,0.3.0,0.3.1}`; an unbumped edit does not propagate).
- Historical docs are exempt from the sweep: `plugins/netdust-core/docs/HANDOFF.md` (dated handoff snapshot; `netdust-local` hits at L15/33/34/35 stay).
- Repo is a git repo on `main` tracking `origin/main` (verified) — commit per cluster; do not touch the pre-existing dirty `.gitignore` / untracked `memory/`.

---

## Gate decisions (planner, Class A)

| Gate | Fires? | Trigger walk |
|---|---|---|
| **1a threat-modeling** | **NO** | Walked literally: no user-controlled URLs, no auth/session/token surface, no untrusted parsing, no BYOK credentials, no tenancy/workspace boundary, no outbound request to user-supplied address. Markdown docs only. |
| **1b architecture-invariants** | **NO** | No `ARCHITECTURE-INVARIANTS.md` convergence point touched; no authorization/data-access/live-update/error-handling/entity code changed. |
| **designing-apis** | **NO** | No API or module boundary designed. |
| **1g feature-acceptance** | **NO** | No user-facing feature, view, flow, or client-driven endpoint. |
| **1c ground-truthing** | **DONE** | Every line number and claim below verified against disk 2026-07-03 (evidence inline per task). Premise drift found is listed at the bottom. |
| **doubting-decisions** | **NO** | No big architectural decision — the only judgment calls (planner.md E-row, version bump, review tiers) are recorded inline with rationale. |
| **1d testing-workflow** | Applied | Every task is **Tier B** (docs) — verification = grep gates, no unit tests. |
| **1f/1h review sizing** | Applied | Three clusters, each ≤ 4 tasks, tiers argued at each `── REVIEW GATE ──`. |

**Part B verdict (audit-close): SPLIT.**
- `plugins/netdust-agent/skills/harnessed-development/SKILL.md` **contains the full Class E intake row at line 60** — and so does the installed 0.3.1 cache (same line). The morning audit's SKILL.md claim was version-skew fallout (auditor read the stale pre-phase-1 copy). → **NO-OP, recorded with evidence in Task 4.**
- `plugins/netdust-agent/agents/planner.md:13` classifies **A/B/C/D only — in the repo AND in the installed 0.3.1 cache**. This half is **REAL**, not skew. → **Task 5 fixes it.**

---

## Cluster 1 — Part A: `~/.claude/CLAUDE.md` factual reconciliation

### Task 1: Backup + lesson-location fixes

**Files:**
- Create: `/home/ntdst/.claude/CLAUDE.md.bak-2026-07-03` (backup copy)
- Modify: `/home/ntdst/.claude/CLAUDE.md:51` and `:86`

**Interfaces:**
- Produces: backed-up original; `memory/lessons.md` as the only lesson path in the file. Tasks 2–3 edit the same file and assume the backup already exists.

`no unit test: Tier B, documentation-only edit; verification = grep steps below`

Ground truth (read 2026-07-03): exactly two `tasks/lessons.md` occurrences exist — L51 (§3 Self-Improvement Loop) and L86 (Task Management item 6). The netdust-agent Stop hook (`plugins/netdust-agent/hooks/session-stop.py:12`) routes `LESSON:` → `memory/lessons.md`; 24 real projects use `memory/lessons.md`; phase 2 deleted the last `tasks/lessons.md` copies. Note: `tasks/todo.md` references (L81, L85, L174) are CORRECT (hook routes `TODO:` → `tasks/todo.md`, session-start.sh:224 reads `$CWD/tasks/todo.md`) — do NOT touch them.

- [ ] **Step 1: Backup the untracked file**

```bash
cp /home/ntdst/.claude/CLAUDE.md /home/ntdst/.claude/CLAUDE.md.bak-2026-07-03
ls -la /home/ntdst/.claude/CLAUDE.md.bak-2026-07-03
```
Expected: backup file exists, 10796 bytes (same size as original).

- [ ] **Step 2: Fix line 51** — replace exactly:

Old: `- After ANY correction from the user, update `tasks/lessons.md` with the pattern`
New: `- After ANY correction from the user, update `memory/lessons.md` with the pattern`

- [ ] **Step 3: Fix line 86** — replace exactly:

Old: `6. **Capture Lessons**: Update `tasks/lessons.md` after corrections`
New: `6. **Capture Lessons**: Update `memory/lessons.md` after corrections`

- [ ] **Step 4: Verify no occurrence remains**

```bash
grep -n "tasks/lessons.md" /home/ntdst/.claude/CLAUDE.md
```
Expected: no output (exit 1). And confirm `tasks/todo.md` untouched: `grep -c "tasks/todo.md" /home/ntdst/.claude/CLAUDE.md` → `3`.

### Task 2: Skill Architecture tables — ghost skills, namespacing, plugin status

**Files:**
- Modify: `/home/ntdst/.claude/CLAUDE.md:100-101` (Plugins table), `:108-115` (NTDST table), `:138` (Paperclip table), `:154-155` (Replacements table)

**Interfaces:**
- Consumes: backup from Task 1 (do not re-backup).
- Produces: tables containing only skill names that resolve on disk today.

`no unit test: Tier B, documentation-only edit; verification = grep steps below`

Ground truth (verified 2026-07-03):
- `~/.claude/skills/` contains NO `code-audit`, `ntdst-infra`, `mainwp`, `create-agent-adapter`, or bare `testing-workflow` (full listing taken; `create-agent-adapter` symlink was deleted in phase 2).
- Real skills: `netdust-wp:wp-infra` (repo `plugins/netdust-wp/skills/wp-infra/` — WP-CLI, Vite-for-WP, Bedrock Makefile), `netdust-core:ploi` (repo `plugins/netdust-core/skills/ploi/` — server/fleet ops), `netdust-agent:testing-workflow` (repo `plugins/netdust-agent/skills/testing-workflow/`). `netdust-agent/skills/` has NO code-audit; review reality = `/code-review` + the netdust-agent reviewer agents (`agents/reviewer.md` + specialists).
- `ntdst-architecture`, `ntdst-data`, `ntdst-patterns`, `ntdst-yootheme` all exist — but only namespaced under `netdust-wp:` (repo `plugins/netdust-wp/skills/`). §0b (L21) already fully qualifies netdust plugin skills (`netdust-wp:wp-plan-requirements`) — that is the file's own precedent, so **decision: qualify, don't leave bare**.
- `~/.claude/settings.json:30`: `"ui-ux-pro-max@ui-ux-pro-max-skill": false` (disabled). `claude-mem` absent from `enabledPlugins` entirely (only its marketplace `thedotmack` is registered, settings.json:44-49). **Decision per brief: the table describes intent — flag status in-place, do not delete the rows.**

- [ ] **Step 1: Plugins table status flags (L100–101)** — replace the two rows:

Old L100: `| `ui-ux-pro-max` | Design intelligence: 50+ styles, palettes, font pairings, component systems |`
New: `| `ui-ux-pro-max` | Design intelligence: 50+ styles, palettes, font pairings, component systems — *currently disabled in settings.json; re-enable before relying on it* |`

Old L101: `| `claude-mem` | Persistent cross-session memory, AST search, timeline |`
New: `| `claude-mem` | Persistent cross-session memory, AST search, timeline — *marketplace registered but plugin not currently installed/enabled* |`

- [ ] **Step 2: NTDST table (L108–115)** — replace rows as follows (row order preserved):

```
| Planning architecture | `netdust-wp:ntdst-architecture` |
| Data models & APIs | `netdust-wp:ntdst-data` |
| Infra & deployment | `netdust-wp:wp-infra` (WP infra); server/fleet ops: `netdust-core:ploi` |
| YOOtheme integration | `netdust-wp:ntdst-yootheme` |
| Feature / architecture design | `netdust-wp:ntdst-architecture` + `netdust-wp:ntdst-data` + `netdust-wp:ntdst-patterns` |
| Code review | `/code-review` + the netdust-agent reviewer agents |
| Testing | `netdust-agent:testing-workflow` |
```
The `| Site management | `mainwp` |` row (L115) is **deleted** — no such skill exists anywhere and nothing replaces it.

- [ ] **Step 3: Paperclip table (L138)** — delete the row `| Creating adapters | `create-agent-adapter` |` (symlink target gone, retired in phase 2). Keep the other two rows.

- [ ] **Step 4: Replacements table (L154–155)** — replace:

Old L154: `| `testing-workflow` | `superpowers:test-driven-development` |`
New: `| `netdust-agent:testing-workflow` | `superpowers:test-driven-development` |`

Old L155: `| `ntdst-architecture` + `ntdst-data` + `ntdst-patterns` | `superpowers:brainstorming` (for WordPress design/planning — WP work skips generic brainstorming in favor of the framework design skills) |`
New: `| `netdust-wp:ntdst-architecture` + `netdust-wp:ntdst-data` + `netdust-wp:ntdst-patterns` | `superpowers:brainstorming` (for WordPress design/planning — WP work skips generic brainstorming in favor of the framework design skills) |`

- [ ] **Step 5: Verify ghost names gone**

```bash
grep -n "code-audit\|ntdst-infra\|mainwp\|create-agent-adapter" /home/ntdst/.claude/CLAUDE.md
grep -n '`testing-workflow`' /home/ntdst/.claude/CLAUDE.md
```
Expected: first grep no output. Second grep no output (only `netdust-agent:testing-workflow` forms remain — confirm with `grep -c "netdust-agent:testing-workflow" /home/ntdst/.claude/CLAUDE.md` → `2`).

### Task 3: Memory System section accuracy sweep

**Files:**
- Modify: `/home/ntdst/.claude/CLAUDE.md:174` (Layer C row), `:178` (Layer B paragraph), `:196` (footnote)

**Interfaces:**
- Consumes: backup from Task 1.
- Produces: Memory System section attributing hooks to netdust-agent and naming the `.no-auto-memory` mechanism.

`no unit test: Tier B, documentation-only edit; verification = grep steps below`

Ground truth (verified 2026-07-03):
- The Stop hook lives in **netdust-agent** (`plugins/netdust-agent/hooks/hooks.json` registers `session-stop.py` on Stop; netdust-core 0.2.3 ships no hooks — its plugin.json self-describes "live hooks in netdust-agent"). L174's "netdust-core Stop hook" is stale.
- `.no-auto-memory` marker exists at `/home/ntdst/Sites/netdust-wp-manager/.no-auto-memory`; `session-stop.py:44` defines `NO_AUTO_MEMORY_MARKER = ".no-auto-memory"` ("at a project root: hook must not write there") and skips at `:533-538`. L178's "NOT written by any hook" is now true again — add the mechanism parenthetical.
- `compounding` lives in **netdust-agent** (`plugins/netdust-agent/skills/compounding/`; netdust-core/skills has no compounding). L196 footnote is stale.
- Checked, NO change needed: Layer C paths (`memory/STATE.md`, `lessons.md`, `tasks/todo.md`) match session-stop.py routing exactly; Layer A and B paths unchanged; §0b's named skills all exist (`netdust-wp:wp-plan-requirements` ✓, `ntdst-*` domain skills ✓ under netdust-wp, `shakeout-qa` agent ✓ at `plugins/netdust-agent/agents/shakeout-qa.md`), so §0b needs no edit.

- [ ] **Step 1: Fix Layer C attribution (L174)** — replace exactly:

Old: `| **netdust-core Stop hook** (`DECISION:`/`RISK:`/`LESSON:`/`TODO:` tags) |`
New: `| **netdust-agent Stop hook** (`session-stop.py`; `DECISION:`/`RISK:`/`LESSON:`/`TODO:` tags) |`

- [ ] **Step 2: Name the Layer B guard mechanism (L178)** — replace exactly:

Old: `**Layer B is manual and intentional** — it is NOT written by any hook, and that's correct: it's the fleet/business brain.`
New: `**Layer B is manual and intentional** — it is NOT written by any hook (enforced by the `.no-auto-memory` marker file at the workspace root; the netdust-agent Stop hook skips any project root containing it), and that's correct: it's the fleet/business brain.`

- [ ] **Step 3: Fix compounding footnote (L196)** — replace `netdust-core:compounding` with `netdust-agent:compounding`.

- [ ] **Step 4: Cluster-1 Integration gate — final consistency grep**

```bash
grep -n "tasks/lessons.md\|code-audit\|ntdst-infra\|mainwp\|create-agent-adapter\|netdust-core:compounding\|netdust-core Stop hook" /home/ntdst/.claude/CLAUDE.md
diff /home/ntdst/.claude/CLAUDE.md.bak-2026-07-03 /home/ntdst/.claude/CLAUDE.md | grep "^[<>]" | wc -l
```
Expected: first grep no output. Second: a small line count (~30 changed lines total) — eyeball the full `diff` to confirm ONLY the lines named in Tasks 1–3 changed (scope guard: no working rule, tone, or structure edits).

`── REVIEW GATE ── (tier: STANDARD — docs-only by content, but this is the user's global instruction file steering every future session across all projects, it is untracked (backup is the only revert path), and a wrong edit here has outsized blast radius. 2 finders: one correctness pass verifying each replacement against the ground-truth evidence above, one scope-guard pass verifying the diff contains nothing beyond the named minimal replacements. No browser pass — substitute the Step-4 consistency grep. Escalation is one-way; no 1a surface exists, so FULL cannot be warranted.)`

---

## Cluster 2 — Part B: Class E audit finding — half no-op, half real

### Task 4: Record the SKILL.md no-op with evidence (closes the audit finding as version-skew fallout)

**Files:**
- Modify: this plan file (check the boxes below); evidence also goes in Task 5's commit message.

`no unit test: Tier B, verification-record only; the steps ARE the gate`

- [x] **Step 1: Re-verify the repo copy has Class E**

```bash
grep -n "^| \*\*E" /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/skills/harnessed-development/SKILL.md
```
Expected: one hit at **line 60**: `| **E — Small self-contained change, no plan warranted** … | **Go straight to Stage 2 as one TDD cycle.** … |`

- [x] **Step 2: Re-verify the installed 0.3.1 cache has the same row**

```bash
grep -n "^| \*\*E" /home/ntdst/.claude/plugins/cache/netdust-plugins/netdust-agent/0.3.1/skills/harnessed-development/SKILL.md
```
Expected: one hit at line 60, identical text.

- [x] **Step 3: Record the verdict** — check this box to record: *SKILL.md intake table Class E finding = NO-OP; the morning auditor read a stale pre-phase-1 copy (version-skew bug fixed in phase 1). Evidence: E row present at line 60 in repo AND 0.3.1 cache, verified 2026-07-03.* Emit `DECISION: Class E SKILL.md audit finding closed as version-skew fallout — E row present in repo + 0.3.1 cache (phase 3, Task 4)` in the session transcript so the Stop hook captures it.

### Task 5: Add Class E to planner.md classification + bump netdust-agent 0.3.2

**Files:**
- Modify: `/home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/agents/planner.md:13`
- Modify: `/home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/.claude-plugin/plugin.json:3`
- Modify: `/home/ntdst/Projects/netdust-plugins/.claude-plugin/marketplace.json:23`

**Interfaces:**
- Produces: planner persona that recognizes Class E and bounces it back instead of misfiling a tweak as Class A/C. Version 0.3.2 in both manifests (sibling-site audit: the version lives in TWO files — plugin.json AND marketplace.json).

`no unit test: Tier B, agent-persona text + version strings; verification = grep steps below`

Ground truth (verified 2026-07-03): planner.md:13 reads `**1. Classify the work first (A/B/C/D), in one sentence, before anything else.**` and enumerates only A–D — in the repo AND in the 0.3.1 cache. This is genuinely missing, not skew. Design note honored by the edit: Class E work should never REACH a planner (E = no plan), so the correct planner behavior is to recognize E and hand it back, not to plan it. Source text for E's definition: SKILL.md line 60 (cache and repo identical).

- [x] **Step 1: Replace planner.md line 13** with exactly:

```
**1. Classify the work first (A/B/C/D/E), in one sentence, before anything else.** This determines which stages fire. New feature / multi-task = A (Stage 0→1→2→3). Executing an existing plan = B (Stage 1 freshness review first). Bug-fix bundle = C. Ad-hoc security-boundary edit = D (security gate only). Small self-contained change, no plan warranted (a logic tweak, a small helper, a localized refactor — one area, no design questions, NOT a security-boundary file) = E: do NOT write a plan — report back that this is Class E and belongs in a single TDD cycle (red/green + test-evidence), per the harnessed-development intake table. If you cannot classify, the request is ambiguous — ask, do not improvise.
```

- [x] **Step 2: Bump both version sites 0.3.1 → 0.3.2**

In `plugins/netdust-agent/.claude-plugin/plugin.json:3`: `"version": "0.3.1"` → `"version": "0.3.2"`.
In `.claude-plugin/marketplace.json:23`: `"version": "0.3.1"` → `"version": "0.3.2"`.

Rationale (decided at plan time): planner.md is persona behavior loaded from the version-keyed cache (`~/.claude/plugins/cache/netdust-plugins/netdust-agent/<version>/`); without a bump the fix does not propagate on `claude plugin update`. This is the ONLY version bump in phase 3 — Part C stays unbumped.

- [ ] **Step 3: Verify**

```bash
grep -n "A/B/C/D/E" /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/agents/planner.md
grep -rn '"version": "0.3.2"' /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/.claude-plugin/plugin.json /home/ntdst/Projects/netdust-plugins/.claude-plugin/marketplace.json
grep -rn "0.3.1" /home/ntdst/Projects/netdust-plugins/plugins/netdust-agent/.claude-plugin/plugin.json /home/ntdst/Projects/netdust-plugins/.claude-plugin/marketplace.json
```
Expected: hit on planner.md:13; two 0.3.2 hits; zero remaining 0.3.1 hits in those two files.

- [ ] **Step 4: Commit (Cluster-2 Integration gate)**

```bash
cd /home/ntdst/Projects/netdust-plugins && git add plugins/netdust-agent/agents/planner.md plugins/netdust-agent/.claude-plugin/plugin.json .claude-plugin/marketplace.json && git commit -m "fix(netdust-agent): planner persona classifies A-E, bounces Class E back (0.3.2)

Closes the morning audit's Class E finding: SKILL.md half was a no-op
(version-skew artifact — E row present at line 60 in repo and 0.3.1 cache);
planner.md half was real (A/B/C/D only, in repo AND cache). Planner now
recognizes Class E and reports it back for a direct TDD cycle instead of
planning it.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
Expected: commit contains exactly 3 files.

`── REVIEW GATE ── (tier: LIGHT — single generalist pass; agent-body/manifest text only, no 1a surface, no invariant, no data layer. Reviewer checks: the E sentence matches the SKILL.md line-60 semantics (bounce-back, not plan-it), and both version sites moved together.)`

---

## Cluster 3 — Part C: repo doc deferrals (ride-along commit, NO version bump)

### Task 6: netdust-core — stale `netdust-local` refs + ghost `code-audit` in the gate-skill lists

**Files:**
- Modify: `/home/ntdst/Projects/netdust-plugins/plugins/netdust-core/README.md:37,147,148`
- Modify: `/home/ntdst/Projects/netdust-plugins/plugins/netdust-core/CLAUDE.md:17`

`no unit test: Tier B, documentation-only; verification = Task 8 sweep grep`

Ground truth (verified 2026-07-03): README L147–148 (Roll back section) reads `/plugin disable netdust-core@netdust-local` and `enabledPlugins.netdust-core@netdust-local` — the marketplace is `netdust-plugins` (README L22–31, the phase-2 pattern, already correct). ADDITIONALLY (drift found during 1c, same factual class): README L37 and CLAUDE.md L17 both list `code-audit` among netdust-agent's gate skills — `plugins/netdust-agent/skills/` contains no code-audit (full listing verified; review is done by the reviewer agents + `/code-review`).

- [ ] **Step 1: Fix README.md:147–148** — replace both `netdust-local` with `netdust-plugins`:

```
#   /plugin disable netdust-core@netdust-plugins
# OR in ~/.claude/settings.json set enabledPlugins.netdust-core@netdust-plugins to false.
```

- [ ] **Step 2: Remove ghost `code-audit`** — in README.md:37 AND CLAUDE.md:17, change the parenthetical list `(threat-modeling, architecture-invariants, feature-acceptance, testing-workflow, test-effectiveness, shake-out, compounding, code-audit)` → `(threat-modeling, architecture-invariants, feature-acceptance, testing-workflow, test-effectiveness, shake-out, compounding)` (identical text in both files).

### Task 7: netdust-wp README — replace dead git-clone + install.sh flow with the marketplace flow

**Files:**
- Modify: `/home/ntdst/Projects/netdust-plugins/plugins/netdust-wp/README.md:16-27,58,99`

`no unit test: Tier B, documentation-only; verification = Task 8 sweep grep`

Ground truth (verified 2026-07-03): `plugins/netdust-wp/install.sh` does NOT exist on disk. README Install section (L16–27) still documents `git clone <repo> ~/.claude/plugins/netdust-wp` + `bash ~/.claude/plugins/netdust-wp/install.sh` + the `netdust-local` marketplace; Layout tree L58 lists `install.sh`; L99 says "The soft-dep check in install.sh warns but doesn't enforce." Mirror the pattern phase 2 put in core's README (L20–31).

- [ ] **Step 1: Replace the Install section body (L18–27)** with:

```markdown
**Install netdust-core first.** Then, with the marketplace already added (`claude plugin marketplace add netdust/netdust-plugins`):

```bash
claude plugin install netdust-wp@netdust-plugins
```

Restart Claude Code to pick it up. To update later: `claude plugin update netdust-wp@netdust-plugins`.

Skills, commands, templates load **directly from the installed plugin directory** via Claude Code's plugin loader (`${CLAUDE_PLUGIN_ROOT}`). This plugin ships no `install.sh` — installation and updates go through `claude plugin` commands against the `netdust-plugins` marketplace.
```

(Keep the `## Install` heading and the surrounding sections untouched.)

- [ ] **Step 2: Remove the Layout tree line 58** `├── install.sh                       (soft-dep check on netdust-core)` (delete the line; keep the tree otherwise intact).

- [ ] **Step 3: Fix L99** — replace the final sentence `The soft-dep check in install.sh warns but doesn't enforce.` with `The dependency is soft — nothing enforces it at install time.`

### Task 8: netdust-statamic README — same treatment + repo-wide sweep gate

**Files:**
- Modify: `/home/ntdst/Projects/netdust-plugins/plugins/netdust-statamic/README.md:~16-22,48,82,107`

`no unit test: Tier B, documentation-only; verification = sweep grep below`

Ground truth (verified 2026-07-03): `plugins/netdust-statamic/install.sh` does NOT exist. README hits: L19 (`bash …/install.sh`), L22 (`netdust-local` marketplace sentence), L48 (Layout tree `install.sh`), L82 ("soft-dep check in install.sh"), L107 ("all coexist in the shared `netdust-local` marketplace"). These are normative install docs → fix. NO version bump (0.1.1 stays).

- [ ] **Step 1: Apply the Task-7 pattern** to the statamic README Install section (read L14–25 first; the wording mirrors netdust-wp's, so apply the same replacement with `netdust-statamic` substituted), delete the L48 tree line, reword L82's install.sh sentence identically to Task 7 Step 3, and in L107 replace `` the shared `netdust-local` marketplace `` with `` the `netdust-plugins` marketplace ``.

- [ ] **Step 2: Cluster-3 Integration gate — sweep grep**

```bash
grep -rn "netdust-local" /home/ntdst/Projects/netdust-plugins/plugins/ --include="*.md" | grep -v "docs/HANDOFF.md"
grep -rn "install\.sh" /home/ntdst/Projects/netdust-plugins/plugins/*/README.md /home/ntdst/Projects/netdust-plugins/plugins/*/CLAUDE.md
```
Expected: first grep — no output (HANDOFF.md is the exempt historical doc). Second grep — ONLY negative-statement hits allowed, i.e. core README L31 and L129 plus the two new "ships no `install.sh`" sentences added by Tasks 7–8; zero hits describing install.sh as something to RUN.

- [ ] **Step 3: Commit (ride-along, no version bump)**

```bash
cd /home/ntdst/Projects/netdust-plugins && git add plugins/netdust-core/README.md plugins/netdust-core/CLAUDE.md plugins/netdust-wp/README.md plugins/netdust-statamic/README.md && git commit -m "docs: reconcile plugin docs with marketplace reality (phase 3)

- netdust-core: netdust-local -> netdust-plugins in Roll back; drop ghost
  code-audit from the netdust-agent gate-skill lists (README + CLAUDE.md)
- netdust-wp / netdust-statamic: replace dead git-clone + install.sh flow
  with the marketplace install flow (mirrors core's phase-2 pattern)

No version bumps — doc-only ride-along.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
Expected: commit contains exactly 4 files.

`── REVIEW GATE ── (tier: LIGHT — doc/copy only in the repo, no 1a surface, no behavior. Single generalist pass: confirm the sweep grep output matches the expected residual set and the wp/statamic install sections match core's pattern.)`

---

## Sibling-site audit

| Cross-cutting string | All sites (verified 2026-07-03) | Covered by |
|---|---|---|
| `tasks/lessons.md` | CLAUDE.md L51, L86 — only two | Task 1 |
| ghost skill names (`code-audit`, `ntdst-infra`, `mainwp`, `create-agent-adapter`) | CLAUDE.md L110/113/115/138; core README L37; core CLAUDE.md L17 | Tasks 2, 6 |
| `netdust-local` | core README L147/148; statamic README L22/107; HANDOFF.md L15/33/34/35 (exempt, historical) | Tasks 6, 8 |
| runnable `install.sh` refs | wp README L22/25/58/99; statamic README L19/22/48/82 | Tasks 7, 8 |
| netdust-agent version string | plugin.json L3 AND marketplace.json L23 — two sites, must move together | Task 5 |

## Premise drift found during 1c (vs. the phase-3 briefing)

1. **Part B is a SPLIT verdict, not a pure no-op.** SKILL.md half = version-skew artifact (E row at line 60 in repo AND 0.3.1 cache). planner.md half = REAL: A/B/C/D only, in repo AND 0.3.1 cache — the briefing's "the 0.3.0/0.3.1 copy DOES contain Class E" is true only for SKILL.md, so Task 5 exists and carries phase 3's only version bump (0.3.2).
2. **Extra ghost found:** `code-audit` also appears in netdust-core README L37 and netdust-core CLAUDE.md L17 as a claimed netdust-agent gate skill — folded into Task 6 (same factual class, same files being edited).
3. **The NTDST table's other bare names** (`ntdst-architecture`/`ntdst-data`/`ntdst-patterns`/`ntdst-yootheme`) resolve only as `netdust-wp:*` — same drift class as `testing-workflow`; qualified in Task 2 using the file's own §0b precedent. `ntdst-yootheme` itself is real (exists in netdust-wp).
4. **wp README stale flow is wider than the Install section** — Layout tree L58 and L99 also reference install.sh; statamic README mirrors all of it. Tasks 7–8 cover the full set.
5. **Layer C paths are accurate as-is** — session-stop.py routes LESSON → `memory/lessons.md` and TODO → `tasks/todo.md`; only the "netdust-core" hook attribution is wrong. `tasks/todo.md` references must NOT be edited.
6. The netdust-plugins directory IS a git repo (main, tracking origin/main) despite the session env header claiming otherwise — Part B/C commits are possible; Part A stays backup-based (no repo at `~/.claude`).

## Self-review (writing-plans checklist)

- Spec coverage: A1–A5 → Tasks 1–3; B → Tasks 4–5; C6–C8 → Tasks 6–8. No gaps.
- Placeholder scan: none — every edit shows exact old/new text; the one read-before-edit (Task 8 statamic Install wording) names exact lines and the exact donor pattern.
- Consistency: version 0.3.2 used identically in Task 5 steps and commit; grep gates match the strings the tasks remove.

---

## Review section (execution record, 2026-07-03)

- Cluster 1 (global ~/.claude/CLAUDE.md): 34-line diff, every hunk mapped to a plan step. STANDARD review ×2 (fact-check: every claim verified true on-machine; scope-guard: zero unauthorized drift) — both APPROVED. Backup: ~/.claude/CLAUDE.md.bak-2026-07-03.
- Cluster 2: Part B split verdict confirmed — SKILL.md Class E was version-skew fallout (no-op, evidence recorded); planner.md genuinely lacked E → fixed + 0.3.2 bump (commit 6351637 post-rebase).
- Cluster 3: netdust-local refs, ghost code-audit mentions, wp/statamic dead install.sh flows all swept (commit e606445 post-rebase); residuals classified (4 negative-statements + HANDOFF.md exemption). LIGHT review: APPROVED.
- Delivery: rebased over e779abe (parallel session's netdust-wp REST/CORS docs — no conflicts), pushed, netdust-agent 0.3.1→0.3.2 installed and verified (Class E in installed planner.md).
- Deferral: netdust-wp/docs/superpowers/specs/2026-05-17-harness-design.md carries historical code-audit mentions — exemption class (dated spec archive), noted not fixed.
