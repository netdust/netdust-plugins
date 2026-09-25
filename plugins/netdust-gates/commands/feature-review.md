---
description: Run the reviewers on a feature — with or without a plan — or, with `staging`, on where the promoted features meet, and report back. make review runs it. Report only.
argument-hint: <feature | staging>
allowed_tools: ["Bash", "Read", "Glob", "Grep", "Agent"]
---

You coordinate reviewers and report. You change nothing and ask nothing — this runs headless.

**What to review.** The name is `$ARGUMENTS`, else `$REVIEW_NAME`. For a feature: head
`origin/feature/<name>` (else the local branch), base its merge-base with the production branch
(`environments.production.branch` in `site.yml`, else `main`). For `staging`: head
`origin/staging`, and the features are its `promote: <name>` merges with each second parent.

**Feature.** When `specs/<name>/plan.md` exists, give the reviewers its requirements,
`Review Focus` and threat model; otherwise the diff and the commit messages — a feature without
a plan is reviewed, never refused. Dispatch in parallel:
- superpowers' reviewer: a `general-purpose` subagent filling `requesting-code-review/code-reviewer.md` for the range;
- `security-sentinel` when the plan has a `## Threat model` or the diff touches auth, sessions,
  capabilities, nonces, input parsing, outbound fetches of user URLs, credentials or tenancy;
- `invariant-auditor` when the project has `ARCHITECTURE-INVARIANTS.md`.

**Staging.** Dispatch `staging-reviewer` with the base, the head and the feature list.

**Report back** one summary: what was reviewed (range; plan or none), then the findings grouped
Blocking / Should fix / Note, each with file:line and the reviewer that raised it. No findings is
a legitimate report.
