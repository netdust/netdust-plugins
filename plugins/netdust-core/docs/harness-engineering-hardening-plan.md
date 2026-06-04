# Harness-Engineering Hardening Plan — netdust-core

**Status:** PARKED — research done, implementation deferred (Stefan: "we do this later")
**Created:** 2026-05-31
**Source of truth for this plan:** this file. Source repo: `github.com:netdust/netdust-plugins`, plugin path `plugins/netdust-core/`.
**Origin:** Deep-research comparison of [ai-boost/awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering) against the netdust-core harness (2026-05-31 session).

---

## Why

The awesome-harness-engineering list organizes harness quality into six buckets — **Observe & Plan, Act, Control, Remember, Verify, Collaborate**. netdust-core already scores strongly on Remember (deterministic tag scanner + Haiku), Verify (`/integration`→`/shakeout`→`/evaluate`), Act (commands declare tight `allowed-tools`), and Collaborate (`/deploy` dry-run + prod confirmation).

Three gaps remain, all in the **Control** bucket, all confirmed against source files this session:

1. **Reviewer agents grant full tools** (least-privilege violation / OWASP LLM06 "excessive agency").
2. **No `PreToolUse` layer** — every guardrail is post-hoc, none is pre-action.
3. **No context-budget / compaction strategy** (the list's top "compaction fragility" warning).

---

## Confirmed evidence (this session)

- `agents/*.md` (all 7): frontmatter is `name` + `description` only — **no `tools:` line**. Agent registry shows `(Tools: All tools)` for every one. A "findings-only" reviewer can currently `Edit`, `Write`, `Bash rm`, push.
- `hooks/hooks.json`: registers only `SessionStart`, `Stop`, `SubagentStop`. No `PreToolUse`.
- `commands/*.md`: DO declare tight `allowed-tools` (e.g. `/deploy` = `Bash, Read, AskUserQuestion`) — good, the gap is agents, not commands.

---

## Item 1 — Least-privilege tool scoping on the 7 reviewer agents `[HIGH PRIORITY, TRIVIAL]`

**Problem:** Reviewers are dispatched by `/shakeout` with a "findings only" briefing — but that's prompt-level prose, not a harness-level guarantee. The list's "Beyond Permission Prompts" principle: structured authorization must replace natural-language trust.

**Fix:** Add a `tools:` line to each of the 7 agent frontmatters, restricting to read-only inspection. The 7 files:

```
agents/accessibility-reviewer.md
agents/api-design-reviewer.md
agents/architecture-strategist.md
agents/code-simplicity-reviewer.md
agents/frontend-architect.md
agents/performance-oracle.md
agents/security-sentinel.md
```

**Proposed line** (verify exact key — `tools:` for subagent frontmatter):
```yaml
tools: Read, Grep, Glob, Bash
```
- Keep `Bash` only for grep-style pattern hunting across the diff. If a reviewer never shells out, drop it to `Read, Grep, Glob` — a reviewer that *cannot* mutate the tree is structurally incapable of the dual-modal-regression class of bug.
- A review agent with no `Edit`/`Write`/`Agent` cannot violate the findings-only contract even if its prompt is ignored.

**Effort:** ~7 one-line edits. No threat model needed (removing capability, not adding a trust boundary).

**Verification:**
- After edit, re-check `claude` agent registry / `/agents` listing shows the restricted tool set per agent (no longer "All tools").
- Run an existing `/shakeout` against a throwaway diff; confirm reviewers still produce findings (Read/Grep is sufficient for review).
- Existing python hook tests (`tests/run.sh`) should still pass (untouched, but run as regression).

**Open question:** confirm the correct frontmatter key in this Claude Code version — `tools:` vs `allowed-tools:`. Commands use `allowed-tools`; agents historically use `tools`. Check one agent against the docs before bulk-editing.

---

## Item 2 — PreToolUse destructive-action guard hook `[HIGH VALUE, NEEDS CARE]`

**Problem:** Every safety mechanism in netdust-core fires *after* the action. `SubagentStop` catches "you didn't test" after code exists; nothing catches `rm -rf`, `git push --force`, `DROP TABLE`, or a write to a production path *before* it runs. The global CLAUDE.md / RULES.md already encode the intent ("confirm environment before destructive ops", "never edit prod files", "never commit to main directly") — but it's advice the model can skip, not an enforced invariant. The list's strongest Control pattern is **pre-action authorization**: synchronous interception before execution, deterministic policy.

**Fix:** Add a `PreToolUse` hook (matcher `Bash`, optionally `Edit|Write`) — a deterministic Python script mirroring the existing `subagent-stop.py` style — that pattern-matches a small denylist and returns `deny` or `ask`.

**Scope of the denylist (v1, conservative — favor `ask` over `deny` to avoid friction):**
- `rm -rf` / `rm -fr` on broad paths
- `git push` with `--force` / `-f` / `+` refspec
- `git ... main`/`master` direct push or commit (per RULES.md "never commit directly to main")
- SQL `DROP TABLE` / `DROP DATABASE` / `TRUNCATE`
- writes/edits under a production path read from the project's `site.yml` (if present)
- `wp ... --path=<prod>` destructive WP-CLI (db reset, etc.) — stack-specific, may defer to netdust-wp

### Threat model (required by CLAUDE.md — hook touches the tool-execution boundary)

**Assets**
- The developer's working tree and git history.
- Production servers/sites reachable via Bash (ssh, rsync, wp-cli, ploi).
- Production databases.

**Actors**
- The agent itself (primary): may run a destructive command from a stale plan, a hallucinated path, or an over-eager autonomous loop.
- A compromised/malicious instruction injected via untrusted content the agent ingested (prompt injection → tool call). The lethal-trifecta concern the list names: private data + untrusted content + outbound action.

**Attacks → Mitigations**
1. **Agent runs `rm -rf` on the repo or `$HOME` from a bad variable expansion.** → Mitigation: PreToolUse denylist matches `rm -rf` patterns, returns `ask`, surfacing the literal command for human eyeball before exec.
2. **Agent force-pushes over `main`, destroying remote history.** → Mitigation: match `git push.*(--force|-f|\+)` and pushes targeting main/master → `ask`.
3. **Agent edits/deploys to a production path directly (violates "local-first").** → Mitigation: read `site.yml` prod path; flag Bash/Edit/Write targeting it → `ask` (or `deny` if `site.risk: high`).
4. **Prompt-injected destructive command.** → Mitigation: same deterministic denylist; the guard does not trust intent/explanation, only the literal command string. Deny-by-default for the highest-risk patterns regardless of stated reason.
5. **Drops a real production DB via SQL or wp-cli.** → Mitigation: match `DROP (TABLE|DATABASE)|TRUNCATE` and destructive wp db subcommands → `ask`.

**Failure modes of the guard itself (must not regress the harness)**
- **False positives blocking legit work** → favor `ask` over `deny`; keep the denylist tight and literal; log every decision to `~/.claude/logs/` like the other hooks.
- **Hook crash blocking ALL tool calls** → wrap in try/except; on internal error, fail OPEN (allow) and log loudly — a broken guard must not brick the session. (Contrast: SubagentStop fails toward gating, but that's a Stop hook; a PreToolUse crash failing closed would be catastrophic.)
- **Infinite loop / re-prompt** → PreToolUse returns a single decision per call; no loop risk, but ensure the `ask` path doesn't re-trigger on the user's confirmation.
- **Interaction with superpowers plugins layered on top** → TEST before shipping: superpowers' own worktree/git automation must not trip the git-main guard. May need an allowlist exception for known-safe superpowers commands.

**Out of scope (v1)**
- Intent-level semantic classification (the list's two-stage fast/slow classifier) — overkill for one developer; literal denylist is enough.
- Outbound-network egress control / lethal-trifecta full mitigation — deferred.
- Per-tool-call structured audit log (see Item 4).

**Effort:** ~60–90 lines Python + hooks.json entry + tests. Write as TDD (pytest, matching `tests/test_subagent_stop.py` style): table of (command → expected decision).

**Verification:**
- New `tests/test_pretooluse_guard.py`: assert deny/ask/allow for a table of commands incl. false-positive cases (`rm -rf node_modules` inside project should probably allow or ask, not hard-deny).
- Manual: run a benign `git status` (allow), a `git push --force` to a throwaway (ask), confirm no friction on normal edits.
- Run `tests/run.sh` full suite — green.
- Smoke-test one real superpowers-driven workflow to confirm no false-block.

---

## Item 3 — Context-budget / compaction awareness `[LOWER PRIORITY]`

**Problem:** netdust-core does eager construction (SessionStart injects memory/site.yml upfront) but nothing watches context pressure or proactively consolidates. `/memory-audit` only *warns* when `lessons.md` > 80 lines. The list treats context engineering as the central discipline and "compaction fragility" as a top warning.

**Fix (two cheap moves, no new hook):**
1. Upgrade `/memory-audit` to *propose* truncation/consolidation of oversized lessons/STATE files (currently warn-only). Keep it report-only per its existing contract — propose, don't auto-edit.
2. Audit that all *critical* rules live in CLAUDE.md/RULES.md/system prompt (they appear to) so server-side compaction can never evict them — the list's explicit mitigation. Document this as an invariant.

**Effort:** small. **Verification:** `/memory-audit` on a project with an oversized lessons file emits a consolidation proposal.

---

## Deferred / not-now (logged, not planned)

- **Trajectory observability** `[LC]`: a `PostToolUse` JSONL logger of per-subagent tool calls for replay. List rates observability first-class, but ROI depends on whether Stefan actually debugs agent trajectories. Revisit if "why did this agent do X?" becomes a recurring question.
- **Skill count discipline**: ~13 skills, list says consolidate at ≤12. Currently fine — cleanly domain-separated with sharp triggers. No action; just don't let it sprawl.

---

## Recommended order when resumed

1. **Item 1** (agent tool scoping) — 10 min, highest safety/effort ratio, zero downside. Do first.
2. **Item 2** (PreToolUse guard) — ~1–1.5 hr, biggest architectural upgrade. Write as a TDD task with the threat model above as the convergence target for review. Smoke-test against superpowers before merging.
3. **Item 3** (memory-audit consolidation) — when a lessons file actually gets unwieldy.

## Workflow when resumed

- Branch off `main` in `github.com:netdust/netdust-plugins` (don't edit the live cache at `~/.claude/plugins/cache/...` — it's the installed copy and gets overwritten on update).
- After merge + plugin update, re-run SessionStart symlink maintenance picks up the new version.
- Commit style per repo convention.

## Key sources

- https://github.com/ai-boost/awesome-harness-engineering — the knowledge base (taxonomy + design warnings)
- https://openai.com/index/harness-engineering/ — OpenAI's canonical definition
- https://www.infoq.com/news/2026/02/openai-harness-engineering-codex/ — independent corroboration
- netdust-core `hooks/hooks.json`, `agents/*.md`, `commands/*.md` — primary evidence for the gaps
