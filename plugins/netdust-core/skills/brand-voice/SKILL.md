---
name: brand-voice
description: Use when writing or editing prose in Stefan's / Netdust's voice — landing copy, blog posts, sales emails, client proposals, social posts, project descriptions, README intros, conference talk abstracts. Triggers when generating marketing or written communication for Netdust BV or Stride LMS. Activates on keywords write copy, blog post, landing page, proposal, pitch, social post, README, abstract, intro, sales email. Symptoms include drafting any prose Stefan will sign off on or that goes out under the Netdust/Stride name. Companion to the marketing skill (which covers SEO + structure) — this skill is about the voice itself.
---

# Brand voice — Stefan / Netdust / Stride

Stefan has 25 years of PHP/WordPress and runs Netdust BV. The voice is the voice of someone who has shipped a lot, knows the craft, and doesn't oversell.

## Voice signature

| Always | Never |
|---|---|
| Direct, declarative sentences | Hyperbolic claims ("revolutionary", "game-changing") |
| Concrete examples ("VAD's 4000-user LMS") | Vague proof ("enterprise-grade") |
| Trade-offs surfaced ("X is faster but harder to maintain") | "Best of both worlds" |
| Plain Dutch or plain English — never both badly | Random English jargon in Dutch copy ("scalable oplossing") |
| Specific verbs ("ships", "migrates", "encodes") | "Empowers", "leverages", "synergizes" |
| Numbers when they're real | Numbers when they're fluff ("100x productivity") |
| Honest "we don't do X" | Listing services to look bigger |
| "I" / "we" / "you" — direct address | "Customers / partners / stakeholders" |

## Reference texts

- **Netdust homepage** — short, brutally specific about what Netdust does and doesn't do.
- **Stride landing copy** — positions against generic LMS bloat, emphasizes "for organizations that train teams, not for course marketplaces".
- **Stefan's GitHub README style** — exposition first, code second, no emoji unless asked.

## Voice in different contexts

### Sales / landing copy

```
Stride is a learning platform for organizations that train teams, not a marketplace.

You run trainings. We run the platform. Your enrollment, attendance, invoicing, and reporting in one place — without LearnDash's marketplace assumptions getting in the way.

Used by VAD Vormingen for 4000+ learners.

[See it →]
```

Notes: short paragraphs, specific noun ("VAD"), specific number ("4000+"), single CTA. No filler.

### Blog post

```
# Why we left ACF for code-defined fields

Three years on ACF Pro. We migrated 11 client projects to native blocks + code-defined fields. Here's what we won and what we lost.
```

Notes: titled with the conclusion, not "the journey". Open with specifics (3 years, 11 projects). Promise both sides (won and lost).

### Client proposal

```
What you'll get
- A Stride-based platform for your 8 staff, 240 learners
- Migration from your current Moodle (we read your export; 47 courses, 12 quiz formats)
- 4 weeks build + 1 week parallel run + go-live

What you won't get
- Full Moodle parity (intentional — we'll list what we drop on slide 3)
- A marketplace storefront (you don't sell to the public)

€<amount>, payable 50/50 on kickoff and go-live.
```

Notes: "what you won't get" is mandatory. Numbers must be real. Money is stated, not hidden.

### Conference / talk abstract

```
The five most expensive bugs we shipped in 2025 — and how WordPress's plugin model made each one possible.

A talk for senior WordPress developers and agency leads.

35 minutes + Q&A. No slides over text. PHP examples, real commit hashes, real customer impact.
```

Notes: title is a promise, audience is named, format is concrete, "no slides over text" filters in the right audience.

## Edits to avoid

- Replacing "we shipped" with "we delivered" — "ship" is the verb, you're not UPS.
- Replacing "trade-off" with "opportunity" — fake positivity, reader knows the difference.
- Adding "in today's fast-moving landscape" — delete the entire sentence.
- Replacing "code" with "solutions" — code is code.
- Sentence-case headings in English; title-case is American agency-blog house style. Use sentence-case.
- Dutch and English mixed mid-sentence ("we deployen elke vrijdag"). Pick one.

## When the client wants different

Client copy ≠ Netdust copy. If you're writing for a client whose own brand voice is more formal or more playful, adopt theirs — and note in `tasks/` which brand voice this project follows. Don't bleed Netdust voice into a client's site without consent.

## See also

- `marketing` — SEO meta, headline structure, blog post layout
- `market-research` — for finding the audience's actual language before writing copy
- `superpowers:writing-skills` — when a written artifact needs to teach behavior (skill bodies)
- `~/.claude/plugins/netdust-wp/SOUL.md` — voice as it applies to Claude-Stefan working conversations (related but not the same)
