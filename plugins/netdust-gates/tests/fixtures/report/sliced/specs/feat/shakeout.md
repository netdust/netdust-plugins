# Shake-out — feat

| # | Flow | Layer | Verdict | Evidence |
|---|---|---|---|---|
| AF-1 | List shows rows | browser | pass | Test: tests/e2e/list.spec.ts :: list shows rows · Browser: https://x.ddev.site/wp/wp-admin/admin.php?page=rows · shakeout/list.png |
| AF-2 | List filters by type | browser | pass | Test: tests/e2e/list.spec.ts :: list filters by type · Browser: https://x.ddev.site/wp/wp-admin/admin.php?page=rows&type=a · shakeout/list-filter.png |
| AF-3 | Detail opens | browser | pass | Test: tests/e2e/detail.spec.ts :: detail opens · Browser: https://x.ddev.site/rows/1/ · shakeout/detail.png |
| AF-4 | Export downloads a CSV | wire | pass | Accepted-by-human: the export needs the cron the dev box lacks — driven by Stefan 11-06 |

Hunt: 3 charters · 1 confirmed · 1 not ours · 1 rejected
- charter: the list as a first-time visitor
- not ours: the footer's privacy link 404s | open any page, click Privacy
- rejected: rows sort by id | seed data has no dates
