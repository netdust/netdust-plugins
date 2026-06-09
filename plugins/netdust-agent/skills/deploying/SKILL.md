---
name: deploying
description: "CRAFT skill — a THIN pointer to the real deploy authority: the /deploy command (9-method dispatcher driven by site.yml's deploy.method) and the dev-stack skill. Reached for at harnessed-development Stage 3 (finish), AFTER shake-out + finishing-a-branch are green. It does not re-implement deploy mechanics; it routes to /deploy + dev-stack and states the Netdust deploy discipline: NEVER deploy to prod without explicit confirmation; honor site.yml deploy.method and site.risk (high = triple-check); always test on DDEV/staging before prod. The Netdust ordering layer: deploy is downstream of the WHOLE harness — shake-out and the reviews must be green first. Use when shipping a finished, reviewed branch to an environment. Fires on 'ship/push/deploy this to staging/prod/the customer', 'release the build', 'roll out', 'branch is merged and shake-out is green — push the build out to the customer's environment', 'get this live'."
---

<objective>
This skill is a **thin pointer**, not a deploy engine. The deploy mechanics already exist: the `/deploy` command is a 9-method dispatcher driven by `site.yml`'s `deploy.method`, and the `dev-stack` skill owns the environment + branch + Makefile flow. This skill's job is to **route you to them at the right moment, with the right guardrails** — nothing more.
</objective>

<route_to_the_authority>
**Run `/deploy`.** It reads `site.yml`'s `deploy.method` and dispatches the correct one of the 9 supported methods. For the surrounding flow — which branch deploys where, the Makefile targets, `.env` conventions, staging vs prod — defer to **`dev-stack`**. Do not hand-roll a deploy script when the dispatcher already knows the method for this site.
</route_to_the_authority>

<deploy_discipline>
The non-negotiable guardrails:
- **NEVER deploy to prod without explicit confirmation.** Prod is a deliberate, confirmed action — never a default, never implied by "ship it."
- **Honor `site.yml`'s `deploy.method` + `site.risk`.** The method is decided per-site in `site.yml`; do not override it ad-hoc. If `site.risk: high`, **triple-check** — re-confirm the target, the branch, and that the backup/rollback path exists before proceeding.
- **Always test on DDEV/staging before prod.** A change reaches prod only after it has run on a non-prod environment. Staging is the gate, not a formality.
</deploy_discipline>

<the_netdust_layer>
The ordering this skill exists to enforce — why it sits at the very end of the harness:

**Deploy is downstream of the WHOLE harness.** It is the last action of Stage 3, *after* `shake-out` swept the artifact and `finishing-a-branch` settled merge/PR/cleanup. **Shake-out and the reviewer agents must be green first** — deploying a branch that has not cleared shake-out + review ships unverified work to an environment. The sequence is fixed: execute → shake-out (+ reviews) → finish-branch → *then* deploy. If shake-out is not green, you are not at this skill yet.
</the_netdust_layer>

<success_criteria>
A deploy done under this skill:
- **Routed to `/deploy` + `dev-stack`** — did not re-implement the dispatcher.
- Ran only **after `shake-out` + reviews were green** and `finishing-a-branch` had settled the integration.
- Honored `site.yml`'s **`deploy.method`** and treated **`site.risk: high` as a triple-check** trigger.
- **Tested on DDEV/staging before prod**, and reached prod only with **explicit confirmation**.
</success_criteria>

<integration>
- **`/deploy`** — the AUTHORITY: the 9-method dispatcher driven by `site.yml`. This skill routes to it; it does the deploy.
- **`dev-stack`** — owns the environment / branch / Makefile / `.env` flow this skill defers to.
- **`harnessed-development` Stage 3 (finish)** — the step that reaches for this skill, after shake-out + finishing-a-branch.
- **`shake-out` + `finishing-a-branch`** — the gates that MUST be green before this skill runs; deploy is strictly downstream of them.
- **Provenance** — no addy/superpowers base; the deploy authority is Netdust's own `/deploy` + `dev-stack`. This file is a thin pointer that adds only the ordering + the prod-confirmation/`site.risk` discipline.
</integration>
