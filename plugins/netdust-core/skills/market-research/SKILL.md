---
name: market-research
description: Use when researching markets, competitors, audiences, pricing, positioning for client proposals or Netdust/Stride business decisions. Triggers when planning a sales conversation, drafting a proposal, evaluating a competitor's offering, deciding on pricing, or understanding a target audience. Activates on keywords competitor analysis, market positioning, audience research, pricing research, proposal, RFP, vertical analysis, customer interview, B2B SaaS pricing, WP agency pricing, LMS market. Symptoms include preparing for a client meeting with limited info, drafting pricing tiers for Stride, comparing FluentCRM vs Mailchimp for a client, sizing a market opportunity. Companion to research (technical) — this skill is for business/market questions.
---

# Market research

For business and market questions, not technical. For technical research, use `research`. For deep web investigation, the `deep-research` skill is the right tool.

## When to use this

- Drafting a client proposal and need to anchor pricing vs competitor offerings.
- Evaluating a new plugin/SaaS for a client's stack.
- Stride positioning: who is the actual buyer, what do they look at next to Stride?
- Sizing an opportunity ("how many Belgian nonprofits are large enough to need an LMS?").
- Pre-call homework on a prospect or client.

## Method

### 1. Define the question sharply

"What does the Belgian LMS market look like?" is unanswerable. "What LMS platforms are currently used by 5 Belgian nonprofits >50 employees, and what do they cost?" is researchable.

Reduce vague briefs to 1-3 sharp questions before searching.

### 2. Sources (in order)

1. **Direct conversations** — current clients, ex-clients, peers. The single highest-signal source.
2. **The competitor's own marketing** — pricing page, case studies, testimonials. Honest about who they aim at.
3. **Comparison sites** — G2, Capterra, Trustpilot. Filter by region + employee size to find Stride-shaped buyers.
4. **Public tenders / RFPs** — Belgian public-sector tenders are searchable on E-Procurement. Reveals real budgets and requirements.
5. **LinkedIn** — search the target buyer's job title; read their feed for the language they actually use.
6. **Industry reports** — Forrester, Gartner: expensive, often a generation behind. Use Sparked / Statista for cheaper-but-decent.
7. **Reddit / niche forums** — `r/WordPress`, `r/LMS`, /r/learndash — where practitioners complain about competitors.

For deep multi-source synthesis, escalate to `deep-research` skill.

### 3. Specific tactics

- **Pricing intel**: most B2B SaaS hides price. Tactics: book a demo with a throwaway email, ask peers who've signed, ask the prospect what they currently pay.
- **Feature parity**: open the competitor's docs site. The "comparison" pages on their site lie; the docs reveal what the product actually does.
- **Buyer language**: read 10 LinkedIn posts by the target persona. Use *their* words in proposals, not yours.
- **Win/loss**: when you lose a deal, ask why. Honestly. Pattern across 5 losses tells you positioning gaps.

### 4. Outputs

Write findings to `tasks/<topic>-research.md` (gitignored if sensitive). Format:

```markdown
# <topic> research — YYYY-MM-DD

## Question
<the sharp question>

## Findings
- <fact + source>
- <fact + source>

## Implications for Netdust/Stride
- <one-line>

## What we still don't know
- <gap>

## Confidence
high | medium | low — and why
```

## Anti-patterns

- "Research" that's actually opinion shopping (you already decided; you're just confirming). Devil's-advocate your own research.
- Pricing benchmarks from sites where the listed price is fictional (small-business directories).
- Treating one Reddit comment as the market.
- Extrapolating Belgian/Dutch market behavior from US data — the buyer behavior is different.
- Spending more on the research than the decision's value.

## When to stop

- The remaining open questions don't change the decision you'll make.
- More research has diminishing returns (you're rereading the same 3 sources).
- The decision can be tested cheaply in market (run a $200 LinkedIn ad and see who clicks).

## See also

- `research` — technical/code investigation
- `deep-research` — multi-source synthesis with credibility scoring
- `OSINT` — due diligence on specific people/companies
- `devils-advocate` — pressure-test the research conclusions before acting
- `brand-voice` — when the research output needs to be turned into prospect-facing copy
