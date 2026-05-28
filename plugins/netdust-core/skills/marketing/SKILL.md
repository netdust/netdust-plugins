---
name: marketing
description: Use when writing or editing marketing artifacts — landing pages, blog posts, SEO meta (title, description, OG, Twitter card, schema.org), email subject lines, social copy, ad copy, or making content discoverable. Triggers on file edits in marketing/, blog/, posts/, content/, or when generating page meta, structured data, or campaign assets. Activates on keywords SEO, meta description, title tag, OG image, schema.org, keyword research, landing page, blog post, CTA, ad copy, email subject. Symptoms include drafting a new page, optimizing an existing one for search, planning content calendar, deciding what keywords to target. Calls brand-voice for tone. Stack-agnostic — applies to WordPress, Statamic, plain HTML.
---

# Marketing — SEO, structure, distribution

For voice/tone, see `brand-voice`. This skill is the layer above: structure, keywords, meta, distribution.

## Page-level checklist (landing or blog)

For every public-facing page:

| Element | Constraint |
|---|---|
| Title tag | 50-60 chars, primary keyword in first 30, brand suffix optional |
| Meta description | 140-160 chars, single sentence, contains CTA verb |
| H1 | One per page, matches title intent |
| H2 structure | Outlines the page in headings only — reader skims and gets the picture |
| Opening paragraph | Specific noun + specific verb in first 12 words. No "in today's." |
| Primary CTA | Above the fold, action verb, what happens after click is obvious |
| OG image | 1200x630, plain, readable at thumbnail size |
| OG title + description | May differ from page title — optimize for social click-through |
| Schema.org | `Article` for blog, `Product` / `Service` for landing, `Organization` site-wide |
| Internal links | At least 1 link to a related page (deeper) and 1 to a pillar page (shallower) |
| Page weight | Target <500KB total. Image-heavy pages: lazy-load below the fold. |
| Mobile breakpoint check | The hero readable at 360px wide without scrolling sideways |

## SEO meta — concrete

```html
<title>Stride LMS — for organizations that train teams</title>
<meta name="description" content="A learning platform for organizations running internal trainings. Enrollment, attendance, invoicing, reporting in one place. Used by VAD Vormingen.">

<!-- Open Graph -->
<meta property="og:type" content="website">
<meta property="og:title" content="Stride LMS — train your teams, not your marketplace">
<meta property="og:description" content="Built for organizations that run their own trainings. No marketplace bloat. 4000+ learners at VAD.">
<meta property="og:image" content="https://stridelms.be/og/stride-default.png">
<meta property="og:url" content="https://stridelms.be/">

<!-- Twitter (X) -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Stride LMS — train your teams">
<meta name="twitter:description" content="...">
<meta name="twitter:image" content="https://stridelms.be/og/stride-default.png">

<!-- Schema.org -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Stride LMS",
  "applicationCategory": "EducationalApplication",
  "operatingSystem": "Web",
  "offers": { "@type": "Offer", "priceCurrency": "EUR" }
}
</script>
```

OG title can differ from `<title>` — `<title>` optimizes for Google, OG optimizes for social click-through. They often want different angles.

## Keyword work

- **Long-tail over head terms.** "Belgian LMS for nonprofit trainers" beats "best LMS". Less traffic, much higher intent.
- **Map keywords to intent**: informational ("what is xAPI"), comparative ("LearnDash vs Stride"), transactional ("Stride pricing"). Each gets a different page type.
- **One primary keyword per page.** If a page tries to rank for 5 terms, it ranks for 0.
- **Verify the keyword has volume**: Ahrefs / Semrush free tier, or Google Search Console for what you already rank for.
- **Search the term yourself.** If page 1 is dominated by giant directories, you won't break in. Pick a less crowded variant.

## Blog post structure

```
# Title — matches the search query, doesn't tease

(Opening: 2-3 sentences, specific. Who this is for. What they'll get.)

## H2 — first concrete thing
Content. Code or screenshot. Numbers where real.

## H2 — second concrete thing

## What we won't cover
(Honest scope. Filters in the right reader.)

## What we did
Concrete outcome.

## What we'd do differently
(Mandatory section. Shows you actually shipped this, not just wrote about it.)

## See also
- [Internal pillar page]
- [Related blog post]
```

No "in conclusion" section. No bulleted summary at the bottom — if the post needed a summary, it was too long.

## Distribution

Once published:

1. **Internal links** — link the new post from at least 1 older relevant post + the related pillar page.
2. **Social** — 1 post per platform, different angle each. Don't paste the same blurb everywhere.
3. **Newsletter** — included in the next issue's "what we shipped" section.
4. **Submit to Search Console** — request indexing for the new URL.
5. **Track**: which channel actually drove signups, not just clicks. Skip the channel that drove clicks but no signups for next time.

## Anti-patterns

- Title tags that try to be witty at the expense of being searchable.
- Meta descriptions that are the first sentence of the page copy-pasted (Google often rewrites these anyway — make yours intentional).
- OG images with text smaller than 24px (unreadable as thumbnails).
- Schema.org markup for fake claims (rating widgets when you have no real ratings) — Google penalizes this.
- Keyword-stuffing the H1 ("WordPress LMS - Best WordPress LMS for WordPress - WordPress LMS Belgium").
- "Pillar page" with 8000 words and no point — readers skim and bounce.
- Publishing without an internal link target — orphan page that never gets crawled.

## See also

- `brand-voice` — tone for the actual copy
- `market-research` — finding the audience's language before writing
- `research` — investigating technical claims you make in marketing
- `wp-frontend` — when the implementation is in WordPress
- `superpowers:writing-clearly-and-concisely` (via elements-of-style plugin if installed) — sentence-level editing
