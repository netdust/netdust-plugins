# make review — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `make review name=X` / `make review env=staging` runs `commands.review` and prints its report.

**Architecture:** One target in the vendored core, following the pattern of `gate`/`e2e`/`smoke`: read `commands.review` from `site.yml`, run it with `REVIEW_NAME` and `REVIEW_SCOPE` set.

**Tech Stack:** GNU make, sh; `dist/scripts/tests/flow-test.sh`.

**Spec:** specs/feature-review/spec.md (R1)

## Global Constraints

- The Makefile never calls an LLM itself. The `claude -p` line lives in `site.yml` (template, doctor hint).
- `name=` is checked with `_check-name` before any shell line reads it, like every `name=` verb.
- No stamp, no tag, no change to `ship`.

## Review Focus

- A name outside the charset (`a;b`) is refused before anything runs. (Task 1)
- `env=production` is refused by name, because production only carries what staging had. (Task 1)

**First working version:** Task 1.

**Simplest design:** this is the simplest one: a thin runner, in the pattern `e2e` already uses.

---

### Task 1: the `review` target

**Files:**
- Modify: `plugins/netdust-devops/dist/Makefile.netdust`: add the target after `e2e` (≈ line 495), a FLOW help line after `save` (≈ line 110), and `_DOCTOR_COMMANDS` + `_doctor-line-review` (≈ line 985)
- Modify: `plugins/netdust-devops/templates/site.yml.tmpl`: add `review:` after `e2e:`
- Modify: `plugins/netdust-devops/skills/devops/SKILL.md`: one verbs-table row
- Modify: version 0.8.0 in `.claude-plugin/marketplace.json`, `plugins/netdust-devops/.claude-plugin/plugin.json`, `dist/VERSION`
- Test: `plugins/netdust-devops/dist/scripts/tests/flow-test.sh`: a section after "ship waits for the staging e2e" (≈ line 491), plus the FLOW vocabulary line (105)

- [ ] **Step 1: Failing tests.** Insert:

```bash
echo; echo "flow — review: runs commands.review and reports back"
git checkout -q main; RLOG="$TMP/review.log"; : > "$RLOG"
assert_refuses "review with no commands.review: refused naming the key" "No commands.review" M review name=x
printf '#!/bin/sh\necho "name=$REVIEW_NAME scope=$REVIEW_SCOPE" | tee -a %s\n' "$RLOG" > "$TMP/review.sh"
sed -i "s|^commands: {gate: \(.*\)}$|commands: {gate: \1, review: sh $TMP/review.sh}|" site.yml
assert_refuses "review with neither name= nor env=: usage" "Usage: make review" M review
assert_refuses "a name outside the charset, before anything runs" "Invalid name" M review 'name=a;b'
assert_refuses "env=production: refused by name" "staging only" M review env=production
ROUT=$(M review name=banner)
assert_eq "review name=banner runs commands.review for the feature, and prints what it says" "name=banner scope=feature 1" "$(tail -1 "$RLOG") $(has "$ROUT" 'name=banner scope=feature')"
M review env=staging >/dev/null
assert_eq "review env=staging runs it for staging" "name=staging scope=staging" "$(tail -1 "$RLOG")"
git checkout -q -- site.yml
assert_eq "…and the review section leaves the tree clean, origin untouched" "" "$(git status --porcelain)"
```

Change line 105's expected vocabulary to `"feature hotfix save review promote unpromote gate ship"`.

- [ ] **Step 2: RED.** Run `cd plugins/netdust-devops/dist && bash scripts/tests/flow-test.sh 2>&1 | grep -E "FAIL|flow-test:"`. Expected: the new lines and line 105 fail.

- [ ] **Step 3: Implement.**

```make
# The review is the project's own reviewer (commands.review): an agent that runs the
# reviewers and reports back. It reads and reports; it stamps and gates nothing.
.PHONY: review
review: ## Review a feature (make review name=X) or where staging's features meet (make review env=staging)
	@$(if $(name),$(call _check-name,review,my-feature))
	@R=$$($(SITE) commands.review 2>/dev/null); \
	if [ -z "$$R" ]; then \
		echo "$(RED)✗ No commands.review in site.yml — nothing knows how to review$(RESET)"; \
		printf "$(YELLOW)  e.g. %s$(RESET)\n" '$(_doctor-line-review)'; exit 1; fi; \
	if [ -n "$(name)" ]; then N="$(name)"; S=feature; \
	elif [ "$(env)" = staging ]; then N=staging; S=staging; \
	elif [ -n "$(env)" ]; then echo "$(RED)✗ review env= takes staging only — production carries only what staging had$(RESET)"; exit 1; \
	else echo "$(RED)✗ Usage: make review name=<feature>  ·  make review env=staging$(RESET)"; exit 1; fi; \
	echo "$(BLUE)$$R  ← $$S $$N$(RESET)"; \
	REVIEW_NAME="$$N" REVIEW_SCOPE="$$S" sh -c "$$R"
```

FLOW help after `save`: `@printf "  $(GREEN)%-22s$(RESET) %s\n" "review name=X" "run the reviewers on a feature and report (commands.review); env=staging: where features meet"`.
Doctor: `_DOCTOR_COMMANDS := gate smoke e2e review` and `_doctor-line-review := review: claude -p "/netdust-gates:feature-review"`.
Template, after `e2e:`:

```yaml
  # The reviewers, on demand: `make review name=<x>` / `make review env=staging` runs this with
  # REVIEW_NAME and REVIEW_SCOPE set. It reports; it gates nothing. '' opts out.
  review: claude -p "/netdust-gates:feature-review"
```

SKILL.md verbs row: `| make review name=X | run commands.review on feature X (env=staging: where the promoted features meet) and print its report — reviewers inspect, they gate nothing |`. Version 0.8.0, with the description starting "0.8.0: make review name=X / env=staging runs commands.review (an agent that dispatches the reviewers and reports back); no stamp, no gate. ".

- [ ] **Step 4: GREEN.** Run `bash plugins/netdust-devops/tests/run.sh 2>&1 | tail -1`. Expected: `netdust-devops: all suites passed`.

- [ ] **Step 5: Commit.** `git add .claude-plugin/marketplace.json plugins/netdust-devops && git commit -m "feat(devops): make review runs the reviewers on demand (0.8.0)"`
