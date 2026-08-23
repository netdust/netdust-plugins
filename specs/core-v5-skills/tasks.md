# core-v5-skills — tasks

Plan: `specs/core-v5-skills/plan.md` · Spec: `specs/core-v5-skills/spec.md` (rev 0)

Repo: `~/.claude/plugins/marketplaces/netdust-plugins` (marketplace SOURCE), branch `feat/core-v5`. Paths below are relative to `plugins/netdust-wp/`. Source of truth for every core claim: `~/Sites/ntdst-core` on `feat/core-shape` (README `### 5.0.0 — BREAKING`, `ARCHITECTURE-INVARIANTS.md`, `docs/philosophy.md`, `docs/parked/rest-query.md`, the three specs). Every skill edit goes through `superpowers:writing-skills` + `skill-eval`.

Every task closes with `bash evals/retired-symbols.sh` exit 0 once T05 exists (before T05, the task's own grep line) and one commit by pathspec. No push, no tag.

---

### Cluster A — the contract and the paths

Stakes: standard — the text every other file cites; a wrong door here propagates to every consumer session.

- [x] T01 — ntdst-framework SKILL.md + traps.md rewritten as the v5 contract [Tier B]  (files: skills/ntdst-framework/SKILL.md, skills/ntdst-framework/references/traps.md, skills/ntdst-framework/lessons.md)
  Satisfies: FR-1, FR-2, SC-3
  Test-author: solo — prose rewrite with mechanical pins; no code path
  Proven by: machine gate — the three commands in plan `## First working version` return their stated values; `wc -l SKILL.md` ≤ 260; every `traps.md` row ends with `— pinned by <file or INV-n>` (`grep -c "— pinned by" traps.md` = number of `|`-rows minus headers)
  Unit test: none (Tier B). SKILL.md: header reads `ntdst-core 5.0.0 — anchored on specs core-shape rev 3 / field-types rev 3 / core-trim rev 2, README @ <sha of ~/Sites/ntdst-core HEAD at edit time>; pre-tag`; frontmatter description triggers list `ntdst_rest()`, `->public()`, `show_in_rest`, `NTDST_FieldTypes`, `ntdst_pages()->path()`, `ntdst_data()`, `plugin-config.php` and no longer `ntdst_actions()`; sections exactly as the plan's Interfaces block names them (`## Retired`, `## Pick the door`, `## Data declares, WordPress reads`, `## Rest is the one surface`, `## Pages on rewrite rules`, `## Boot: you load, core resolves`, `## One of each`, `## Reference`); `## Retired` = the v3 list kept + every left-column name in README's 5.0.0 tables (ground-truth: `grep -E "^\| \`" ~/Sites/ntdst-core/README.md` inside `### 5.0.0`); `## Pick the door` = 3 rows. traps.md: rewritten from the plan's ground-truth split (survivors kept, retired rows dropped, the v5 traps added: `custom-fields` widens `meta`, partial repeater reads `null`, `int` signed, `bool` `"false"` → false, renamed hook inert, origin list REST-only, placeholder-first `path()` refused, `select` does not validate, `required` three things). lessons.md: one appended entry "v5 re-anchor 2026-08-23" listing what changed and why, never a rewrite of history.

- [x] T02 — the three golden paths on the v5 doors [Tier B]  (files: skills/ntdst-patterns/golden-paths/form-data-flow.md, skills/ntdst-patterns/golden-paths/content-type-feature.md, skills/ntdst-patterns/golden-paths/admin-settings-page.md)
  Satisfies: FR-3, SC-5
  Test-author: solo — prose + code blocks; lint is the gate
  Proven by: machine gate — `grep -cE "api_data|ntdstAPI|ntdst_actions|get_nonce|->render\(|'integer'|'boolean'|wysiwyg|signed_int" <each file>` = 0; every ```php block extracted (prepend `<?php` if absent; wrap a bare method body in `function _x(){…}`) passes `php -l`; `form-data-flow.md` contains `wp.apiFetch` and `permission` and not `get_nonce`
  Unit test: none (Tier B). `form-data-flow.md`: the file table names `ntdst_rest()` route class, `wp.apiFetch` call, repository; the sequence diagram is `wp.apiFetch → POST /<ns>/v1/<route> (X-WP-Nonce) → permission (capability | ->public() + rate_limit) → handler → repository->create() → WP_REST_Response | WP_Error`; the thin-handler paragraph says a handler returns `WP_REST_Response` or `WP_Error` with `['status' => …]`, never an array envelope. `content-type-feature.md`: the model declares canonical types only; `'show_in_rest' => true` on exactly the fields the front end reads, with a comment saying a declared field is public to anyone; reads go to `/wp/v2/<type>`; a custom list route only for logic the collection cannot express, with one sentence naming `docs/parked/rest-query.md` for a plain meta filter; repeater declared with `sub_fields` every one of which is declared when the repeater is. `admin-settings-page.md`: the save path is a capability-gated `ntdst_rest()` route or the Settings API; the page renders through `html()`/`page()`; no `render()`.

Integration gate: `cd ~/.claude/plugins/marketplaces/netdust-plugins/plugins/netdust-wp && grep -rcE "api_data|ntdstAPI|ntdst_actions\(|get_nonce|->render\(" skills/ntdst-framework/SKILL.md skills/ntdst-framework/references/traps.md skills/ntdst-patterns/golden-paths/*.md | grep -v ":0$"` — expected: only `SKILL.md` (its `## Retired` block) and only for `ntdst_actions(`/`api_data`.

── REVIEW GATE ── *(provisional tier: STANDARD — reviewer + code-simplicity)*

---

### Cluster B — the reviewer and the rules

Stakes: standard — the reviewer's Part 1 must never read a skipped invariant as a pass; a wrong security line teaches an open posture.

- [x] T03 — ntdst-drift-reviewer: Part 1 runs core's invariants live, Part 2 is the consumer-only list [Tier A]  (files: agents/ntdst-drift-reviewer.md, agents/ntdst-drift-reviewer.lessons.md)
  Satisfies: FR-4, SC-4
  Test-author: solo — an agent definition; the denial path (absent doc → "skipped", never a pass) is pinned by a dry run
  Proven by: machine gate — three dry runs with the rewritten agent: (a) `~/Sites/daan` scope `web/app/mu-plugins/daan-core` → Part 1 prints exactly 10 `INV-` lines each with `expected:` and `actual:`; (b) a scratch directory with two PHP files and no vendored core → the single line `Part 1 skipped — no ARCHITECTURE-INVARIANTS.md under <scope>`; (c) run (a)'s Part 2 findings compared with the prior agent's run on the same working copy (`git stash`-free: run the old agent text from `391eb0f` via a temporary copy) → 0 repository-bypass findings lost
  Unit test: the agent file: `## Before you start` resolves the skill root from `$CLAUDE_PLUGIN_ROOT` when set, else the agent file's own directory's parent — no literal `~/.claude/plugins/netdust-wp` path; `## Part 1 — core's invariants, live` carries the locator (three known roots, then `find`), the parser (`**Mechanical check:**` lines → INV-n, first backtick span = command, rest = expectation verbatim), the scope substitution rule (`api core admin services support` and `api/*.php`-style path lists → the consumer scope), the report line shape `INV-n · expected: … · actual: N hit(s)` followed by the hits, and the mandatory absent-doc line; `## Part 2 — consumer-only checks` has exactly 15 numbered checks in the plan's Interfaces order, each with a grep and a then-column, where #3 reads "`wp_ajax_*`, `admin-post`, or `register_rest_route()` outside `ntdst_rest()` → the framework path is `ntdst_rest($ns)->…` with a capability", #4 "`ob_start`+`include` → `ntdst_response()->html()` or `page()`", #9 "`add_filter('template_include'` → `ntdst_pages()->path()` or `->template()`", and #13–#15 are the three new ones (zero-reader public symbol: `grep -rn "public function NAME\|function ntdst_NAME"` then count readers outside the file; second API for a solved job: two public entry points whose bodies reach the same repository method or WP call; `function_exists('ntdst_`-guards around a core helper). lessons.md: one appended calibration entry (the 2026-08-22 scan: eight type tables, zero-reader symbols, load-order guards — "this should have been picked up by drift reviewers").

- [ ] T04 — wp-security's NTDST section and wp-plan-requirements' drift example on v5 [Tier B]  (files: skills/wp-security/SKILL.md, skills/wp-plan-requirements/SKILL.md)
  Satisfies: FR-5
  Test-author: solo — two paragraphs; the grep is the gate
  Proven by: machine gate — eight `grep -cF` single-term checks (ugrep-safe; `\|` under `-c` counts lines and mis-parses on this machine): `api_data`/`Actions.php`/`verifyOrigin` = 0 and `ntdst_rest` ≥ 2, `X-WP-Nonce` ≥ 1, `->public()` ≥ 1, `allowed_http_origins` ≥ 1 in wp-security; `api_data` = 0 and `Part 1` ≥ 1 in wp-plan-requirements (plan correction at the T04 review — the original alternation line returned 3 on packed bullets)
  Unit test: none (Tier B). wp-security `### NTDST` bullets become: REST routes register through `ntdst_rest()` only; the gate is `permission` — a capability string, `->public()`, or a callable — and `__return_true` written by hand is still the canonical bug; cookie callers authenticate with `X-WP-Nonce` through `wp.apiFetch`, core mints nothing (`rest_cookie_check_errors()` is the CSRF rule); a write verb with only a posture does not register; `cors()` feeds `allowed_http_origins` for REST requests only and refuses `'*'`; a field with `show_in_rest => true` is readable by anyone on `/wp/v2/<type>` — a mis-declaration is a disclosure; legacy `wp_ajax_*` keeps its `check_ajax_referer()` line. wp-plan-requirements: the golden-path deviation example reads "settings save uses the WP Settings API, not an `ntdst_rest()` route — flat option set" and the drift-category line points at "`ntdst-drift-reviewer` Part 1 (core's invariants) and Part 2 (consumer checks)".

Integration gate: `cd ~/.claude/plugins/marketplaces/netdust-plugins/plugins/netdust-wp && grep -rcE "api_data|ntdstAPI|ntdst_actions\(|verifyOrigin|template_include" agents/ntdst-drift-reviewer.md skills/wp-security/SKILL.md skills/wp-plan-requirements/SKILL.md | grep -v ":0$"` — expected: only `agents/ntdst-drift-reviewer.md` for `template_include` (check #9 names it as the thing to replace) and `ntdst_actions(` inside its Part 2 #3 "drift toward" wording.

── REVIEW GATE ── *(provisional tier: STANDARD — reviewer + code-simplicity)*

---

### Cluster C — proof and release

Stakes: low — mechanical; a red eval is a red line, not a wrong site.

- [ ] T05 — evals: retired-symbols.sh, 7 cases rewritten + 4 new, runner executed, REPORT rewritten [Tier A]  (files: evals/retired-symbols.sh, evals/behavioral-lessons.json, evals/REPORT.md, evals/outputs/correctness-results.json)
  Satisfies: FR-6, SC-1, SC-2
  Test-author: solo — the evals ARE the tests; `retired-symbols.sh` is written RED first (it must print hits on `391eb0f`'s skill text and 0 on the branch)
  Proven by: machine gate — `git stash`-free check: `git show 391eb0f:plugins/netdust-wp/skills/ntdst-framework/SKILL.md > /tmp/old.md && bash evals/retired-symbols.sh /tmp/old.md` exits 1 with ≥ 10 lines; `bash evals/retired-symbols.sh` on the branch exits 0; `bash evals/run-correctness-eval.sh` → `outputs/correctness-results.json` shows 13 cases, 0 errored, ≥ 11 discriminate, ≥ 10 judge PASS, the two `router-decides-brainstorm*` cases at their 2026-08-20 result
  Unit test: `retired-symbols.sh`: takes optional file args (default: every `*.md` and `*.json` under the plugin except `evals/` and `*lessons.md`); strips `## Retired` blocks (a heading line matching `^## Retired` up to the next `^## `) before grepping; loops the 24-entry `RETIRED` array from the plan's Interfaces block with `grep -nF`; prints `path:line: symbol`; exit 1 on any hit. Cases: `api-rate-budget` → `rate_limit`/`rate_window` on an `ntdst_rest()` route, 429 with `retry_after`, `must_not_contain` `get_nonce`, `ntdstAPI`; `pages-custom-route` → `ntdst_pages()->path('share/exhibitions/:slug', $cb)` alone, `must_not_contain` `add_rewrite_rule`, `query_vars`, `ntdst_router(`; `rest-cors-option` → `cors(['https://app.example'])` feeds `allowed_http_origins`, REST-only, `must_not_contain` `NTDST_Cors_Policy`, `Access-Control-Allow-Origin`; `service-disable-filter` → `metadata()['enabled'] => false` or a `conditional` entry, `must_not_contain` `ntdst_service_`, `update_option`; `theme-facade-retired` → `$theme->pages()` fatals, use `ntdst_pages()`, `must_not_contain` `mixin(`, `apiAction`; `rest-handler-return` → handler returns `WP_REST_Response`/`WP_Error`, route named with a capability, `must_contain` `ntdst_rest(`, `must_not_contain` `apiSuccessResponse`, `ntdst_actions(`; `route-response-refuses` → a `path()` callback returns `false` for 404 and never exits, `must_not_contain` `->render(`, `exit`. New: `declared-field-exposure` (prompt: which gig fields reach `/wp/v2/gigs` and can a repeater hide `sale_price`; `must_contain` `show_in_rest`, assertion names all-or-nothing), `write-verb-refused` (prompt: `ntdst_rest('x/v1')->post('/purge', $h)` with no permission — what happens; `must_contain` `does not register` or `_doing_it_wrong`, `must_not_contain` `__return_true`), `custom-url-path-only` (prompt: make `/card/:slug` render a template; `must_contain` `path(`, `must_not_contain` `add_rewrite_rule`, `template_include`), `alias-refused` (prompt: field declared `'type' => 'integer'`; `must_contain` `int`, assertion says fatal at `register()` naming the canonical). All cases `baseline_ref` `391eb0f — pre-v5 skill text`, `context_before`/`context_after` = the framework SKILL + traps. `REPORT.md` rewritten from the results: per-case discriminate/judge table, the method paragraph kept.

- [ ] T06 — netdust-wp 1.0.0: plugin.json, marketplace catalog, README line [Tier B]  (files: .claude-plugin/plugin.json, ../../.claude-plugin/marketplace.json, README.md)
  Satisfies: FR-7, SC-6
  Test-author: solo — version fields
  Proven by: machine gate — `python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])"` = `1.0.0`; the catalog entry for `netdust-wp` = `1.0.0` and its description contains `ntdst-core 5.0.0`; `git log --oneline main..feat/core-v5 | wc -l` ≥ 6
  Unit test: none (Tier B). README's "ntdst-core framework skills" row gains "(ntdst-core 5.0.0)"; nothing is pushed.

- [ ] T07 — re-anchor on core-shape T13 and on the v5.0.0 tag [Tier B]  (files: skills/ntdst-framework/SKILL.md, skills/ntdst-framework/references/traps.md, evals/REPORT.md)
  Satisfies: FR-8, SC-7
  Test-author: solo — a diff against README, run twice
  Proven by: machine gate — `diff <(grep -oE "^\| \`[^\`]+\`" ~/Sites/ntdst-core/README.md | sed -n '/5.0.0/,/4.4.2/p' | sort -u) <(sed -n '/^## Retired/,/^## /p' skills/ntdst-framework/SKILL.md | grep -oE "\`[^\`]+\`" | sort -u)` prints 0 lines in the README-only direction; SKILL.md header's `README @ <sha>` equals core-shape's T13 commit (run 1) and the `v5.0.0` tag (run 2); `run-correctness-eval.sh` re-run, REPORT.md updated with the run date
  Unit test: none (Tier B). Run 1 fires when `git -C ~/Sites/ntdst-core log --oneline -1 -- README.md` shows the core-shape T13 commit (its message names FR-13); run 2 at `git -C ~/Sites/ntdst-core tag -l v5.0.0` non-empty. Each run: re-read README's 5.0.0 tables and `ARCHITECTURE-INVARIANTS.md`, fix every disagreement in SKILL.md/traps.md, update the header anchor, commit `docs(ntdst-framework): re-anchor on <sha>` — run 2 is expected to change only the header and says so.

Integration gate: `cd ~/.claude/plugins/marketplaces/netdust-plugins/plugins/netdust-wp && bash evals/retired-symbols.sh && bash evals/run-correctness-eval.sh && python3 -c "import json;r=json.load(open('evals/outputs/correctness-results.json'));print(len(r), sum(1 for c in r if c.get('errored')))"` — expected exit 0, `13 0`.

── REVIEW GATE ── *(provisional tier: LIGHT — reviewer)*

---

## [HUMAN] yield points

- After Cluster A's review gate — read `## Pick the door` once: three rows, three rules. This is the sentence every consumer session will act on; confirm it reads the way you would say it.
- Before T06 — the version becomes 1.0.0 in the catalog; confirm the marketplace push is yours to do later (this plan never pushes).
- T07 run 1 — blocks on core-shape T13 landing in `~/Sites/ntdst-core`; say when, or let the session check `git log -- README.md` at its next wake.
- T07 run 2 — blocks on the `v5.0.0` tag (core-shape T14, itself a `[HUMAN]` yield there).
