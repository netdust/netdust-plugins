# promote reviews first — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `make promote name=X [review=off|low|full|ultra]` shows the review before its "Continue?". `make review` takes the same level, and both save the report and name the follow-up.

**Architecture:** One new guarded command-line variable, `review`. The `review` target passes it on as `REVIEW_LEVEL`, saves the output to `<git-common-dir>/reviews/<name>.md`, and prints the `Findings:` line and `/review-fix <name>`. `promote` calls `$(MAKE) review` between showing the commits and asking to continue. A failed review is a warning, never a refusal.

**Tech Stack:** GNU make, sh; `dist/scripts/tests/flow-test.sh`.

**Spec:** specs/feature-review/spec.md (R6, R7)

## Global Constraints

- The review never refuses a promote. Only the operator's typed answer does, as today.
- `review=` joins `_CLI_GUARDED`. Its only values are `off low full ultra`, one word, checked like every guarded variable (`_cli-check`: refused when typed, dropped when inherited).
- The report lives under `git rev-parse --git-common-dir`, so every worktree sees it, and `make` writes it, not the reviewer. It never dirties a checkout.
- No `commands.review` declared: promote behaves exactly as today, with no review and no message.

## Review Focus

- A review that crashes: promote still reaches its "Continue?" and says the review did not run. (Task 1)
- `review=bogus`: refused by name, before anything runs. (Task 1)

**First working version:** Task 1.

**Simplest design:** promote calls the existing `review` target. There is no second review path.

---

### Task 1: `review=` and the promote hook

**Files:**
- Modify: `plugins/netdust-devops/dist/Makefile.netdust`: `_CLI_GUARDED` (line 25) with `_review-ok`/`_why-review` beside `_dryrun-ok` (≈ line 53); the `review` target (≈ line 499); `promote` (≈ line 207); the FLOW help lines for `promote` and `review`
- Modify: `plugins/netdust-devops/skills/devops/SKILL.md`: the `promote` and `review` verb rows, and a "What gets said" row: "review it before it lands" → `make promote name=X` (it reviews first)
- Modify: version 0.9.0 in `.claude-plugin/marketplace.json`, `plugins/netdust-devops/.claude-plugin/plugin.json`, `dist/VERSION`
- Test: `plugins/netdust-devops/dist/scripts/tests/flow-test.sh`, extending the "review: runs commands.review and reports back" section

- [ ] **Step 1: Failing tests.** Change the section's stub so it records the level and writes a findings line:

```bash
printf '#!/bin/sh\necho "name=$REVIEW_NAME scope=$REVIEW_SCOPE level=$REVIEW_LEVEL" | tee -a %s\necho "Findings: 1 Blocking · 0 Should fix · 2 Note"\n[ ! -e %s/review.fail ]\n' "$RLOG" "$TMP" > "$TMP/review.sh"
```

and update the section's two existing expected lines to carry ` level=full`. Then, before `git checkout -q -- site.yml`, add:

```bash
assert_refuses "review=bogus: refused by name" "Refused review=" M review name=banner review=bogus
M review name=banner review=low >/dev/null
assert_eq "review=low reaches the reviewer as REVIEW_LEVEL" "name=banner scope=feature level=low" "$(tail -1 "$RLOG")"
RD="$(git rev-parse --git-common-dir)/reviews"; ROUT=$(M review name=banner)
assert_eq "…the report is saved under the common git dir, and the findings line and follow-up are printed" "1 1 1" \
  "$(grep -c '^Findings: 1 Blocking' "$RD/banner.md") $(has "$ROUT" 'Findings: 1 Blocking') $(has "$ROUT" '/review-fix banner')"
git checkout -q -b feature/rv origin/main && echo rv > rv.txt && git add rv.txt && git commit -q -m rv && git push -q origin feature/rv
git checkout -q main; : > "$RLOG"; YF "make --no-print-directory promote name=rv"
assert_eq "promote reviews first (level full), then asks, then promotes" "0 name=rv scope=feature level=full 1" \
  "$YRC $(head -1 "$RLOG") $([ "$(printf '%s' "$YOUT" | grep -n 'Findings:' | cut -d: -f1)" -lt "$(printf '%s' "$YOUT" | grep -n "Continue?" | cut -d: -f1)" ] && echo 1)"
: > "$RLOG"; YF "make --no-print-directory promote name=rv review=off"
assert_eq "promote review=off: no review" "0 0" "$YRC $(wc -c < "$RLOG" | tr -d ' ')"
: > "$TMP/review.fail"; YF "make --no-print-directory promote name=rv"; rm -f "$TMP/review.fail"
assert_eq "a review that fails: promote says so and still promotes" "0 1" "$YRC $(has "$YOUT" 'review did not run')"
```

Promote needs no clean tree (`_ensure-flow` refuses only local commits missing from origin), so `commands.review` stays declared by the section's uncommitted `sed`, and origin's `main` is never touched. Restore after it, before the section's final tree assertion:

```bash
step unpromote name=rv; git push -q origin :refs/heads/feature/rv; git branch -q -D feature/rv; rm -rf "$RD"; git fetch -q --prune origin
```

- [ ] **Step 2: RED.** Run `cd plugins/netdust-devops/dist && bash scripts/tests/flow-test.sh 2>&1 | grep -E "FAIL|flow-test:"`. Expected: the new lines fail.

- [ ] **Step 3: Implement.** The guard:

```make
_CLI_GUARDED := env verb dryrun rung uploads review
_review-ok = $(and $(filter 1,$(words $(review))),$(filter off low full ultra,$(review)))
_why-review := off, low, full or ultra
```

In the `review` target, replace its last line with:

```make
	L="$(or $(review),full)"; [ "$$L" != off ] || { echo "review=off — nothing reviewed"; exit 0; }; \
	D="$$(git rev-parse --git-common-dir)/reviews"; mkdir -p "$$D"; OUT="$$D/$$N.md"; \
	echo "$(BLUE)$$R  ← $$S $$N ($$L)$(RESET)"; \
	REVIEW_NAME="$$N" REVIEW_SCOPE="$$S" REVIEW_LEVEL="$$L" sh -c "$$R" > "$$OUT.tmp"; RC=$$?; \
	cat "$$OUT.tmp"; mv "$$OUT.tmp" "$$OUT"; [ $$RC = 0 ] || exit $$RC; \
	echo ""; grep -m1 '^Findings:' "$$OUT" || true; \
	echo "$(YELLOW)report: $$OUT$(RESET)"; \
	[ "$$S" = staging ] || echo "$(YELLOW)follow-up: /review-fix $$N — then make promote name=$$N again$(RESET)"
```

(Delete the old `echo "$(BLUE)$$R  ← $$S $$N$(RESET)"; \` line above it.) In `promote`, between the `git --no-pager log …` line and `read -p "Continue? …`:

```make
	if [ "$(or $(review),full)" != off ] && [ -n "$$($(SITE) commands.review 2>/dev/null)" ]; then \
		$(MAKE) --no-print-directory review name=$(name) review=$(or $(review),full) \
			|| echo "$(YELLOW)⚠ the review did not run — promote goes on$(RESET)"; fi; \
```

FLOW help: promote → `"put a feature on $(BR_REVIEW) — reviews it first (review=off|low|full|ultra)"`; review → `"review a feature now (review=low|full|ultra); env=staging: where features meet"`. Version 0.9.0, with the description starting "0.9.0: make promote reviews the feature before its Continue? — like opening a PR; review=off|low|full|ultra; the report is saved under the common git dir with its findings line and the follow-up /review-fix. The review never refuses. ".

- [ ] **Step 4: GREEN.** Run `bash plugins/netdust-devops/tests/run.sh 2>&1 | tail -1`. Expected: `netdust-devops: all suites passed`.

- [ ] **Step 5: Commit.** `git add .claude-plugin/marketplace.json plugins/netdust-devops && git commit -m "feat(devops): promote reviews first, review= sets how much (0.9.0)"`
