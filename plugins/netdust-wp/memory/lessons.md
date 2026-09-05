_Harness-self lessons for `netdust-wp`. Patterns that apply to the plugin's own development, not to user projects._

### 2026-05-17 — Stop hook silently skipping for months
Root cause: missing `ANTHROPIC_API_KEY` + no logging meant the hook was a no-op and nobody noticed. Fixed by (a) adding observability via `~/.claude/logs/memory-hook.log` and (b) switching the primary capture path to a deterministic tag-scanner that runs with zero deps. Haiku summarization is now opt-in, not the only path.

### 2026-05-17
- when a skill description leans on architectural verbs ("planning, designing, scaffolding"), it under-triggers on implementation-time prompts that just say "add a service that does X". The trigger sentence needs the literal phrases users actually type ("add a service", "write a service", "create a service") plus framework-keyword cues (`NTDST_Service_Meta`, `metadata()`, `plugin-config.php`). Scenarios 5+7 fired the skill cleanly because they used framework vocabulary; scenario 1 didn't.
- re-eval after skill changes is cheap (~30 min wall time, single session) and the per-scenario shape tells you more than the headline delta. Scenario 1's flip from +0 to +4 is the load-bearing signal from this run; the unchanged +15 total understates the qualitative win.

### 2026-06-09 — Mining real Stride into golden paths: the references describe the spine, but real code drifts at the edges
Built four golden-path docs (`ntdst-patterns/golden-paths/`) by extracting verified vertical slices from live Stride/Rossi source. What the mining taught about the gap between the rulebook and the real code:

- **The references are correct but altitude-mismatched.** `anti-patterns.md` shows ~15 isolated WRONG/CORRECT pairs; real features need the *whole slice wired together* (CPT→Repo→Service→Router→template). A model assembling from pairs reproduces each rule but not the seams between them. The golden path is the seams. (The folio lesson restated for WP: descriptions failed external agents, recipes fixed it.)
- **Drift concentrates at the layer boundaries the references can't see.** The Edition spine (CPT/Repo/Service/Router) is spotless against all nine drift greps — but the *frontend template* (`single-vad_edition.php:88`) drifts to `ntdst_data()` because themes can't use DI and the correct path loses the ergonomics race (now logged in `ntdst-core-gaps.md`). And the whole `Edition/Admin/` subfolder is drifted (raw `get_post_meta`, hardcoded `_ntdst_`). **Never extract a whole module as an exemplar — extract the verified-clean *spine* and explicitly mark the drifted parts "do not copy."** A "canonical" module is canonical in its middle, not its edges.
- **Verify candidates with the actual drift greps, don't trust the survey.** The Explore survey called Stride's settings "clean"; the greps confirmed `StrideSettingsService` clean but caught the Edition admin drift the survey glossed, and the one frontend drift line. Run the reviewer's own grep set against every candidate before citing it.
- **A "missing" archetype is a finding, not a failure.** Stride has zero YOOtheme (FSE stack); the clean exemplar was in Rossi. Flagging the origin and sourcing from the gallery site beat synthesising fake Stride code.
- **Plan-time injection (`wp-plan-requirements` Block 0) and review-time check (drift-reviewer #11) must name the SAME slice.** Same convergence discipline as the four pillars: a named golden path lets the reviewer flag "deviates from archetype X at layer Y" instead of re-discovering scattered cat-1 hits. An *unnamed* deviation is the finding; a named+justified one is permitted.

### 2026-08-20 — A stack plugin must not carve itself out of the router's decisions
Correction from Stefan during the ntdst-core 4.x re-anchor. This plugin's `CLAUDE.md`
said "WP work does **not** use generic `superpowers:brainstorming` — the framework
design skills replace it."

**Why it's wrong:** `harnessed-development` is always the entry point, and IT decides
whether the work brainstorms — by CLASS. Class A/B routes to `planning`, which invokes
brainstorming; C/D/E go straight to `building` and brainstorm nothing. A stack plugin
asserting "WP never brainstorms" pre-empts a decision that is not its to make, and gets
it wrong in both directions at once: it skips brainstorming on a Class A feature that
needed it, and implies a design stage on the Class E tweak that didn't.

**The general shape:** a stack plugin describes what it LAYERS ON at each point the
router reaches, never whether the router reaches it. Intent stays with brainstorming +
the human; the stack skills own the technical design shape on that stack. Restating or
replacing upstream superpowers content is the duplication drift that bloated 0.17 —
`netdust-agent` 0.18 was the re-thinning that removed it, and this line survived it.

**Second thing the same paragraph got wrong:** it described `harnessed-development` as
the skill that "sequences the full harness (design → plan → execute → shake-out →
finish)". It has not been a stage-sequencer since 0.18 — it is an intake ROUTER that
classifies and hands off. A doc that describes the old shape teaches a session to look
for stages that the skill no longer has.

**Check when editing any stack plugin's CLAUDE.md:** does a sentence decide something
the router decides (whether to plan, whether to brainstorm, which class this is)? If so
it belongs in `netdust-agent`, or nowhere.

- **2026-09-02 — ntdst-yootheme v2** (`specs/yootheme-skill-v2/`): the skill taught a
  retired source pattern in four places and recommended ACF in the binding reference;
  twenty verified traps sat only in josworld/edushare memory; the build loop was never
  written down. Now: the baseline module, `yoo-lint.php` (run before every write),
  `yoo-measure.mjs`, `workflow.md`, lessons by task. Gates: `evals/yootheme-anchor.sh`,
  `yootheme-budget.sh`, `yootheme-cases.sh`, `tests/yootheme/run.sh`.

- **2026-09-05 — scaffolding citizenne took five runs; every cause was in our own
  tooling, not the site.** The transferable parts:

  **Never read an exit code through `tee`.** `new-site.sh … | tee log` reports *tee's*
  status, so a run that died at step 5 of 13 was recorded as success and the first
  diagnosis went looking in the wrong place entirely. Redirect (`> log 2>&1`) and echo
  `$?`, or you are debugging a lie.

  **Never disable errexit to test code that runs under it.** `scaffold_project_meta`
  aborted on the CLEAN-render path — `grep` exits 1 on no match, pipefail propagated
  it, errexit killed the function — and the contract test passed throughout because it
  ran the function under `set +e`. The one line that mattered was the one the harness
  switched off. A test that relaxes the caller's shell options is not testing the
  caller.

  **Put repo hygiene ABOVE the gate, not below it.** The theme whitelist, the born-gated
  commit and (now) the rung branches all sat below step 13. A red gate aborted under
  `set -e` before them, so each failed attempt left the site's own theme untracked with
  zero commits — meaning every retry was a full wipe and re-run rather than a resume.
  Anything that makes the tree *recoverable* belongs before the thing that can fail.

  **The wp-starter payload's example tests drift against ntdst-core.** Two of them
  asserted an API that no longer exists — `Container::make()/forget()`, removed by core
  commit `6a14e5a` (core-trim T07), and `ntdst_model_create_after`, a hook core never
  fires (it is `ntdst/model/created`). Born-gated only means something if the payload
  tracks the framework; re-check these whenever core's surface changes.

  **`wp core download` has no stall detection and a 600s ceiling.** A wedged transfer
  burns the full ten minutes then dies (seen at 30.0MB of 35.4MB). `WP_CLI_CACHE_DIR`
  pointed at `/mnt/ddev-global-cache` is shared across every DDEV project, so warming it
  once makes core arrive in ~3s offline, forever.

  **`bin/new-project` only creates the three rung branches when it initialises the repo
  itself.** `new-site.sh` clones the template first, so `.git` exists, that arm never
  fires, and the site had no ladder for `make feature` / `make finish` / `make deploy`.

  Regression pins live in `netdust-wp-manager/scripts/tests/` (187 passing), not here —
  the fixes are script behaviour, and that suite is where they are held.
