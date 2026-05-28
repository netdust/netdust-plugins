_Harness-self memory for the `netdust-wp` plugin itself. Stays minimal — real project state lives in each `~/Sites/<project>/memory/STATE.md`._

### 2026-05-17 — initial bootstrap

**Decisions**
- Harness deploys as a self-installing plugin via `bash ~/.claude/plugins/netdust-wp/install.sh` rather than `/plugin install` — Claude Code's local plugin discovery isn't reliable enough for non-marketplace plugins.
- Split from a single `netdust-wp` into a 3-plugin harness (core / wp / statamic) on 2026-05-17. See `~/.claude/plugins/netdust-core/docs/HANDOFF.md` for the architecture.

---
### 2026-05-17 — tagged capture

**Decisions**
- Tier 1.5 fixes applied to `ntdst-architecture` (4 doc-drifts: A10 line cap, A5/A9 prefix, E3 config-file name, A8 admin gating) + 2 missing patterns added (A6 sub-services, E4 *CPT class) + broadened SKILL.md trigger description so it fires on bare "add a service" prompts. Also added `wp-security` paragraph clarifying ntdst_api handlers don't need per-handler nonce.

---
### 2026-05-17 — tagged capture

**Decisions**
- Tier 1.5 fixes applied to `ntdst-architecture` (4 doc-drifts: A10 line cap, A5/A9 prefix, E3 config-file name, A8 admin gating) + 2 missing patterns added (A6 sub-services, E4 *CPT class) + broadened SKILL.md trigger description so it fires on bare "add a service" prompts. Also added `wp-security` paragraph clarifying ntdst_api handlers don't need per-handler nonce.

---
### 2026-05-17 — tagged capture

**Decisions**
- Tier 1.5 fixes applied to `ntdst-architecture` (4 doc-drifts: A10 line cap, A5/A9 prefix, E3 config-file name, A8 admin gating) + 2 missing patterns added (A6 sub-services, E4 *CPT class) + broadened SKILL.md trigger description so it fires on bare "add a service" prompts. Also added `wp-security` paragraph clarifying ntdst_api handlers don't need per-handler nonce.
- re-eval done. Net `skill_delta` held at +15 (prior +16), but the qualitative shift is what matters: scenario 1 went from the eval's headline failure (+0) to the eval's headline win (+4), and A6/E4 patterns landed in skill-on outputs that previously didn't have them. Three small new issues surfaced (B3 in 2b, C4 in 3, EX5 in 6) — none are skill-doc bugs, they're consistency issues in agent output.
