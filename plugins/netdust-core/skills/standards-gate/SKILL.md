---
name: standards-gate
description: Stage-2 task-close gate that enforces a project's coding standards by actually RUNNING its linter/formatter on the touched files — eslint + prettier (TS/JS), phpcs (PHP/WordPress), biome, etc. — auto-detected per stack the way testing-workflow auto-detects the test runner. Adds a `Standards: clean | <violations>` line to the task's Test-evidence block, and is backstopped deterministically by the subagent-stop.py hook (which blocks a subagent close when a linter is configured but was never run). Closes the harness's goal #2: "respect any given coding standards" becomes enforced, not advisory. Fires at every code-task close alongside testing-workflow. NOT for projects with no linter configured (it no-ops), and not for doc/prose-only tasks.
---

<objective>
The harness enforced *tests* (testing-workflow + the subagent-stop hook) but only *advised*
coding standards — they lived in stack skills and reviewer agents as suggestions, and the
mandatory static-analysis step was a typecheck (`tsc --noEmit`), not a linter. This skill
closes that gap: at each code-task close it **runs the project's configured linter/formatter
on the touched files** and records the result, giving standards the same enforcement tier as
tests.

Two layers, same as the testing gate:
1. **This skill** = the discipline: detect the linter, run it on the diff, record the
   `Standards:` evidence line.
2. **`subagent-stop.py`** = the deterministic backstop: if the project has a linter
   configured and a code-editing subagent never ran it, the hook blocks the close.

The standard itself is declarative and lives upstream — in the project's linter config and
in the constitution's Article II (`constitution-bridge`). This skill *enforces* what those
*define*. It does not invent style rules.
</objective>

<process>

**Step 1 — Detect the linter (run once per session, cache).** Mirror testing-workflow's
Project Detection. Presence of any of these means standards are defined and this gate is live:

| Marker | Stack | Lint / format command (on touched files) |
|---|---|---|
| `.eslintrc*` / `eslint.config.*`, or `eslint` in `package.json` deps | TS/JS | `npx eslint <files>` |
| `.prettierrc*` / `prettier` in deps | TS/JS | `npx prettier --check <files>` |
| `biome.json` | TS/JS | `npx biome check <files>` |
| `package.json` `scripts.lint` / `scripts.format` | TS/JS | `npm run lint` (or the script's runner) |
| `phpcs.xml(.dist)` / `.phpcs.xml`, or `squizlabs/php_codesniffer` / WPCS in `composer.json` | PHP/WP | `vendor/bin/phpcs <files>` (prefix `ddev exec` if `.ddev/`) |
| `.php-cs-fixer*.php` | PHP | `vendor/bin/php-cs-fixer fix --dry-run <files>` |

If **none** is present, the project has no defined standard — **this gate no-ops**. Do not
hand-roll a style opinion; record `Standards: n/a — no linter configured` and move on. (The
backstop hook is also inert in this case, by the same `project_has_linter` check.)

**Step 2 — Run it on the touched files (not the whole repo).** Scope to the task's changed
files so the signal is about *this* task, not pre-existing debt. Run from the affected app's
directory (same rule as testing-workflow — never repo root for a monorepo).

**Step 3 — Fix or justify.** 
- Auto-fixable formatting (`prettier --write`, `phpcbf`, `php-cs-fixer fix`) → fix and re-run.
- Real lint violations → fix them; a lint rule firing on new code is the gate doing its job.
- A rule that is genuinely wrong for this code → disable it *narrowly and explicitly* (inline
  `// eslint-disable-next-line <rule> — <reason>` / `phpcs:ignore <sniff> — <reason>`), never
  a blanket file/project disable. An unexplained blanket disable is a failed gate.

**Step 4 — Record the evidence line.** Append to the task's `## Test evidence` block (the one
the harnessed-development dispatch addendum demands):

```
- Standards: clean | <N violations fixed> | n/a — no linter   (cmd: <what you ran>)
```

This line — visible in the report and commit body — is the auditable artifact, exactly like
the tier/RED-first/deferral lines. The `subagent-stop.py` hook is the backstop, not the
primary record.

</process>

<red_flags>

| Thought | Reality |
|---|---|
| "There's no linter, I'll just tidy it to my taste" | No. No config = no defined standard = this gate no-ops. Imposing your own style is the YAGNI/over-reach SOUL.md warns against. Record `n/a` and stop. |
| "Typecheck passed, that covers standards" | `tsc --noEmit` checks types, not style/lint rules. They are different gates. Run the linter too. |
| "I'll lint the whole repo to be safe" | Scope to the touched files — whole-repo lint surfaces pre-existing debt that isn't this task's job and drowns the real signal. |
| "This rule is annoying, I'll add `/* eslint-disable */` at the top" | Blanket disable = failed gate. Disable one rule, one line, with a reason — or fix the code. |
| "I ran prettier --write, good enough" | Re-run in check mode (`--check` / `phpcs`) and confirm clean. Auto-fix then verify; don't assume. |
| "I'll skip the Standards line, the lint passed anyway" | The line is the auditable evidence. No line = the backstop hook can't see it and the gate is honor-system again. Record it. |

</red_flags>

<success_criteria>
1. The linter was detected per the table (or `n/a` recorded when none configured).
2. It was actually RUN on the task's touched files (not the whole repo, not skipped).
3. Violations were fixed, or narrowly+explicitly justified inline.
4. A `Standards:` line is present in the task's Test-evidence block.
5. The subagent-stop backstop did not have to fire (it's a safety net, not the path).
</success_criteria>

<integration>

| Skill / artifact | Relationship |
|---|---|
| `netdust-core:testing-workflow` | **SIBLING at task close.** Tests = behavior, standards = style. Both gate the same close; the `Standards:` line sits in the same Test-evidence block. |
| `hooks/subagent-stop.py` | **DETERMINISTIC BACKSTOP.** Blocks a code-editing subagent close when a linter is configured (`project_has_linter`) but no lint command ran. |
| `netdust-core:constitution-bridge` | **DECLARATIVE SOURCE.** Constitution Article II names the standard this gate enforces. |
| `netdust-core:harnessed-development` | **SEQUENCER.** Invokes this at every Stage-2 code-task close, alongside testing-workflow. |
| stack sub-plugins (`netdust-wp`, …) | **OVERRIDE LAYER.** A stack may pin the exact ruleset (WPCS, PSR-12); detection picks up its config automatically. |

</integration>
