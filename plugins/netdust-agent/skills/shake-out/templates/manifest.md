# Bug Manifest — [Project Name]

**Generated:** [date]
**Plan:** [plan file path]
**Build status:** Unit tests pass / spec complete
**Sweep status:** Automated [X checks] + Manual [Y checks]

---

## Summary

[Total] issues found: [N] critical, [N] important, [N] minor

---

## Root Cause Clusters

Group bugs that likely share a single root cause. This prevents fixing the same thing three times.

### Cluster A: [Name — e.g., "Auth token not propagating"]
- BUG-001, BUG-003 are likely the same root cause
- Fix at: [suspected origin point]

### Cluster B: [Name]
- BUG-002, BUG-005
- Fix at: [suspected origin point]

### Standalone
- BUG-004, BUG-006 — appear independent

---

## Bug List

### BUG-001 [CRITICAL] — [Short description]
- **Found by:** Automated / Manual
- **What happened:** [Actual behavior]
- **Expected:** [Expected behavior]
- **Where:** [File path / URL / endpoint]
- **Cluster:** A / Standalone
- **Status:** OPEN
- **Root cause:** [filled after fix]
- **Fix:** [filled after fix — commit SHA or description]

### BUG-002 [IMPORTANT] — [Short description]
- **Found by:** Automated / Manual
- **What happened:** [Actual behavior]
- **Expected:** [Expected behavior]
- **Where:** [File path / URL / endpoint]
- **Cluster:** B / Standalone
- **Status:** OPEN
- **Root cause:**
- **Fix:**

---

## Fix Log

| Bug | Attempts | Root Cause | Fix | Re-sweep |
|-----|----------|-----------|-----|----------|
| BUG-001 | 1 | [cause] | [commit/description] | PASS / FAIL |

---

## Final Status

**Resolved:** [N]
**Deferred:** [N] (with reasons)
**New bugs found during fix:** [N]
**Final sweep:** PASS / FAIL
