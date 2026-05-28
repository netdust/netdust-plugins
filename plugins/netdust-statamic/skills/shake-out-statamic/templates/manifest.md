# Bug Manifest — [Project Name]

**Generated:** [date]
**Plan:** [plan file path]
**Stack:** Statamic 6 + Peak
**Build status:** Unit tests pass / spec complete
**Sweep status:** Automated [X checks] + Manual [Y checks]

---

## Summary

[Total] issues found: [N] critical, [N] important, [N] minor

---

## Root Cause Clusters

Group bugs that likely share a single root cause. Statamic clusters often share a **stache**, **blueprint**, **partial**, or **fieldset** origin — fixing the source resolves multiple symptoms.

### Cluster A: [Name — e.g., "Stale stache after blueprint rename"]
- BUG-001, BUG-003 — likely same root cause
- Fix at: [suspected origin — blueprint / partial / config]
- Stache action required: yes / no

### Cluster B: [Name]
- BUG-002, BUG-005
- Fix at: [suspected origin]

### Standalone
- BUG-004, BUG-006 — appear independent

---

## Bug List

### BUG-001 [CRITICAL] — [Short description]
- **Found by:** Automated / Manual / Existing test
- **What happened:** [Actual behavior]
- **Expected:** [Expected behavior]
- **Where:** [File path / URL / blueprint handle / block partial]
- **Layer:** Content / Routing / Rendering / Page Builder / Assets / Forms / CP / Deploy
- **Cluster:** A / Standalone
- **Reproduction:**
  ```
  [exact curl / mcp / chrome-devtools steps]
  ```
- **Status:** OPEN
- **Root cause:** [filled after fix]
- **Fix:** [filled after fix — commit SHA or description]
- **Stache cleared after fix:** yes / no / not applicable

### BUG-002 [IMPORTANT] — [Short description]
- **Found by:** Automated / Manual
- **What happened:**
- **Expected:**
- **Where:**
- **Layer:**
- **Cluster:** B / Standalone
- **Reproduction:**
- **Status:** OPEN
- **Root cause:**
- **Fix:**
- **Stache cleared after fix:**

---

## Fix Log

| Bug | Attempts | Root Cause | Fix | Test Added | Re-sweep |
|-----|----------|-----------|-----|------------|----------|
| BUG-001 | 1 | [cause] | [commit/description] | tests/Feature/[X]Test.php / N/A | PASS / FAIL |

---

## Final Status

**Resolved:** [N]
**Deferred:** [N] (with reasons)
**New bugs found during fix:** [N]
**Final sweep:** PASS / FAIL
**Stache warm + search index updated:** yes / no
**Pint clean:** yes / no
