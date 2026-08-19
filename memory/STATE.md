---
### 2026-08-13 (later) — orphaned-session work reconciled

**Decisions**
- The 5 stranded local commits + dirty tree are fully published. Design-builder (netdust-core): 4 commits rebased onto main and released as 0.2.8 (herdr and design-builder had both claimed 0.2.7 on divergent lines); catalog synced; installed plugin updated. Root .gitignore learned the stop-hook state file.
- The netdust-wp drift-check rework (references/templates deleted — 6,637 lines were sitting in a mislabeled 'memory auto-capture' commit — plus bin/drift-check.py, golden-paths, framework-map.md, an uncommitted 0.7.1→0.8.0 bump) is PARKED on pushed branch `wip/netdust-wp-drift-check`, deliberately NOT on main: the bump would ship a half-verified plugin on the next update. Finish through the harness (Class B freshness review) before releasing. Loose end noted in the wip commit: a7838e5's lessons cite the deleted references/api-endpoints.md — re-home that content.
- Local main now equals origin/main; tree clean except untracked memory/ (the stop hook's domain). Suite 22/22 at every push.

---
### 2026-08-13 — spec-kit harvest shipped upstream (agent 0.19.0)

**Decisions**
- Re-evaluated github/spec-kit: adopt no tooling; harvested two ideas into netdust-agent 0.19.0, PUSHED as b9376b9 on origin/main — new `convergence` gate (skill + /converge: code-vs-spec completeness, gaps missing/partial/contradicts/unrequested appended to tasks.md as a PROPOSED phase behind gate-check + the seam) and three semantic passes in planning Stage 1.5 (duplication, vague-adjective ambiguity, terminology drift). Marketplace catalog entry re-synced (had sat at 0.17 through the 0.18 release). Evidence: tests 22/22, trigger eval 4/4.
- This clone sat at a pre-0.18 base with another session's uncommitted netdust-wp work; the harvest was re-landed and pushed from a temporary worktree instead, and this clone was restored to exactly its pre-session state (foreign work untouched, local main left at 2d3b96e — it still needs its own rebase onto origin/main to publish the 5 local design-builder/memory commits).

**Incident**
- This session briefly truncated this file (open('w') before reading the old content); restored from restic snapshot 05b8369d (2026-08-12) + this corrected entry. Lesson filed in memory/lessons.md.


---
### 2026-07-03 — tagged capture

**Decisions**
- Track B (Haiku summarizer) permanently removed from the Stop hook — capture is tags-only; if `tags=[]` sessions keep losing content, the agreed future option is a block-once tag nudge, not an API key.
[2026-07-03] — session ended (no significant changes captured)

---
### 2026-07-03 — tagged capture

**Decisions**
- netdust-core stays as a plugin — it is no longer a harness (that's netdust-agent) but the business/fleet plugin: brand-voice, marketing, market-research, ploi, secure-server, dev-stack, /deploy, /memory-audit, RULES/SOUL. Do not dissolve or rename it. netdust-wp remains the WordPress domain layer.

---
### 2026-08-19 — tagged capture

**Decisions**
- herdr remote topology is ssh-then-`herdr` on the box, never the `--remote` thin client; recorded in netdust-core:herdr-orchestration 0.2.9.
