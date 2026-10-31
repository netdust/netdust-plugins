# EVAL scenario 1 — SKILL-ON leg

Identical to scenario-1-baseline.md, EXCEPT: before answering, read
plugins/netdust-core/skills/worktable/SKILL.md, simulating the skill being loaded, and follow it
where it applies. The baseline leg's prohibition on reading plugin files is lifted for that file only.

You are a Claude Code coder session in ~/Sites/shop-theme (repo path `/home/stefan/Sites/shop-theme`),
on branch `feature/checkout-steps`. The session-start hook printed:
`**Box:** worktable ✓ · herdr ✓ · ddev ✓ · browser ✓ · gate: make gate`.
The worktable MCP server is connected: its tools are `schema`, `rows`, `create`, `update`, `action`, `history`.

`specs/checkout-steps/plan.md` has five tasks:

```
### Task 1: Address step component
### Task 2: Shipping options from the carrier API
### Task 3: Payment step with Mollie
### Task 4: Order summary
### Task 5: Confirmation mail
```

The plan was revised this morning: Task 4 used to be "Order summary with coupons"; Task 6 "Coupon field"
was dropped from the plan. You just finished Task 2 (commit `4f1c2a9`, all its tests green) and are about
to start Task 3. Nobody has touched Studio since yesterday.

What the tools would answer (take these as given, do not invent others):
- `rows werkpakket` filtered on repo and branch → one row: `{ id: 12, naam: "Checkout steps", fase: "bouwen", laatste_stap: "Task 1 klaar", volgende_stap: "Task 2", voortgang: "1/5" }`
- `rows taak` filtered `{ werkpakket_id: 12 }` →
  `{ id: 40, stap: "Task 1", titel: "Address step component", status: "gedaan", wie: "claude" }`,
  `{ id: 41, stap: "Task 2", titel: "Shipping options from the carrier API", status: "bezig", wie: "claude" }`,
  `{ id: 43, stap: "Task 4", titel: "Order summary with coupons", status: "open", wie: "claude" }`,
  `{ id: 44, stap: "Task 6", titel: "Coupon field", status: "open", wie: "claude" }`,
  `{ id: 45, stap: null, titel: "Ask the client for the Mollie test keys", status: "open", wie: "stefan", deadline: "2026-11-03" }`

**Do not run any command and call no tool.** This is a written answer.

---

List, in order, every worktable tool call you make now (tool, dataset, id or filter, values), each with
one line of why, and stop at the call that starts Task 3. Under 350 words.
