# Edge classes — where Review Focus lines come from

Green suites shipped every one of these. For a feature, name the classes it can actually
meet, most likely first, and pin each to a test in the task that owns the code. Omit a class
only with a written reason. (Incidents: Folio, 2026.)

1. **Empty / zero** — no data, blank input, first run, a prop a data layer toggles to empty
   (`refetch-toggle-blank-editor`: a refetch flipped `doc` to `undefined` and blanked the editor).
2. **Denied actor** — wrong role, second tenant, missing token; drive the denial through the
   whole chain, not the route function (`route-vs-service-guard`: the service ran a second
   mutation pass the route guard never saw).
3. **Wrong order / re-entry** — back button mid-wizard, refresh mid-flow, an action before its
   precondition, a second mount.
4. **Concurrent / double** — double-click submit, two tabs, racing requests
   (`double-submit-a11y-collision`).
5. **Boundary** — max length, zero, negative, off-by-one, unicode/emoji, the huge paste.
6. **Mid-flow failure** — network drop, a 500, the dependency down: does it roll back, clean
   up, tell the user (`bun-sqlite-no-rollback`).

Two more, from what green hid:

7. **Delivery seam** — the mail sends, the row writes, the webhook fires. The failure nobody
   sees by looking is the one even a low-stakes feature must drive.
8. **Shape, not behaviour / compiled, not rendered** — a test that asserts what a callable
   reference looks like never calls it (`shape-not-behaviour`); a build that exits 0 and
   changes a hash says nothing about the computed values on the page (`compiled-not-rendered`).
   Invoke it; compare rendered values to the design's own numbers.
