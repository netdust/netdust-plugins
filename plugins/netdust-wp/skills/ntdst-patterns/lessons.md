# NTDST Patterns — Lessons

Project incidents that became structural/placement rules, and the freshness journal for the golden-path exemplars. Each entry: what happened, what we learned, where the rule now lives.

For canonical structure rules read `SKILL.md`; for the worked vertical slices read `golden-paths/*.md`. This file is the journal — it explains *why* those say what they say, and records when a golden path was re-verified against its live source.

---

## Match the framework, not the closest sibling

**Problem (Stride, 2026-05-19):** When adding new code, copying the nearest existing file propagates whatever drift that sibling already carries — two dialects then coexist in one module and diverge over time. Sibling files are not the spec; the framework reference is.

**Rule:** Build to the framework reference (and now the matching `golden-paths/*.md` slice), never to the nearest sibling. The golden path names what changes per project vs what never does — so "the sibling does it this way" is not justification for a structural choice.

**Where it lives:** `SKILL.md` → *Golden paths* routing table; enforced at review by `ntdst-drift-reviewer` check #11 and front-loaded into plans by `wp-plan-requirements` Block 0.

---

## Golden-path freshness journal

The four `golden-paths/*.md` docs cite live Stride/Rossi source down to file:line. Source evolves; the slices can go stale (same failure class as a stale test baseline). Each doc carries a `Verified against source: YYYY-MM-DD` header; `/skill-audit` flags any not re-verified in 90 days, and `compounding`'s spec-close harvest re-runs the drift greps when a golden-path *source* project is touched.

Record re-verifications here:

- **2026-06-09** — Four golden paths authored + blessed against live source (Edition spine, ProfileHandler, StrideSettingsService from Stride; ArtistSourcesService from Rossi). All drift-clean at authoring. Initial `Verified against source` date stamped on all four.
