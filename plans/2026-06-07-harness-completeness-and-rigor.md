# Plan — Harness completeness + graduated rigor (netdust-core)

**Date:** 2026-06-07
**Repo:** `github.com:netdust/netdust-plugins`, plugin path `plugins/netdust-core/`
**Branch for this work:** `claude/harness-evaluation-IXMMd`
**Class:** A — multi-task change to the harness itself.
**Status:** PLAN ONLY — no implementation yet (Stefan: "just the plan").

**Supersedes / absorbs:** `plugins/netdust-core/docs/harness-engineering-hardening-plan.md` (the PARKED Items 1/2/3). That doc stays as the detailed threat-model reference for Item 2; this file is the single source of truth for *what to do and in what order*.

**Origin:** 2026-06-07 evaluation session. Benchmarked netdust-core against current development harnesses — SWE-agent, Aider, OpenHands, Cursor, OpenAI Codex, `obra/superpowers` — and the `ai-boost/awesome-harness-engineering` taxonomy.

---

## Framing — what "complete" means here (read first)

The harness was scored across 8 axes (the awesome-list's six buckets — Observe & Plan, Act, Control, Remember, Verify, Collaborate — plus two added this session: **Repo-context/ACI** and **Runtime isolation**).

**Do NOT chase all 8 axes to framework parity.** OpenHands and Codex earn their Runtime-isolation / Act scores by being *hosted, multi-user, sandboxed products*. netdust-core is a solo shop running on Stefan's own machine **with deliberate production SSH/wp-cli/Ploi reach**. Replicating their *infrastructure* (Docker runtime, network-off container) is the wrong target. Steal the **pattern**, never the **infrastructure**.

Honest completeness picture:

| Axis | Status | If gap: steal the *pattern* from | This plan |
|---|---|---|---|
| Observe & Plan | ✅ structural — plan-as-convergence-target (threat-model / architecture-invariants / wp-plan-requirements become the `/code-review` + `/shakeout` target) | — | keep |
| Remember | ✅ best-in-class — deterministic tag scanner + Haiku + per-project & per-skill lessons | — | keep |
| Verify (design-time) | ✅ strong — `integration → shakeout → evaluate`, testing-workflow, SubagentStop backstop | — | keep |
| Collaborate | ✅ fine for scale — `/deploy` dry-run + prod confirm, `site.yml`, SOUL.md voice | — | keep |
| **Control (execution-time)** | ❌ **the one real hole** — all guardrails post-hoc; no PreToolUse; reviewers hold full tools | awesome-harness "beyond permission prompts" + Codex network-off-default | **Items 1 + 2** |
| Act | 🟡 adequate (inherits Claude Code tools + MCP) | OpenHands event stream — low ROI | no action |
| Repo-context / ACI | 🟡 **efficiency-only** gap — Step 2.5/1c ground-truthing already covers *correctness*; only lookup *speed* is missing | Aider tree-sitter repo-map | Item 5 (optional) |
| Runtime isolation | 🟡 can't fully sandbox (need real prod SSH) | **collapses into Control** — PreToolUse guard is the "soft sandbox" | folded into Item 2 |

**Conclusion:** of 8 axes, structurally complete on 4; three of the remaining four either collapse into one piece of work or are efficiency-only. **"Complete" is one axis away, not seven: execution-time Control.** Everything else is optional polish.

**Why design-time enforcement does NOT already cover this (the boundary that holds):** the plan governs *intent* — the work that goes through the plan. It cannot, by construction, constrain *off-plan* actions: a stale path, a hallucinated `rm -rf "$VAR"` expansion, an autonomous-loop overrun between gates, a prompt-injected tool call (the harness's own `threat-modeling` skill names "AI tool-call args" / "webhook payloads" as untrusted-parse surfaces — so it already knows the agent ingests attacker-influenced content), or the intake-exempted "trivial edits / dependency bumps" that fire zero plan-gates. Every actor in Item 2's threat model is *by definition off-plan*. So the plan-gates have **zero coverage** of exactly the region the PreToolUse guard exists for. Orthogonal axes, not overlapping.

---

## Sequencing rule (why order matters)

Build the **floor before the dial.** Item 4 (graduated rigor) deliberately creates a fast path with fewer gates — and that fast path is precisely where an unrecoverable command gets fat-fingered. The deterministic execution-time floor (Items 1 + 2) is what makes "quick mode" safe to offer. **The rigor dial doesn't make the guard less necessary — it's the feature that makes it mandatory.** Floor first, dial second.

Recommended order: **Item 1 → Item 2 → Item 3 → Item 4 → Item 5 (if needed).**

---

## Item 1 — Least-privilege tool scoping on the 7 reviewer agents `[HIGH / TRIVIAL]`

**Source pattern:** SWE-agent's ACI thesis — *the interface constrains the agent, not the prompt.* Also OWASP LLM06 "excessive agency."

**Problem:** All 7 agents (`agents/*.md`) have frontmatter `name` + `description` only — no `tools:` line — so the registry shows `(Tools: All tools)`. A "findings-only" reviewer dispatched by `/shakeout` can currently `Edit`, `Write`, `Bash rm`, push. The findings-only contract is prompt-level prose, not a harness-level guarantee.

**Fix:** Add a `tools:` line to each of the 7 reviewer frontmatters, restricting to read-only inspection:

```yaml
tools: Read, Grep, Glob
```

Add `Bash` back only for a reviewer that genuinely needs grep-style shelling across the diff. A reviewer that *cannot* mutate the tree is structurally incapable of breaking the findings-only contract even if its prompt is ignored.

Files: `accessibility-reviewer.md`, `api-design-reviewer.md`, `architecture-strategist.md`, `code-simplicity-reviewer.md`, `frontend-architect.md`, `performance-oracle.md`, `security-sentinel.md`.

**Open question to settle before bulk-editing:** confirm the correct frontmatter key in this Claude Code version — `tools:` (agents) vs `allowed-tools:` (commands). Check one agent against the docs first.

**Acceptance:** `/agents` listing shows the restricted tool set per agent (no longer "All tools").

**Verification:** run `/shakeout` against a throwaway diff; confirm reviewers still produce findings (Read/Grep is sufficient). Run `tests/run.sh` as regression.

**Effort:** ~7 one-line edits.

---

## Item 2 — PreToolUse destructive-action guard `[HIGH VALUE / NEEDS CARE]`

**Source pattern:** awesome-harness "pre-action authorization" (synchronous interception before execution, deterministic policy) + Codex's "network off by default." This is also the **Runtime-isolation** axis — a "soft sandbox" for a shop that can't use a real container because it needs live prod SSH.

**Problem:** Every safety mechanism fires *after* the action. Nothing intercepts `rm -rf`, `git push --force`, direct main push, `DROP TABLE`, a write to a prod path, or `redis-cli FLUSHALL` (RULES.md rule 10 — destroys VAD's cache exclusions) *before* it runs. CLAUDE.md/RULES.md encode the intent, but it's advice the model can skip, not an enforced invariant.

**Fix:** A `PreToolUse` hook (matcher `Bash`, optionally `Edit|Write`) — deterministic Python mirroring `subagent-stop.py` style — pattern-matching a tight literal denylist, returning `ask` (preferred) or `deny`.

**Denylist v1 (conservative — favor `ask` over `deny`):**
- `rm -rf` / `rm -fr` on broad paths
- `git push` with `--force` / `-f` / `+` refspec
- `git push`/commit targeting `main`/`master` directly (RULES.md rule 5)
- SQL `DROP TABLE` / `DROP DATABASE` / `TRUNCATE`
- destructive WP-CLI (`wp db reset`, `wp db drop`) — may defer detail to netdust-wp
- `redis-cli FLUSHALL` / `wp cache flush` (RULES.md rule 10)
- writes/edits under a production path read from the project's `site.yml` (if present)

**Threat model:** see the PARKED `docs/harness-engineering-hardening-plan.md` Item 2 — assets (working tree, git history, prod servers/DBs), actors (the agent from a stale plan / hallucinated path / autonomous loop; a prompt-injected destructive command), attacks→mitigations, and the guard's own failure modes. Do not re-derive it; that doc is the convergence target for Item 2's `/security-review`.

**Critical failure-mode invariants (must hold):**
- **Fail OPEN on internal error.** Wrap in try/except; a crashing PreToolUse hook that fails closed would brick every tool call. Log loudly to `~/.claude/logs/`.
- **Favor `ask` over `deny`** to avoid blocking legit work; keep the denylist literal and tight.
- **The guard trusts the literal command string, not stated intent** — deny-by-default for the highest-risk patterns regardless of explanation (prompt-injection mitigation).
- **Test against superpowers** worktree/git automation before shipping — its git ops must not trip the main-push guard (may need an allowlist exception).

**Out of scope (v1):** semantic intent classification, full lethal-trifecta egress control, per-tool-call audit log (Item 5).

**Acceptance / verification:** new `tests/test_pretooluse_guard.py` — table of (command → expected decision) incl. false-positive cases (`rm -rf node_modules` inside project → allow or ask, not hard-deny). Manual: `git status` allows, `git push --force` to a throwaway asks, normal edits no friction. `tests/run.sh` green. Smoke-test one real superpowers workflow.

**Effort:** ~60–90 lines Python + hooks.json entry + tests. Write as TDD.

---

## Item 3 — Context-budget / compaction awareness `[LOWER PRIORITY]`

**Source pattern:** awesome-harness "compaction fragility" warning.

**Fix (two cheap moves, no new hook):**
1. Upgrade `/memory-audit` to *propose* consolidation/truncation of oversized lessons/STATE files (currently warn-only at 80 lines). Keep report-only — propose, don't auto-edit.
2. Document as an explicit invariant that all *critical* rules live in CLAUDE.md/RULES.md/system prompt (they do) so server-side compaction can never evict them — the list's named mitigation.

**Acceptance:** `/memory-audit` on a project with an oversized lessons file emits a consolidation proposal. The compaction invariant is written down.

**Effort:** small.

---

## Item 4 — Graduated rigor dial `[NEW — build AFTER Items 1+2]`

**Source pattern:** the harness's own `/code-review` effort param (low/med/high) applied to the harness stages; the general "graduated autonomy" idea. Builds directly on the existing `<intake>` work-class taxonomy (A/B/C/D), which is *already* a scope-based rigor system.

**Idea (Stefan):** like `/code-review` has low/med/high, let the harness run at a chosen rigor level where some gates get skipped for lighter tasks.

**Two knobs — do not conflate:**
- **Scope** — *which* gates fire. Already exists: intake class + per-skill trigger predicates (threat-modeling only on security surfaces, feature-acceptance only on user-facing features).
- **Effort** — *how deep* each gate goes. The `/code-review` analogy. This is the new thing.

**THE HARD RULE — the dial moves the ceiling, never the floor.**
`/code-review` is safe to dial down because every level only changes *how many findings* — a missed bug is **recoverable**. The harness has gates whose skip is **irreversible** (a dropped prod DB, a force-push over main). So:

```
FLOOR — always on, every level, NOT dial-addressable:
  - threat-modeling on a triggering security surface   (intake Class D already pins this)
  - PreToolUse destructive-action guard                (Item 2)
  - never-commit-to-main / never-deploy-without-confirm (RULES 5, 6)
  - testing-workflow on any edited code                (SubagentStop backstop)

CEILING — this is what the dial scales:
  - brainstorm stage (Stage 0)
  - number of reviewers /shakeout dispatches
  - sibling-site audit blocks (1e)
  - acceptance-flow edge-class depth (1g)
  - review-group granularity (1f)
  - architecture-invariants re-audit vs cite-only (1b)
```

**Levels (proposal):**

| Level | Skips (ceiling) | Keeps (floor) | When |
|---|---|---|---|
| `quick` | brainstorm, plan, shake-out, multi-reviewer | all 4 floor gates | trivial / one-file / dependency bump |
| `standard` | nothing structural; fewer reviewers, single review group if <4 tasks | floor + plan gates | Class A default |
| `full` | nothing | everything + all 7 reviewers + force invariants re-audit + `/security-review` | irreversible / multi-tenant / auth surface |

**Override policy:**
- Manual **up-override** (force `full`) — always safe, always allowed.
- Manual **down-override of an auto-fired safety/floor gate** — FORBIDDEN. The floor is not dial-addressable. (e.g. you cannot set `quick` to skip a threat model on a surface that triggered it.)

**Cleanest first slice (reuse an existing knob):** make `/shakeout`'s reviewer dispatch inherit a level mapped to `/code-review`'s low/med/high — `quick` → high-confidence findings from the 2–3 most relevant reviewers; `full` → all 7 + uncertain findings. The semantics already exist; you're just propagating them. Start here before touching the planning stages.

**Implementation sketch:** add a `rigor:` line the controller states at intake (extends the existing "state your class and reason" step in `harnessed-development` `<intake>`). Map each gate to a `min-rigor` at which it fires; pin the four floor gates to `always`. Likely derive a default `rigor` from the work-class (D→floor-only-plus-security, C→standard, A→standard, explicit `full` for irreversible/tenancy/auth).

**Acceptance:** a documented level set; the floor gates demonstrably fire even at `quick`; `/shakeout` reviewer breadth scales with level; intake states a rigor level with its class.

**Effort:** medium — mostly skill-markdown wiring in `harnessed-development` + `/shakeout`. No new hook if the floor is already enforced by Item 2 + SubagentStop.

---

## Item 5 — Optional polish (only on demonstrated need) `[DEFERRED]`

- **Repo-map (Observe/efficiency):** Aider-style tree-sitter ranked symbol map, cached per-project, refreshed at SessionStart. ONLY a lookup-speed win — Step 2.5/1c already cover correctness. Add only if grep-rediscovery on a large WP/LearnDash repo becomes a real time sink.
- **Trajectory observability:** OpenHands-style `PostToolUse` JSONL logger of per-subagent tool calls for replay. Add only if "why did this agent do X?" becomes a recurring debugging question.
- **Edit-time ACI feedback:** SWE-agent/Aider-style immediate lint/syntax feedback on edit. Minor — Claude Code's Edit tooling is decent; testing-workflow catches it post-hoc.

Do not build these speculatively. They are logged so the question gets revisited deliberately, not so it gets built.

---

## Review-group sizing (1f)

Three implementation clusters, reviewed separately (they fail in different ways):
1. **Item 1** (reviewer scoping) — mechanical, reversible. One review.
2. **Item 2** (PreToolUse guard) — irreversible-class (touches the tool-execution boundary). Own review + `/security-review` against the parked threat model.
3. **Items 3 + 4** (memory-audit + rigor dial) — skill/contract wiring. Own review: confirm the floor gates are non-dial-addressable.

Each cluster: commit → `/integration` → `/code-review` (+ `/security-review` for cluster 2) before starting the next.

---

## What this plan deliberately does NOT do

- Does not build a Docker/container runtime — wrong target for a shop needing live prod SSH; the PreToolUse guard is the soft-sandbox substitute.
- Does not chase Act / repo-map / trajectory-log to framework parity — efficiency-only or low-ROI for this scale.
- Does not duplicate the parked Item 2 threat model — references it as the single source.
- Does not let the rigor dial touch the safety floor — that is the one invariant the whole Item 4 design protects.

## Key sources

- `ai-boost/awesome-harness-engineering` — taxonomy + design warnings (the six buckets, "beyond permission prompts", "compaction fragility")
- SWE-agent — Agent-Computer Interface (the interface constrains the agent → Items 1, 5)
- OpenAI Codex — cloud sandbox, network-off-by-default (→ Item 2 soft-sandbox)
- OpenHands — sandboxed runtime + event stream (→ Item 2 framing, Item 5 trajectory log)
- Aider — tree-sitter repo-map (→ Item 5)
- `obra/superpowers` — the upstream engineering loop netdust-core sequences (must not be tripped by Item 2's guard)
- netdust-core `docs/harness-engineering-hardening-plan.md` — the detailed Item 2 threat model
