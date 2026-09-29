# Review — devops-composer-hygiene

Range 97a9237..6e9395b · no plan · superpowers code-reviewer (no threat model, no invariants, not WordPress).
Verdict: ready with fixes. Composer rule verified against Composer 2.8.9 source (DownloadManager::getAvailableSources).

## Blocking
None.

## Should fix
1. lessons.md:53 / SKILL.md:225 — the map does not heal an already-cloned server: composer keeps a package's previous install source on update. Docs needed the one-time cleanup. — FIXED in the fix pass (SKILL.md, lessons.md, eval `map-does-not-heal-a-cloned-server`).

## Note (all six fixed on request, Stefan 2026-09-29)
2. dist/Makefile.netdust:661 — ssh without BatchMode/ConnectTimeout; a dead host hangs health (pre-existing in other sections). — FIXED
3. dist/Makefile.netdust:661 — `df -P /` measures root, not the sites' filesystem (separate volume, Combell quota). — FIXED
4. SKILL.md:229 — disk bullet sits in the first-bring-up list; belongs near `make health` at :127. — FIXED
5. tests/test-makefile.sh:1079 — no case for the unreachable branch or two distinct hosts. — FIXED
6. SKILL.md:226 — map names only netdust/*; say "each private vendor before *". — FIXED
7. skills/parallel-work/SKILL.md:57 — still says packages install "with --prefer-source". — FIXED
