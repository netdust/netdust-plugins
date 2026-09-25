# Spec — make review

**Repo:** `netdust-plugins` · **Plugins:** `netdust-devops`, `netdust-gates`
**Provenance:** Stefan, 2026-09-25.

## Problem / why

Reviewers only run when an agent following the policy reaches Close. A feature started by hand
gets no review, because there is nothing to call.

## Requirements

**R1 — `make review name=X`** runs the project's `commands.review` for feature X, and `make review
env=staging` runs it for staging. It prints what comes back. No stamp, no gate.
*Source: "make review name=X should trigger an angent that drives some subagent reviews and then the first one reports back … no hard gate"*

**R2 — `/feature-review <name | staging>`** is that agent. It dispatches the reviewers as
subagents in parallel, then reports their findings back in one summary. It works with or without
a plan.
*Source: same; "if i start a feature manually, without a plan, there's no reviewers"*

**R3 — The staging review looks only where promoted features meet.**
*Source: "how do i call review of entire staging then? make review env=staging"*

**R4 — Close calls it.** The policy's Close step 3 is `make review name=<feature>`, or
`/feature-review <feature>` on a project without devops.
*Source: invented — approved 2026-09-25 ("ok, sounds good")*

**R5 — `/shakeout` works on a branch with no spec.** It derives the changed surfaces from the
diff and commit messages, explores them on the running app, and proposes a flow list that Stefan
approves before any test is written. Then it drives, commits and registers the flows as usual,
so a hand-started feature reaches `make e2e env=staging` too.
*Source: "what if we start creating a branch and finish a feature without a spec / plan. then we need a command that checks the branch" · "its seperate from review, add it like you say"*

## Out of scope

Stamps, ship checks, and any refusal. Reviewers inspect; e2e on staging is the gate.
