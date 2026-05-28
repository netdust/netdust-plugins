<overview>
Statamic 6 + Peak sweep playbook. Loaded by `shake-out-statamic` in Phase 1.

Read the project's `CLAUDE.md` first for site URL, MCP availability, and the design tokens / partials the build is expected to use.

Statamic renders content through:
1. Antlers/Blade templates → 2. Stache (file-backed cache) → 3. Static cache (production)

Most "the page is wrong" bugs are stache-staleness or blueprint mismatches — keep that lens on while sweeping.
</overview>

<tool_tiers>
**Use the fastest tool that can answer the question.**

| curl / `please` / `artisan` (fast) | chrome-devtools (slower, essential) |
|------------------------------------|-------------------------------------|
| Does the page return 200? | Does the **interaction** work? |
| Is expected text in the response body? | Does Alpine `x-intersect` actually animate? |
| Does the route exist? | Does the form submit and show success? |
| Does the blueprint validate? | Does the CP load without JS errors? |
| Does Glide return 200 for the hero image? | Does the page builder edit experience work? |
| **"Is it there?"** | **"Does it work?"** |

**Rule of thumb:** Statamic server-renders most of this site, so curl + grep covers a lot. Reach for the browser when JS, Alpine, scroll-reveal, the CP, or page-builder editing is involved.
</tool_tiers>

<prerequisites>
```bash
# DDEV up?
ddev status

# Resolve site URL — auto-detected from DDEV. STOP if this fails and fix DDEV first;
# do not fall back to a hardcoded URL (silent wrong-target sweeps are the worst kind).
SITE_URL=$(ddev describe -j 2>/dev/null | jq -r '.raw.primary_url' 2>/dev/null)
[ -z "$SITE_URL" ] && { echo "FATAL: could not resolve DDEV site URL. Run 'ddev start' and retry."; exit 1; }

# Quick reachability
curl -sI "$SITE_URL" | head -3

# Stache fresh?
ddev exec php please stache:warm

# Are there migrations or queued jobs we forgot?
ddev exec php artisan migrate:status 2>&1 | tail -5
ddev exec php artisan queue:failed 2>&1 | tail -5
```

If DDEV is down: `ddev start`. If the site URL doesn't resolve, check `.ddev/config.yaml`.
</prerequisites>

<sweep_checklist>

<existing_tests>
**0. Run existing test suites FIRST**

```bash
# Feature + unit tests
ddev exec php artisan test --compact 2>&1

# Filter to what was just built (faster signal during shake-out)
ddev exec php artisan test --compact --filter=[FeatureName] 2>&1

# Pint formatting (often reveals copy-paste issues in PHP)
ddev exec vendor/bin/pint --test --format agent 2>&1 | tail -10
```

Log every test failure as a sweep finding. Skip checks below that are already covered by passing tests — focus exploratory effort on what tests don't reach (Glide, stache, CP, page builder rendering).

If no tests exist, that itself is a finding (MINOR) — note it and continue.
</existing_tests>

<smoke_test>
**1. Smoke — Is it alive?**

```bash
SITE_URL=$(ddev describe -j 2>/dev/null | jq -r '.raw.primary_url')

# Homepage 200
curl -s -o /dev/null -w '%{http_code}\n' "$SITE_URL/"

# CP responds (login redirect or form is fine)
curl -s -o /dev/null -w '%{http_code}\n' "$SITE_URL/cp"

# REST entries endpoint (if API enabled)
curl -s -o /dev/null -w '%{http_code}\n' "$SITE_URL/api/collections"

# Laravel log — recent errors
ddev exec tail -100 storage/logs/laravel.log 2>/dev/null | grep -iE "ERROR|Exception|Fatal" | tail -10

# Statamic config sanity
ddev exec php please support:details 2>&1 | head -20

# Stache warm without errors
ddev exec php please stache:warm 2>&1 | tail -5
```

Expected: all 200/302 (CP redirects), no recent fatals, stache warm completes cleanly.
</smoke_test>

<routes_and_pages>
**2. Routes & Pages — Every URL the plan added**

Read the plan, list every public route. For each:

```bash
# Status code
for path in "/" "/features" "/pricing" "/contact" "/blog" "/lms-voor-vzw" "/privacy"; do
  STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$SITE_URL$path")
  echo "$path: $STATUS"
done
# Expected: 200 for every known route. 404 = missing entry or route map issue.

# Each blog post resolvable
ddev exec php please entry:list blog --format=json 2>/dev/null | jq -r '.[].url' | while read url; do
  curl -s -o /dev/null -w "%{http_code} $url\n" "$SITE_URL$url"
done

# Page renders expected content (not just a 200 with empty body).
# Adapt the search term + the blog item selector to this project's actual markup —
# inspect the rendered HTML once and lock in selectors that will be stable across edits.
curl -s "$SITE_URL/" | grep -c "[brand-keyword]"   # expect > 0
curl -s "$SITE_URL/blog" | grep -cE '<article|class="[^"]*post[^"]*"|class="[^"]*card[^"]*"'  # expect 1+

# Raw Antlers tags leaking through (stache or template bug)
curl -s "$SITE_URL/" | grep -c '{{'   # expect 0
curl -s "$SITE_URL/" | grep -c '@yield'  # expect 0

# 404 page renders gracefully
curl -s -o /dev/null -w '%{http_code}\n' "$SITE_URL/this-does-not-exist"
# Expected: 404 with a styled page, not a Laravel debug screen
```
</routes_and_pages>

<content_layer>
**3. Content Layer — Collections, blueprints, globals, taxonomies**

Use the Statamic MCP routers — they're the fastest way to see canonical state.

```
mcp: statamic-structures action=list type=collections
mcp: statamic-structures action=list type=taxonomies
mcp: statamic-structures action=list type=navigations
mcp: statamic-structures action=list type=sites

mcp: statamic-blueprints action=list
mcp: statamic-blueprints action=get handle=page
mcp: statamic-blueprints action=get handle=article

mcp: statamic-globals action=list
mcp: statamic-globals action=get handle=site_settings

# Entry counts per collection (catches "we forgot to migrate content")
mcp: statamic-entries action=list collection=pages
mcp: statamic-entries action=list collection=blog
```

Cross-check against filesystem:

```bash
# Blueprint YAML parses — catches indentation/duplicate-handle bugs
for f in resources/blueprints/**/*.yaml; do
  ddev exec php -r "yaml_parse_file('$f') or exit('FAIL: $f');" 2>&1
done

# Content frontmatter parses
ls content/collections/pages/*.md | while read f; do
  head -1 "$f" | grep -q '^---' || echo "BAD FRONTMATTER: $f"
done

# Required fields populated (example: pages must have title)
ddev exec php please entry:list pages --format=json 2>/dev/null | jq '.[] | select(.title == null or .title == "")'
# Expected: empty
```

**Common findings here:**
- Blueprint references a fieldset that no longer exists
- Field handle in template (`{{ subheading }}`) doesn't match blueprint (`sub_heading`)
- Globals referenced in templates but missing from globals folder
</content_layer>

<page_builder>
**4. Page Builder — Each block partial renders**

If the project uses Peak page builder (replicator on `pages.page_builder`):

```bash
# Every block partial that the blueprint references actually exists
ddev exec php please entry:list pages --format=json 2>/dev/null \
  | jq -r '.[].page_builder[]?.type' | sort -u | while read block; do
    test -f "resources/views/page_builder/_$block.antlers.html" \
      && echo "OK $block" \
      || echo "MISSING resources/views/page_builder/_$block.antlers.html"
  done

# No raw block-type debug output leaking ("array (...)" or "Object (...)")
curl -s "$SITE_URL/" | grep -cE "Array\(|Object\(|<pre>"
# Expected: 0 (unless your design legitimately uses a <pre>)

# Hero block content actually present on the homepage
curl -s "$SITE_URL/" | grep -c "hero"  # adapt to your block class names
```

For each block type the plan added, render a page that uses it and grep for its hallmark CSS class or copy.
</page_builder>

<assets_and_glide>
**5. Assets & Glide**

```bash
# Asset containers respond
mcp: statamic-assets action=list-containers

# A known image resolves through Glide
curl -s -o /dev/null -w '%{http_code}\n' "$SITE_URL/img/asset/[container]::[path]?w=800&fm=webp"
# Expected: 200

# Broken images on the homepage
curl -s "$SITE_URL/" | grep -oP 'src="[^"]+"' | grep -E "\.(jpe?g|png|webp|avif|svg)" | head -5 | while read line; do
  url=$(echo "$line" | sed -E 's/src="([^"]+)"/\1/')
  [[ "$url" == /* ]] && url="$SITE_URL$url"
  STATUS=$(curl -s -o /dev/null -w '%{http_code}' "$url")
  echo "$STATUS  $url"
done
# Expected: every status 200

# Glide cache writable
ddev exec test -w storage/statamic/glide && echo "WRITABLE" || echo "NOT WRITABLE"

# Picture partial output (responsive srcset present).
# Only assert this on a route the design uses the responsive `picture` partial on —
# a hero image inside a `<picture>` will emit `srcset`, a Glide background-image won't.
# Pick a known image-heavy page and check it specifically:
curl -s "$SITE_URL/[image-heavy-page]" | grep -c 'srcset='
# Expected: > 0 on that page if the design uses responsive images. If the homepage relies on
# Glide-rendered backgrounds instead, sweep there is misleading — skip or move the check.
```
</assets_and_glide>

<forms>
**6. Statamic Forms (if any)**

For each form the plan added:

```bash
# Form blueprint exists
ls resources/forms/*.yaml

# Submission endpoint accepts a valid post
curl -s -X POST "$SITE_URL/!/forms/[handle]" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "name=Test&email=test@example.com&_token=$(curl -s "$SITE_URL/" | grep -oP 'name="_token" value="\K[^"]+' | head -1)" \
  -o /dev/null -w '%{http_code}\n'

# Submissions persisted
ddev exec ls storage/forms/[handle]/ 2>/dev/null | tail -5

# Failed validation returns to form, not a 500
curl -s -X POST "$SITE_URL/!/forms/[handle]" -o /dev/null -w '%{http_code}\n'
# Expected: 302 back to form, NOT 500
```
</forms>

<cp_check>
**7. Control Panel — Use chrome-devtools**

The CP is JS-heavy; curl can't really verify it. Pattern:

```
mcp__chrome-devtools__new_page  url: SITE_URL/cp
mcp__chrome-devtools__fill  selector: "input[name='email']"     value: "[admin email from users/]"
mcp__chrome-devtools__fill  selector: "input[name='password']"  value: "[from CLAUDE.md or .env.local]"
mcp__chrome-devtools__click  selector: "button[type='submit']"
mcp__chrome-devtools__wait_for  selector: ".dashboard"
mcp__chrome-devtools__list_console_messages  level: "error"

# Open a page entry — does the page builder render?
mcp__chrome-devtools__navigate_page  url: SITE_URL/cp/collections/pages/entries
mcp__chrome-devtools__click  selector: "a[href*='/cp/collections/pages/entries/']"  # first entry
mcp__chrome-devtools__wait_for  selector: "[data-replicator-set]"
mcp__chrome-devtools__list_console_messages  level: "error"

# Save without changes — does it persist cleanly?
mcp__chrome-devtools__click  selector: "button[type='submit']"
mcp__chrome-devtools__wait_for  selector: ".publish-form"
mcp__chrome-devtools__list_console_messages  level: "error"
```

**Console errors here are almost always real bugs** (missing addon JS, fieldtype mismatch, blueprint pointing at a removed fieldtype).
</cp_check>

<browser_checks>
**8. Front-end Behaviour — chrome-devtools**

Read the plan, find every interactive feature, apply the matching pattern.

<pattern name="alpine-and-scroll-reveal">
**When:** The design uses Alpine `x-intersect` or `.reveal` scroll animations.

```
mcp__chrome-devtools__new_page  url: SITE_URL/
mcp__chrome-devtools__list_console_messages  level: "error"   # Alpine errors show here
mcp__chrome-devtools__evaluate_script  expression: "document.querySelectorAll('[x-intersect]').length"
# Scroll and check that an off-screen element gains the visible class
mcp__chrome-devtools__evaluate_script  expression: "window.scrollTo(0, 1500)"
mcp__chrome-devtools__evaluate_script  expression: "document.querySelector('.reveal.is-visible') ? 'OK' : 'NO REVEAL'"
```
</pattern>

<pattern name="form-submission">
**When:** Public contact / lead form.

```
mcp__chrome-devtools__navigate_page  url: SITE_URL/contact
mcp__chrome-devtools__fill  selector: "input[name='name']"     value: "Shake Out"
mcp__chrome-devtools__fill  selector: "input[name='email']"    value: "shake@out.test"
mcp__chrome-devtools__fill  selector: "textarea[name='message']" value: "Test"
mcp__chrome-devtools__click  selector: "button[type='submit']"
mcp__chrome-devtools__wait_for  selector: ".form-success, .success"
mcp__chrome-devtools__list_console_messages  level: "error"
```

Then verify storage:
```bash
ddev exec ls -lt storage/forms/contact/ | head -3
```
</pattern>

<pattern name="navigation">
**When:** Header/footer nav was rebuilt.

```
mcp__chrome-devtools__navigate_page  url: SITE_URL/
mcp__chrome-devtools__evaluate_script  expression: "Array.from(document.querySelectorAll('header a')).map(a => a.href)"
# Click each top-level link and confirm 200
```
</pattern>

<pattern name="screenshot-batch">
**When:** Always — at the end of browser checks, screenshot key pages for human review.

```
for url in / /features /pricing /blog /contact; do
  mcp__chrome-devtools__navigate_page  url: SITE_URL + url
  mcp__chrome-devtools__take_screenshot
done
```
</pattern>

</browser_checks>

<deploy_checks>
**9. Deployment Sanity (if shake-out targets a deployed environment)**

Only run these if the build was deployed. Use SSH patterns from `CLAUDE.md`.

```bash
# Stache warm on the server
ssh ploi-staging "cd [path] && php please stache:warm 2>&1 | tail -5"

# Production has static caching enabled
ssh ploi-staging "cd [path] && grep STATAMIC_STATIC_CACHING .env"

# Recent server log
ssh ploi-staging "tail -50 [path]/storage/logs/laravel.log"

# Search index built
ssh ploi-staging "cd [path] && php please search:status 2>&1"
```
</deploy_checks>

</sweep_checklist>

<manual_checklist_guidance>

After automated sweep, generate manual checks ONLY for:

1. Visual layout per design (Tailwind tokens applied correctly, Satoshi/DM Sans loaded)
2. Responsive breakpoints (mobile/tablet — chrome-devtools can do some of this; flag anything that needs human eyes)
3. Scroll-reveal cadence — does it *feel* right?
4. Dutch copy reading naturally (typos, untranslated strings, hardcoded English)
5. Grain texture / brand atmosphere
6. CP editorial UX — would a non-technical editor be able to build a page?

Be specific — not "check the homepage" but "verify the hero gradient + grain overlay matches /mnt/c/Users/.../site/index.html on mobile (375px)."
Keep to 5–10 items.

</manual_checklist_guidance>
