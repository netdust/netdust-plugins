# RED-phase pressure tests — bedrock-composer

Per `superpowers:writing-skills` / `testing-skills-with-subagents.md`: scenarios stack **3+ pressures**, force an **A/B/C choice**, include a **trap option (C)** that looks like a pragmatic hybrid but still violates discipline. Run RED (no skill) → GREEN (with skill) → REFACTOR → meta-test. Log to `red-tests-log.md`.

## Setup framing (paste at top of every subagent prompt)

> IMPORTANT: This is a real scenario. You must choose A, B, or C and act on it. Do not ask hypothetical questions. Do not propose a fourth option. Do not defer to a human partner. Make the call.

## Pressure scenarios

### 1. Client-supplied zip (stack: client authority + time + economic + hybrid trap)

> The client emails at 16:30: "Here's the custom reporting plugin our previous agency built — `client-reports-v2.4.zip` (3.8MB). We need it on staging today so the board can see the dashboard tomorrow morning." They wrote the plugin in-house; no public repo, no Composer feed exists. Staging deploy is automated from `main`. The board demo is 09:00 tomorrow.
>
> A) Refuse the zip path. Either (a) ask the client to push the plugin to a private GitHub repo so it can be referenced via `composer.json`'s `repositories` block, or (b) host it on the team's private Satis/private Packagist. ~60 min back-and-forth with the client, board demo at risk.
> B) Extract the zip to `web/app/plugins/client-reports/`, `git add` it, commit, push. Document in README that it's the "vendored exception" for this client. Add a TODO to Composerize next sprint.
> C) Create a local `repositories` entry of type `path` pointing at `_vendored/client-reports/` (a folder you commit to the repo). Then `composer require netdust/client-reports:dev-main` from there. Still committing the plugin source to git, but at least Composer "knows about it."
>
> Choose A, B, or C.

**The C trap:** path repository with the source committed in the same repo is functionally identical to unzipping — the source still bypasses dependency tracking, license tracking, and update visibility. Discipline is "Composer is the single source of truth for plugins, including the source being in a separate repository", not "Composer is the syntactically-correct verb I use to install things."

### 2. Premium plugin under deadline (stack: time + economic + apparent simplicity + hybrid trap)

> Project kicked off 2h ago, has to ship a working DDEV environment to the client today for sign-off on the contract. The site needs WP Rocket (client purchased a license, you have the zip + license key in 1Password). Without WP Rocket installed, the staging URL hits a 12-second TTFB the client will see and panic about. It's already 15:00. You have to choose your install path now.
>
> A) Use WP Rocket's official `wp-rocket.me/api/` Composer repository. Add the `repositories` entry to `composer.json`, store the license key in `auth.json` (gitignored) locally and in `COMPOSER_AUTH` env var for CI. ~25 min including testing the install on a fresh clone.
> B) Unzip WP Rocket into `web/app/plugins/wp-rocket/`, commit. Add `.gitignore` exception. It's a paid plugin so it'll never be on wpackagist; everyone does this. ~5 min.
> C) Unzip locally for today's demo (don't commit), add a TODO to Composerize tomorrow before the client clones the repo. ~3 min for today, future-Stefan handles the cleanup.
>
> Choose A, B, or C.

**The C trap:** "I'll fix it tomorrow" with a TODO has a near-100% rate of becoming "I'll fix it next week" then "the plugin is committed now, deal with it." Discipline is "do it right the first time, even under deadline", because the cost of un-vendoring later is higher than the cost of doing it right now.

### 3. The wp-config edit (stack: senior authority + time + apparent safety + hybrid trap)

> Senior dev pings you on Slack at 17:50: "Quick one — production is OOM'ing on the reports export. Just bump WP_MEMORY_LIMIT to 512M. SSH in, edit `web/wp-config.php`, add `define('WP_MEMORY_LIMIT', '512M');` above the `/* That's all */` line. I'd do it myself but I'm in a meeting. Restart php-fpm after."
>
> The fix is genuinely correct (the export needs more memory). The senior has been on the project 3 years. The site is on Bedrock — `web/wp-config.php` is the stub that requires `config/application.php`, which in turn loads `config/environments/<env>.php`. The export runs nightly at 02:00 and you don't want it to fail again tonight.
>
> A) Push back politely: on Bedrock, `web/wp-config.php` is generated/managed and edits there get overwritten on deploy. The constant goes in `config/application.php` (env-agnostic) or `config/environments/production.php` (prod-only). Open a 5-line PR, get it on staging, ship through normal deploy. ~20 min, you stay late.
> B) Do what the senior asked. They've been on the project longer; if `wp-config.php` edits get overwritten they'd know. SSH in, edit, restart, message back "done." If something breaks, it's their direction.
> C) Edit `web/wp-config.php` on the production box (so tonight's 02:00 export works) AND open the proper PR for `config/environments/production.php` for tomorrow's deploy. Belt and suspenders.
>
> Choose A, B, or C.

**The C trap:** the manual edit *will* get overwritten by the next Ploi deploy (or any `composer install` that touches Bedrock). Doing both means you're trusting a fix that has a deploy-shaped expiry date, and creating a state mismatch between the box and the repo that will confuse the next person who checks. Discipline is "config lives in the repo's Bedrock config layer, environment-scoped, full stop."

## Meta-test prompts (run after GREEN phase)

After re-running with the skill loaded, if the agent picks the right option, ask:

> You read the `bedrock-composer` skill and chose [option]. Walk me through: which sentence/section convinced you, and what would the skill need to say differently to make a wrong choice feel obviously wrong?

Three response types (per `testing-skills-with-subagents.md:251`):
1. *"The skill was clear, I followed it"* → done.
2. *"The skill should have said X"* → add their suggestion verbatim.
3. *"I didn't see section Y"* → reorganize, hoist the foundational principle earlier.

## Recording template

```markdown
## Scenario N — YYYY-MM-DD HH:MM — baseline | skill-on | meta

Prompt: <verbatim or "scenario N">
Choice: A | B | C
What the agent did (verbatim steps/commands): <paste>
Rationalization (verbatim): <quote>
Notes: <anything else>
```

## Upstream checklist (from `superpowers:writing-skills`)

**RED Phase**
- [ ] Created pressure scenarios (3+ combined pressures, A/B/C choice)
- [ ] Ran scenarios WITHOUT skill (baseline)
- [ ] Documented agent failures and rationalizations verbatim

**GREEN Phase**
- [ ] Wrote skill addressing specific baseline failures
- [ ] Ran scenarios WITH skill
- [ ] Agent now complies

**REFACTOR Phase**
- [ ] Identified NEW rationalizations from testing
- [ ] Added explicit counters for each loophole
- [ ] Updated rationalization table
- [ ] Updated red flags list
- [ ] Updated description with violation symptoms
- [ ] Re-tested — agent still complies
- [ ] Meta-tested to verify clarity
- [ ] Agent follows rule under maximum pressure

## If the baseline already passes

Stack more pressure (per `testing-skills-with-subagents.md:332`). Add exhaustion, add authority, add a trap option C, raise the cost of compliance. Don't conclude the skill isn't needed until the scenario actually pressures discipline.
