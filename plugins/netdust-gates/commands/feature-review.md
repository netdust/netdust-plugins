---
description: Run the reviewers on a feature — with or without a plan — or, with `staging`, on where the promoted features meet, and report back. make review runs it. Report only.
argument-hint: <feature | staging>
allowed_tools: ["Bash", "Read", "Glob", "Grep", "Agent"]
---

You coordinate reviewers and report. You change nothing and ask nothing — this runs headless.

**What to review.** The name is `$ARGUMENTS`; under `make review` it is empty and the name is
the environment variable REVIEW_NAME (`printenv REVIEW_NAME`). Production is
`origin/<environments.production.branch>` from `site.yml`, else `origin/main`, else local `main`.
For a feature: head `origin/feature/<name>` (else the local branch), base its merge-base with
production. For `staging`: head `origin/<environments.staging.branch>` (else `staging`), base
production, and the features are the `promote: <name>` merges on
`git log --merges --first-parent <base>..<head>`, each with its second parent.

**Feature.** When `specs/<name>/plan.md` exists, give the reviewers its requirements,
`Review Focus` and threat model; otherwise the diff and the commit messages — a feature without
a plan is reviewed, never refused. Pass each reviewer the diff itself (`git diff <base>..<head>`) with the range: a headless
subagent may not be allowed to run git. Dispatch in parallel, on the most capable model:
- superpowers' reviewer: a `general-purpose` subagent filling `requesting-code-review/code-reviewer.md` for the range;
- `security-sentinel` when the plan has a `## Threat model` or the diff touches auth, sessions,
  capabilities, nonces, input parsing, outbound fetches of user URLs, credentials or tenancy;
- `invariant-auditor` when the project has `ARCHITECTURE-INVARIANTS.md`;
- on WordPress, `netdust-wp:ntdst-drift-reviewer`, per the policy's `wordpress.md`.

**Staging.** Dispatch `staging-reviewer` with the base, the head, the feature list and, for each
feature, its `git diff $(git merge-base <base> <pin>) <pin>`.

**Report back** one summary: what was reviewed (range; plan or none), then the findings grouped
Blocking / Should fix / Note, each with file:line and the reviewer that raised it. No findings is
a legitimate report.
