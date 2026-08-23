# core-v5-skills — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Every skill edit goes through `superpowers:writing-skills` + `skill-eval` (CLAUDE.md §Skill architecture).

**Goal:** `netdust-wp` 1.0.0 teaches ntdst-core 5.0.0 — one contract skill on the three v5 doors, a drift reviewer that runs core's own invariants live, golden paths and security rules on the v5 surfaces, and evals that prove the old symbols are gone from what the skills teach.

**Architecture:** Three clusters on one branch. Cluster A rewrites the contract (`ntdst-framework/SKILL.md` + `traps.md`) that every other file cites, then the three golden paths against it. Cluster B re-cuts the drift reviewer into Part 1 (core's `Mechanical check:` lines, read from the consumer's vendored invariants doc at run time) and Part 2 (the consumer-only list), and re-points `wp-security` / `wp-plan-requirements`. Cluster C is proof and release: the retired-symbol grep, the rewritten + new eval cases, the REPORT re-run, the 1.0.0 bump, and the re-anchor task that waits for core-shape T13.

**Tech Stack:** Markdown skills + agent definitions (Claude Code plugin format), JSON eval cases, bash (`evals/run-correctness-eval.sh`, new `evals/retired-symbols.sh`), `python3` for JSON edits, `php -l` for golden-path code blocks (PHP 8.2 on this machine), a daan working copy (`~/Sites/daan`, `chore/core-path-repo`) for the reviewer dry run.

**Spec:** `specs/core-v5-skills/spec.md` (revision 0) ·
**Source of truth:** `~/Sites/ntdst-core` on `feat/core-shape` — `README.md` `### 5.0.0 — BREAKING` (its tables: "The breaks a rename does not carry", "Rename in the consumer before you bump core", "Extension points", "Core-trim — what left the package", the field-types table), `ARCHITECTURE-INVARIANTS.md` INV-1…10, `docs/philosophy.md`, `docs/parked/rest-query.md`, and the three specs.

**Repo:** `~/.claude/plugins/marketplaces/netdust-plugins` (the marketplace SOURCE — never the plugin cache under `~/.claude/plugins/cache/`), branch `feat/core-v5` off `main` @ `391eb0f`. All paths below are relative to `plugins/netdust-wp/` unless they start with `~`.

## Global Constraints

- **Edit the marketplace source, never the cache** (CLAUDE.md §8). A path containing `/plugins/cache/` in a diff is wrong by construction.
- **The skills describe v5 only** (D4). A retired symbol appears in exactly two places: a `## Retired` block (as a name, to refuse) and `*lessons.md` (as history). Anywhere else is a defect SC-1 catches.
- **One contract skill** (D2): no new skill directory; `wp-database`, `wp-frontend`, `wp-infra`, `wp-testing`, `bedrock-composer`, `ntdst-yootheme` are not edited.
- **Skills are contracts, not inventories** (CLAUDE.md): decisions, convergence points, traps — never a method list core's own refusals already teach.
- **Every claim about core is ground-truthed against `~/Sites/ntdst-core` source or README at the commit named in the skill header** — not against memory, not against the old skill text.
- **Eval cases carry `baseline_ref: "391eb0f — pre-v5 skill text"`, `must_contain`, `must_not_contain`** so `run-correctness-eval.sh` can discriminate mechanically (D5).
- Commits by pathspec, one per task, on `feat/core-v5`; **no push, no tag** (spec Out of scope).
- No Python dependencies beyond the standard library; the runner already uses `python3 -` heredocs.

---

## Stakes

Stakes: standard — a wrong line teaches every future consumer session a wrong convention, visibly (the agent writes `ntdst_actions()` and core fatals) and recoverably (edit the skill). Nothing here touches money, data, access or a live site.

Per-cluster refinement:
- **Cluster A (contract + golden paths):** standard — the text every other cluster cites; a wrong door here propagates.
- **Cluster B (reviewer + security):** standard — the reviewer's Part 1 must not silently skip; a skipped invariant reads as a pass, which is the failure mode `gate-check.py` guards against in its own domain.
- **Cluster C (proof + release):** low — mechanical; a failed eval is a red line, not a wrong site.

---

## Architecture invariants touched

This repo has no `ARCHITECTURE-INVARIANTS.md`; the plugin's standing rules are in `plugins/netdust-wp/CLAUDE.md` (the router-decides rule, pinned by the two `router-decides-brainstorm*` eval cases) and the global CLAUDE.md "Skill architecture" table. Both are untouched; SC-2 keeps the two control cases at their prior result.

The invariants this plan *serves* are core's: INV-1…10 in `~/Sites/ntdst-core/ARCHITECTURE-INVARIANTS.md`. T03's Part 1 reads their `**Mechanical check:**` lines at run time; T01's contract names each door by the invariant it establishes.

---

## Spec-premise ground-truth

| Premise | Verdict |
|---|---|
| "The eval runner takes `baseline_ref`, `must_contain`, `must_not_contain`, `context_before`, `context_after`" | **Confirmed.** `run-correctness-eval.sh` reads exactly `id`, `prompt`, `with_skill_assertion`, `baseline_ref`, `must_contain`, `must_not_contain`, `context_before`, `context_after` (grep of `c.get(`/`c[`). `context_*` are the skill files to load per arm. |
| "`baseline_ref` is a commit the runner checks the old skill text out of" | **Confirmed.** Existing cases use `"ffcd179 — pre-sweep skill text"`; the runner reads the file list in `context_before` at that ref. T05 uses `391eb0f`. |
| "The reviewer currently reads skills from `~/.claude/plugins/netdust-wp/...`" | **Confirmed — and stale.** `ntdst-drift-reviewer.md` `## Before you start` names `~/.claude/plugins/netdust-wp/skills/...`; the installed path is `~/.claude/plugins/cache/netdust-plugins/netdust-wp/<version>/...`. T03 makes the agent resolve the skill root from its own file location (`$CLAUDE_PLUGIN_ROOT` when set, else `dirname` of the agent file) instead of a hard path. |
| "Core's invariants doc has one `**Mechanical check:**` line per invariant" | **Confirmed** for INV-1…10 at `ff078f5`+ (`grep -c "Mechanical check" ARCHITECTURE-INVARIANTS.md` = 10). Each is a `grep` with an expected result in prose ("→ 0 hits", "= 0", "only `api/Data.php`"); T03 parses the command and reports the expected-result prose verbatim next to the actual count — it does not try to machine-judge the prose. |
| "Every D6 site vendors core at a known path" | **Confirmed.** daan/todai/netdust `web/app/mu-plugins/ntdst-core/`, josworld `app/content/mu-plugins/ntdst-core/`, stride `vendor/netdust/ntdst-core/` (Composer). T03's locator greps for `ARCHITECTURE-INVARIANTS.md` under those roots in that order, then falls back to `find <scope root> -name ARCHITECTURE-INVARIANTS.md -path '*ntdst-core*'`. |
| "`traps.md`'s non-stale traps survive v5" | **Partly.** Survive: `current_user_can('edit_posts')` as a read gate; `'default'` is inert; `label` on a scalar ignored; repeater key is `sub_fields`; unknown route option refuses; private-by-default; publish-only reads; `post_status` not `status`; friendly column vocabulary; `get()` returns a clone; `url()` drops unknown params; template paths read live; the rate-limiter three verbs; `required` three things; `select` does not validate. **Retired:** the `_enabled` fail-open row, `verifyOrigin()`, `{project}_{slug}_config`, raw `WP_Post` from a public handler (no public handlers now — `/wp/v2` projects), "repeater rows on a public payload" (all-or-nothing now), `assets` config key (Theme has no assets API at all), `find($id, true)`, `absint`/`signed_int`, the api_data gate order, `NTDST_Rest` envelope/`apiSuccessResponse`, "permission required and callable", preflight charging wording, `html`/`content`/`person` have no control, `number` sub-field only. T01 rewrites the file from this split. |
| "The golden paths' PHP blocks can be `php -l`'d" | **Confirmed with a step.** Blocks are fenced ```php; T02 extracts each to a temp file with `<?php` prepended when absent and runs `php -l`. Blocks that are fragments (a method body) are wrapped in `function _x(){ … }` for the lint only. |
| "`REPORT.md` documents how the runner is invoked" | **Confirmed.** `evals/run-correctness-eval.sh [cases.json] [out.json]`, run from `plugins/netdust-wp`; writes `evals/outputs/correctness-results.json`; six runs on 2026-08-20 of which run 6 is the record. |
| "`plugin.json` and the catalog both carry the version" | **Confirmed.** `plugins/netdust-wp/.claude-plugin/plugin.json:3` = `0.9.0`; `.claude-plugin/marketplace.json:30` = `0.9.0` with the description at `:29`. |

---

## First working version

**Task:** T01 — after it, the contract skill answers the three v5 questions a consumer session asks first, and the old answers are gone:

```bash
cd ~/.claude/plugins/marketplaces/netdust-plugins/plugins/netdust-wp
grep -n "ntdst_actions\|api_data" skills/ntdst-framework/SKILL.md      # only lines inside the "## Retired" block
grep -c "ntdst_rest\|->public()\|show_in_rest\|path(" skills/ntdst-framework/SKILL.md   # ≥ 8
sed -n '/## Pick the door/,/^## /p' skills/ntdst-framework/SKILL.md | grep -c '^| `'   # 3 doors
```

And the human check: open `SKILL.md`, read "Pick the door" — a declared field, a route, a page — and confirm each row's one-line rule matches what you would tell a developer today.

---

## Constitution check

- **Plugins provide capability, custom skills provide domain knowledge** (CLAUDE.md) — this plan edits domain knowledge only; no harness mechanics move.
- **Skills are contracts, not books** — T01's line budget (SC-3: ≤ 260) and the "no inventory" constraint enforce it; core's own refusals (unknown type, unknown route option, retired symbol fatals) are cited, not restated.
- **Lessons land where a future session reads them, with an eval** (CLAUDE.md §8) — every rewritten rule has a case in T05; `lessons.md` files are appended, never rewritten.
- **Marketplace source, never cache** — the repo path is pinned in the header; T06 bumps the version so the cache refreshes on Stefan's next `plugin update`.
- **Sites count, never design** — daan is the reviewer's dry-run host (T03), read-only.

## Phases & review clusters

| Cluster | Tasks | Stakes | Review tier |
|---|---|---|---|
| A — the contract and the paths | T01–T02 | standard | STANDARD |
| B — the reviewer and the rules | T03–T04 | standard | STANDARD |
| C — proof and release | T05–T07 | low | LIGHT |

Order A → B → C. B cites A's `SKILL.md` sections by heading; C's evals load A's files as `context_after`. T07 (re-anchor) is last and blocks on core-shape T13 — it is a `[HUMAN]` yield, not a wait loop.

---

## Interfaces

Names every task must use. An implementer sees only its own task; this block is how neighbouring tasks agree.

```text
# skills/ntdst-framework/SKILL.md — T01 writes, T02/T03/T04/T05 cite by heading
frontmatter.description: triggers name ntdst_rest(), ->public(), show_in_rest, NTDST_FieldTypes, ntdst_pages()->path(), ntdst_data(), plugin-config.php; NOT ntdst_actions()
# NTDST framework — the contract            (header: "ntdst-core 5.0.0 — anchored on specs core-shape rev 3 / field-types rev 3 / core-trim rev 2, README @ <sha>; pre-tag")
## Retired — a caller gets a fatal, deliberately   (v3 list kept + the v5 list: every left-column name of README's 5.0.0 tables)
## Pick the door                             (exactly 3 table rows: "A field the front end reads" → show_in_rest; "A command or a list WordPress cannot express" → ntdst_rest(); "A URL that is not a post" → ntdst_pages()->path())
## Data declares, WordPress reads            (17 types; show_in_rest; all-or-nothing repeater; json/array never publish; int signed; html = wp_kses_post; rest_query parked → docs/parked/rest-query.md; hooks ntdst/model/{creating,created,updating,updated,deleting,deleted})
## Rest is the one surface                   (internal default; ->public(); string = capability; write verb needs one; cors() REST-only, never '*'; rate_limit; client = wp.apiFetch)
## Pages on rewrite rules                    (path(':param', cb, method); callback returns path|null|false; placeholder-first refused; template()/single()/page()/archive() filter wraps; one loader: html(), page(), download(), inline())
## Boot: you load, core resolves             (require_once or Composer; metadata()['enabled'] / conditional; ntdst/service/{slug}/config; three lifecycle hooks)
## One of each                               (chain; ntdst_log(); Container set/get/has; Theme config + on()/filter(); Mailer → netdust-mail; Scheduler → two WP lines)
## Reference                                 (traps.md, baseline.md)

# skills/ntdst-framework/references/traps.md — T01
sections: ## Fails quiet (the dangerous class) · ## Silent no-ops · ## Reversed or non-obvious defaults · ## Routing · ## Rest · ## The rate limiter has three verbs · ## Admin fields
each trap row ends with "— pinned by <core test file or INV-n>"

# agents/ntdst-drift-reviewer.md — T03
## Part 1 — core's invariants, live
  locate(): for root in [<scope>/web/app/mu-plugins/ntdst-core, <scope>/app/content/mu-plugins/ntdst-core, <scope>/vendor/netdust/ntdst-core] then `find <scope> -name ARCHITECTURE-INVARIANTS.md -path '*ntdst-core*' | head -1`
  parse(): every line matching /^\*\*Mechanical check:\*\*\s*(.+)$/ → (INV-n from the nearest preceding "## INV-" heading, command = first backtick span, expectation = the rest of the line verbatim)
  run(): command with core's path tokens (`api core admin services support`, `api/*.php` …) replaced by the consumer's scope; report "INV-n · expected: <expectation> · actual: <count> hit(s)" + the hits
  absent doc → one line "Part 1 skipped — no ARCHITECTURE-INVARIANTS.md under <scope> (core < 4.x?)"; NEVER a pass
## Part 2 — consumer-only checks   (#1 repository bypass · #2 pass-through · #3 wp_ajax_/admin-post/register_rest_route → ntdst_rest() · #4 ob_start+include → html()/page() · #5 swallowed WP_Error · #6 friendly column vocabulary · #7 hardcoded meta prefix · #8 raw post/meta functions outside *Repository.php · #9 template_include filter → path()/template() · #10 injected-for-one-pass-through · #11 baseline solved it · #12 golden-path conformance · #13 zero-reader public symbol · #14 second API for a solved job · #15 function_exists() guard around a core helper)
output: the existing punch-list shape (file:line · category · what · rule reference · fix), Part 1 findings first, keyed INV-n

# evals/retired-symbols.sh — T05
usage: bash evals/retired-symbols.sh            # from plugins/netdust-wp; exit 0 = clean, 1 = hits printed as path:line
RETIRED=( 'ntdst/api_data' 'ntdstAPI' 'ntdst_actions' 'get_nonce' 'public_fields' 'publicRows' 'getFormattedPosts' 'ntdst_get_formatted_posts' 'sectors' 'ntdst_service_' 'auto_discover' 'discovery_paths' 'apiSuccess' 'apiError' '->json(' '->render(' 'ntdst_redirect' 'ntdst_mail' 'ntdst_schedule_recurring' 'ntdst_notify' 'ntdst_model_' 'mixin(' 'signed_int' 'wysiwyg' )
excluded: any line between a "## Retired" heading and the next "## " heading; files matching *lessons.md; everything under evals/

# evals/behavioral-lessons.json — T05: case shape (unchanged runner contract)
{ "id", "skill", "lesson", "baseline_ref": "391eb0f — pre-v5 skill text", "prompt", "baseline_expected_failure", "with_skill_assertion", "discriminator",
  "context_before": ["skills/ntdst-framework/SKILL.md", "skills/ntdst-framework/references/traps.md"],
  "context_after":  ["skills/ntdst-framework/SKILL.md", "skills/ntdst-framework/references/traps.md"],
  "must_contain": [...], "must_not_contain": [...] }
new ids: declared-field-exposure · write-verb-refused · custom-url-path-only · alias-refused
```

---

## Threat model

The spec flags no security surface (Markdown, JSON, one shell script; readers are agents). Named anyway, because a skill *is* an attack surface on future code:

1. **A skill teaches an open posture** — *Attack:* a rewritten example shows `->public()` on a write route, or `'permission' => '__return_true'`. *Mitigation:* T01's Rest section states the write-verb rule in the same paragraph as `->public()`; T05's `write-verb-refused` case `must_not_contain` `__return_true`; T04 keeps `__return_true` named as "the canonical bug" in `wp-security`.
2. **A skill teaches disclosure** — *Attack:* `content-type-feature.md` declares `show_in_rest` on every field by reflex. *Mitigation:* T02's golden path declares it on exactly the fields the front end reads and says why in the comment; T05's `declared-field-exposure` case asserts the all-or-nothing repeater rule is named.
3. **The reviewer reports a skipped invariant as clean** — *Attack/accident:* no invariants doc found → Part 1 prints nothing → the punch list reads as "core rules: no findings". *Mitigation:* T03's absent-doc line is mandatory and worded "skipped", and SC-4 counts 10 INV lines on daan.
4. **The reviewer runs core's grep over the wrong scope** — core's checks name core's paths (`api core admin services`); run literally on a consumer they hit nothing. *Mitigation:* T03 substitutes the consumer's scope and prints the substituted command with each finding so a reader can re-run it.
5. **Cache edited instead of source** — the lesson lands nowhere. *Mitigation:* Global Constraints; every task's commit step `git -C ~/.claude/plugins/marketplaces/netdust-plugins …`.

## Acceptance flows

No user-facing surface (spec). The shake-out equivalent is the eval run and the reviewer dry run, driven as a release manager would:

| # | Flow | Edge | Expected |
|---|---|---|---|
| AF-1 | `bash evals/retired-symbols.sh` on the finished branch | happy | exit 0, 0 lines |
| AF-2 | same, after deliberately adding `ntdst_actions()` to a golden path | **denied** | exit 1, one `path:line` printed |
| AF-3 | `bash evals/run-correctness-eval.sh` | happy | 13 cases run, 0 errored, ≥ 11 discriminate, ≥ 10 judge PASS; REPORT.md rewritten from `outputs/correctness-results.json` |
| AF-4 | reviewer on `~/Sites/daan` scope `web/app/mu-plugins/daan-core` | happy | Part 1: 10 `INV-n` lines with expected + actual; Part 2: the repository-bypass findings the 2026-08 run reported, none lost |
| AF-5 | reviewer on a scratch dir with no vendored core | **empty** | one "Part 1 skipped — no ARCHITECTURE-INVARIANTS.md" line; Part 2 runs |
| AF-6 | reviewer on stride (`vendor/netdust/ntdst-core` pinned v3.0.0, no invariants doc) | **boundary** | the same "skipped" line — and NOT a claim that stride meets INV-1…10 |
| AF-7 | `php -l` over every extracted golden-path block | happy | 0 syntax errors |
| AF-8 | a consumer session asked "add an endpoint" with the new skill loaded | happy (judge) | writes `ntdst_rest()` with a capability, never `ntdst_actions()` (eval `rest-handler-return`) |

---

## Loop budget

Loop budget: ~9 iterations — 7 tasks plus two expected review-fix rounds. Attended; T07 yields to Stefan and to core-shape T13. If driven by `/loop`, one cluster per wake, stop at every `── REVIEW GATE ──`.

---

## Sequencing note

- T01 before everything: T02–T05 cite its headings; an edit to a heading after T02 is a find-and-replace across four files.
- T05's `baseline_ref` is `391eb0f` — the commit *before* this branch — so the baseline arm reads the old skill text regardless of how many commits the branch has.
- T06 (version bump) before T07 (re-anchor) so the re-anchor commit is the last thing on the branch and Stefan's push carries a single version.
- T07 has two trigger points (core-shape T13 commit; the `v5.0.0` tag). The task is written once and run twice; the second run is expected to change nothing and says so in its commit.
