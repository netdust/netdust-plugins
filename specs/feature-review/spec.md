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

**R6 — Promote reviews first, like opening a PR.** `make promote name=X` runs the review of
feature X after showing what it carries and before its "Continue?", so the review is read before
the feature lands. The review never refuses; a review that fails to run is reported and promote goes
on. `review=off|low|full|ultra` sets how much (default `full`), on `promote` and on `review`.
*Source: "what if reviews start before promote, but never stop promote and we add a flag to promote, to skip reviewers or tune them ( low, ultra or something? )"*

**R7 — The report is kept, like PR comments.** `make` saves it as `<git-common-dir>/reviews/<name>.md`
and prints its findings count and the follow-up command.
*Source: "it let the promote continue and propose a followup dev in same branch" · "if it follows what a pr is , good ,easy to understand."*

**R8 — `/review-fix X` is the follow-up commits.** In a session: check out `feature/X`, show the
saved findings, Stefan picks which to act on (decisions come back as questions), one fix pass
RED→GREEN, push; then `make promote name=X` again re-pins the fixed tip, like a push to the PR.
*Source: same.*

## Out of scope

Stamps, ship checks, and any refusal. Reviewers inspect; e2e on staging is the gate.
