# Plan — WP harness: fix scaffold bugs + enforce WP-security/ntdst-core in the PLAN

**Date:** 2026-06-05
**Repo:** `~/.claude/plugins/marketplaces/netdust-plugins` (the harness marketplace, branch `main`, clean)
**Class:** A — multi-task change to the WP-stack harness itself.
**Driver:** Stefan is about to start a new WP project and wants (1) the known scaffold bugs fixed and (2) WP good-practice + ntdst-core patterns **enforced by the plan**, not only caught by reviewers at the end.

---

## Architecture-invariants citation (Gate 1b)

The convergence point this work touches is **how the WP stack injects stage behavior into the generic harness**. The governing invariant is already stated in `netdust-core/skills/harnessed-development/SKILL.md` `<stack_overrides>`:

> *"This skill never hardcodes their names… prefer the stack-specific skill when one is loaded for this project."*

**Constraint this plan honors:** the new WP plan-gate skill is wired so `harnessed-development` picks it up **by the stack-override rule** (a `netdust-wp` skill that replaces/augments the generic Stage-1 behavior), NOT by adding a `netdust-wp` skill name into the core skill. Core stays stack-agnostic. This is the one place the "how does WP shape the plan" decision lives — the new skill is that convergence point for WP.

No threat model (Gate 1a): the diff edits templates + skill markdown; no runtime input/auth/URL/crypto surface. The new skill's *purpose* is to propagate the security gate downstream — that is its value, not a threat surface in this change.

---

## Part 1 — Fix the three scaffold bugs

### Task 1.1 — Complete the Makefile deploy variants
**File:** `netdust-wp/templates/Makefile.tmpl`
**Bug:** Header advertises 3 variants (`makefile`, `git-push`, `git-bundle-makefile`); only `makefile` is a real, copyable section. `git-push` is commented-out *instructions* (not a usable section), `git-bundle-makefile` is absent. The command (`wp-new-project.md` line 39) tells the scaffolder to "find the section for the chosen method" — for 2 of 3 it finds nothing usable.
**Fix:** Make each of the 3 advertised variants a **complete, self-contained, copyable section** (full Makefile, not a diff-against-the-first). `git-push` becomes a real section with push-based deploy targets. `git-bundle-makefile` becomes a real section (explicit two-step bundle: create on local, fetch+merge on remote).
**Acceptance:** For each of `makefile` / `git-push` / `git-bundle-makefile`, the section between its banner and the next banner is a valid standalone Makefile with `dev/save/deploy-staging/deploy-production/ship/feature/finish` targets.
**Unit test:** n/a (template text). Verify by: extract each section, confirm `make -n -f <section>` parses (dry-run, no exec). Tier B.

### Task 1.2 — Make the deploy-method → Makefile mapping honest in the command
**File:** `netdust-wp/commands/wp-new-project.md`
**Bug:** Line 39 only maps `makefile`/`git-bundle-makefile`/`git-push` to a Makefile, but the prompt offers 9 methods. `rsync`, `rsync-staging-prod`, `ftp`, `autogit`, `manual`, `tbd` silently get no Makefile and no explanation.
**Fix:** Reword step 5 so it (a) maps each of the 9 methods explicitly to "copy variant X" or "no Makefile — deploy is handled by <mechanism>", and (b) for `tbd`, write a stub `site.yml` note instead of leaving the user guessing.
**Acceptance:** Every one of the 9 methods has a defined scaffold outcome in step 5.
**Unit test:** n/a (command prose). Tier B — verify by reading: 9 methods ↔ 9 outcomes.

### Task 1.3 — Delete the stale duplicate template folder
**Path:** `~/Sites/netdust-wp-manager/template/`
**Bug:** March-dated dead duplicate (flat `site.yml` schema, references a hook path that no longer exists). The live scaffold uses the *plugin's* `templates/` (current). The stale copy can mislead a future session into copying the wrong schema.
**Fix:** Delete `~/Sites/netdust-wp-manager/template/`. Before deleting, grep the site-manager for any script that references `template/` so we don't break a consumer.
**Acceptance:** Folder gone; no script in `netdust-wp-manager/` references the deleted path.
**Unit test:** n/a. Tier B — grep-for-references gate before `rm`.
**Safety:** This is a delete of something I did not create. Per the operating rules I will first look at it + grep for consumers, and only delete if it is confirmed dead. If a consumer references it, I STOP and report instead.

### Task 1.4 — Refresh the installed-plugins SHA pin (cosmetic)
**File:** `~/.claude/plugins/installed_plugins.json`
**Bug:** Pin records `7a414a2` (May 28) though the cache content is byte-identical to HEAD `b06492d`. Harmless but misleading — it made an audit conclude "8 days stale" when content was current.
**Fix:** Prefer the marketplace's own `scripts/sync.sh` if it exists (re-pin the right way). If no such script, update the two `gitCommitSha` fields for `netdust-core`/`netdust-wp` to current HEAD.
**Acceptance:** Pin SHA == marketplace HEAD for both plugins.
**Unit test:** n/a. Tier B.

── REVIEW GATE (Part 1) ── commit Part 1, `/integration`-equivalent (parse-check the Makefile sections + re-grep), hand back for `/code-review` on the Part-1 diff before starting Part 2.

---

## Part 2 — Enforce WP-security + ntdst-core IN THE PLAN (the real ask)

### Task 2.1 — Author `netdust-wp:wp-plan-requirements` skill
**New file:** `netdust-wp/skills/wp-plan-requirements/SKILL.md` (+ a `references/checklist.md`)
**What it does:** A Stage-1 skill that, on a WP project, injects **mandatory plan sections** so the plan itself carries the requirements (symmetric with how `threat-modeling` injects `## Threat model`). It produces three blocks the plan must contain before task breakdown is final:

1. **`## WP security requirements (per data-flow)`** — one line per user-facing data flow in the feature, each naming the 4 pillars it must satisfy (validate / sanitize / escape / authorize incl. nonce + capability). Sources its vocabulary from `wp-security` (no duplication — it *references* the 4 pillars + the sanitize/escape tables).
2. **`## ntdst-core layering requirements`** — the framework-pattern obligations the feature's new classes must meet: Service→Repository (no direct `ntdst_data()`), no raw `wp_ajax_*` (use the framework handler), no `ob_start+include` rendering, no swallowed `WP_Error`, no hardcoded meta prefix, correct Data API vocabulary. Sources the list from the `ntdst-drift-reviewer`'s 9 categories — so plan-requirement and review-check are the **same list**, just fired at two ends.
3. **Per-task acceptance line:** every module-touching task gets a `drift pre-check: clean` acceptance criterion, so the drift categories are a *gate on task close*, not only a shake-out finding.

**Authority pattern:** the skill explicitly states its `covered`/`required` blocks become the **convergence target** for the WP `/code-review` + `ntdst-drift-reviewer` — reviewers verify against the named items instead of free-form hunting (one-round convergence, same property threat-modeling buys).
**Acceptance:** skill description triggers on WP plan-writing; body produces the 3 blocks; references (not duplicates) wp-security + ntdst-drift-reviewer canon.
**Unit test:** n/a (skill markdown). Tier B — verify the description triggers (does it name "plan", "WP", "ntdst-core"?) and that it cross-links rather than copies the 4 pillars / 9 categories.

### Task 2.2 — Wire the skill into `harnessed-development` Stage 1 via the stack-override rule
**File:** `netdust-core/skills/harnessed-development/SKILL.md`
**Constraint (invariant 1b):** do NOT hardcode `netdust-wp:wp-plan-requirements` in core. Instead, generalize the Stage-1 language so a loaded stack sub-plugin's *plan-requirements* skill is fired alongside threat-modeling/invariants — the same way `<stack_overrides>` already generalizes brainstorming/testing/shake-out. One added sentence in `<stack_overrides>` + a one-line pointer at Stage 1 ("if the loaded stack sub-plugin provides a plan-requirements skill, invoke it here so its mandatory sections are injected before task breakdown").
**Acceptance:** core stays stack-agnostic (no `netdust-wp` literal); the override rule now covers plan-requirements; reading Stage 1 makes clear a WP project gets the WP plan sections.
**Unit test:** n/a. Tier B — grep core for `netdust-wp` literal == 0 after edit.

### Task 2.3 — Point the project CLAUDE.md template at the new gate
**File:** `netdust-wp/templates/project-CLAUDE.md.tmpl`
**What:** Add one bullet under "How to Work" (between current #2 and #3) naming the plan-requirements skill as the WP plan gate that fires at Stage 1 — so a freshly scaffolded project documents that WP-security + ntdst-core are enforced *in the plan*, and reviewers verify against it. Keep it to the contract, not a duplicate of the skill.
**Acceptance:** scaffolded CLAUDE.md tells the reader the plan will carry WP-security + ntdst-core requirement blocks, fired by harnessed-development Stage 1.
**Unit test:** n/a. Tier B.

### Task 2.4 — Register the skill in the netdust-wp plugin manifest / description
**File:** `netdust-wp/.claude-plugin/plugin.json` (+ any skills index the plugin keeps)
**What:** Add `wp-plan-requirements` to the plugin's declared skills list / description so it loads. Confirm the skill is discoverable (mirrors how the other `wp-*` skills are registered).
**Acceptance:** the new skill appears in the plugin's skill registry the same way `wp-security` does.
**Unit test:** n/a. Tier B — diff against how an existing wp-* skill is registered; match the pattern.

── REVIEW GATE (Part 2) ── commit Part 2, hand back for `/code-review` on the Part-2 diff. Part 2 is skill/contract wiring — the reviewer checks: core stayed stack-agnostic, no canon duplicated, the gate actually fires on a WP plan.

---

## Stage 3 (after both parts)
- Re-grep the whole marketplace for the `netdust-wp` literal in core (must be 0) and for dangling refs to the deleted template folder.
- Optional: a dry pass of the scaffold logic mentally against each of the 9 deploy methods.
- `superpowers:finishing-a-development-branch` to integrate.

## Review-group sizing (1f)
Two clusters, each ~4 tasks, each with its own REVIEW GATE. Part 1 (mechanical/reversible) and Part 2 (skill+contract wiring) reviewed separately — they fail in different ways. Task 1.3 (a delete) reviewed inside Part 1 but called out for the consumer-grep safety step.

## What this deliberately does NOT do
- No new threat surface, no migration, no runtime code — pure harness/docs/templates.
- Does not duplicate the 4 pillars or 9 drift categories — the new skill *references* the canonical sources so they stay single-source.
- Does not touch the other stacks (statamic) — WP-only, by the stack-override rule.
