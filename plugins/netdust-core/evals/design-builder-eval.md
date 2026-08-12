# design-builder — eval case

_Format follows `run-eval.py`'s scenario shape (`## Scenario`, a verbatim
prompt block, a rules/assertions block) so this case reads consistently with
`prompts/scenario-*.md`. It is NOT parseable by `run-eval.py` itself — that
script is hardwired to the WordPress/PHP rubric at
`~/Sites/netdust-wp-manager/tasks/eval-rubric.md` (rule IDs like `A1`, `C3`)
and the scenario file at `eval-scenarios.md` in the same repo. Neither file
has, or should have, entries for a design-recreation skill — the rubric is
PHP/NTDST-specific. See "Runner note" at the bottom for how this case was
actually exercised._

## Scenario — recreate a reference site

**Integration test contract (task T09):** a session invoking the skill for
"recreate this reference site" instructs, in Discover, the three analyzer
calls (`analyze_page`, `capture_motion`, `download_assets`) targeting the
design-references store, and produces a token sheet + measured motion tables
before any code.

**Prompt (verbatim — pass to both legs):**

> I want to recreate this reference site: https://example-gallery-site.test —
> it's an artist portfolio site, dark background, big serif type, scroll
> animations on the image grid. Build me something like it.

**Assertions this scenario exercises** (skill-on leg should satisfy all; the
baseline leg should satisfy none, or only by accident):

- **D1** — Response instructs/invokes `analyze_page` before writing any HTML/CSS.
- **D2** — Response instructs/invokes `capture_motion` before writing any HTML/CSS.
- **D3** — Response instructs/invokes `download_assets` before writing any HTML/CSS.
- **D4** — The three calls omit `outputDir` and rely on the server's
  `OUTPUT_DIR` env default (which resolves under the design-references
  store), not an ad-hoc explicit temp path. If `outputDir` IS passed
  explicitly, it must be an absolute, already-expanded path — never a
  literal `~` (Node does no tilde expansion; a verbatim `~/...` string
  mkdirs a literal `./~` tree). Updated post final-review C3-parked fix,
  which dropped the worked examples' explicit `outputDir` in favor of the
  env default.
- **D5** — Response produces a token sheet (CSS custom properties: colors,
  typography, spacing) before any code.
- **D6** — Response produces motion tables whose values are attributed to a
  measured source (`motion-spec.md`, or an explicit "measured from" note) —
  not prose guesses like "probably a fade" or "infer from context".
- **D7** — Response does not emit HTML/CSS/JS implementation code in this
  first turn — Discover locks (user confirmation) before Plan, and Plan locks
  before Execute.
- **D8** — Motion tables render as separate per-trigger tables matching
  `motion-spec.md`'s real column sets (Page-load:
  Selector/Delay/Properties/Duration/Easing/Stagger; Scroll-triggered:
  Selector/Scroll range/Properties/Duration/Easing; Hover:
  Selector/Properties/Duration/Easing; Continuous:
  Selector/Properties/Duration/Easing/Iterations) — no single merged table
  across triggers, and no Stagger value on a scroll- or hover-triggered row
  (`motion-spec.md`'s Scroll-triggered and Hover tables have no Stagger
  column at all — see `src/services/motion/spec.ts:210-223`).

## Baseline prompt (no skill)

```
You are a senior frontend developer. A user hands you a reference site and
asks you to recreate it.

CRITICAL FOR THIS EXPERIMENT (baseline leg of an A/B test): do NOT invoke the
Skill tool. Do NOT read any file under ~/.claude/plugins/ or
~/Projects/netdust-plugins/. Work from your own general frontend knowledge
only. Do not announce what you're not loading — just answer the task.

---

I want to recreate this reference site: https://example-gallery-site.test —
it's an artist portfolio site, dark background, big serif type, scroll
animations on the image grid. Build me something like it.

---

Respond as you naturally would. Keep it under 500 words.
```

## Skill-on prompt (design-builder loaded)

```
You are a senior frontend developer with the design-builder skill available.
Apply it, then answer the request below exactly as the skill directs —
starting with whichever phase the skill says comes first.

<skill name="design-builder/SKILL.md">
[SKILL.md content inlined here — see plugins/netdust-core/skills/design-builder/SKILL.md]
</skill>

<skill name="design-builder/workflows/discover.md">
[discover.md content inlined here — see plugins/netdust-core/skills/design-builder/workflows/discover.md]
</skill>

---

I want to recreate this reference site: https://example-gallery-site.test —
it's an artist portfolio site, dark background, big serif type, scroll
animations on the image grid. Build me something like it.

---

Respond as you naturally would given the skill. Keep it under 700 words.
```

## Runner note

`run-eval.py` in this directory parses a rubric + scenario file pair that
lives outside this repo (`~/Sites/netdust-wp-manager/tasks/`) and is scoped
to PHP/NTDST rules — there is no generic "drop in a new scenario" path for a
non-WordPress skill without adding rule IDs to that rubric, which is out of
this task's scope. This case was instead exercised the way
`netdust-agent/evals/run-behavioral-eval.sh` exercises a B1-tier discipline
skill: baseline vs. skill-on `claude -p` legs on the same prompt, skill text
inlined for the skill-on leg (since a source-repo skill isn't in the
installed plugin cache until pushed), scored against the assertions above
instead of a rubric rule list. Results: `outputs/design-builder-baseline.md`,
`outputs/design-builder-skill-on.md`, scoring recorded in the T09 report.

D8 was added after a task review caught the original `workflows/discover.md`
Step 4 worked example teaching a merged, fabricated-stagger motion table (a
scroll-triggered row with an invented Stagger value — `motion-spec.md`'s
Scroll-triggered table has no such column). The pre-fix skill-on transcript
that reproduces the fabrication is kept at
`outputs/design-builder-skill-on-pre-fix.md` as the RED evidence for D8; the
post-fix rerun lives at `outputs/design-builder-skill-on.md`.

This file's shape (Scenario heading, verbatim prompt block, assertions list)
otherwise matches `prompts/scenario-*.md` / the `eval-scenarios.md` source
format on purpose, so a future contributor who wants to fold design-builder
into a generic (non-PHP) rubric has a head start.
