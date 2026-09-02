#!/usr/bin/env node
// yoo-measure.mjs — the rendered page as numbers, to diff against the design.
//
//   node yoo-measure.mjs --url=https://site.ddev.site/page/ [--width=1440] [--selector='#tm-main > .uk-section']
//                        [--compare=figma.json] [--tolerance=2] [--out=measure.json]
//
// Prints JSON: one entry per section (rect, background, position, z-index) with its
// headings, cards (.el-item), labels and images (rect + computed font-size / line-height
// / color / border-radius). Waits for every image to DECODE before reading — a loaded
// image reports a rect long before it paints. `--compare` takes a list of
// {name, x, y, width, height} (Figma get_metadata geometry) and prints Δx Δy Δw Δh per
// node matched by text against the page, flagging anything beyond --tolerance px.
//
// Needs `playwright` resolvable from the current directory (the project's node_modules).
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';

const arg = (k, d) => (process.argv.find(a => a.startsWith(`--${k}=`)) ?? `=${d}`).split('=').slice(1).join('=');
const url = arg('url', ''); if (!url) { console.error('--url is required'); process.exit(2); }
const width = +arg('width', 1440), tol = +arg('tolerance', 2);
const selector = arg('selector', '#tm-main > .uk-section, #tm-main > * > .uk-section');
const { chromium } = createRequire(process.cwd() + '/')('playwright');

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width, height: 900 }, ignoreHTTPSErrors: true });
await page.goto(url, { waitUntil: 'networkidle' });
await page.evaluate(async () => {
  for (const s of document.querySelectorAll('section, .uk-section')) { s.scrollIntoView(); await new Promise(r => setTimeout(r, 30)); }
  window.scrollTo(0, 0);
  await Promise.all([...document.images].map(i => i.decode().catch(() => {})));
});

const data = await page.evaluate(sel => {
  const box = el => { const r = el.getBoundingClientRect(); return { x: +r.x.toFixed(1), y: +(r.y + scrollY).toFixed(1), width: +r.width.toFixed(1), height: +r.height.toFixed(1) }; };
  const cs = (el, p) => getComputedStyle(el).getPropertyValue(p);
  const text = el => (el.innerText || el.getAttribute('alt') || '').trim().replace(/\s+/g, ' ').slice(0, 60);
  return { url: location.href, width: innerWidth, sections: [...document.querySelectorAll(sel)].map((s, i) => ({
    i, cls: s.className, rect: box(s), background: cs(s, 'background-color'), position: cs(s, 'position'), zIndex: cs(s, 'z-index'),
    children: [...s.querySelectorAll('h1,h2,h3,h4,h5,h6,.el-item,.uk-label,img,.uk-button,.uk-card,.uk-tile,.uk-accordion-title')].map(el => ({
      tag: el.tagName.toLowerCase(), cls: el.className.toString().split(' ').filter(c => c.startsWith('el-') || c.startsWith('uk-')).slice(0, 4).join(' '),
      text: text(el), rect: box(el), fontSize: cs(el, 'font-size'), lineHeight: cs(el, 'line-height'), color: cs(el, 'color'),
      background: cs(el, 'background-color'), radius: cs(el, 'border-top-left-radius'),
      ...(el.tagName === 'IMG' ? { complete: el.complete, naturalWidth: el.naturalWidth } : {}),
    })),
  })) };
}, selector);
await browser.close();

const out = arg('out', '');
if (out) writeFileSync(out, JSON.stringify(data, null, 1));
else console.log(JSON.stringify(data, null, 1));

const cmp = arg('compare', '');
if (cmp) {
  const nodes = JSON.parse(readFileSync(cmp, 'utf8'));
  const list = Array.isArray(nodes) ? nodes : nodes.nodes ?? [];
  const all = data.sections.flatMap(s => s.children);
  let bad = 0;
  for (const n of list) {
    const hit = all.find(c => n.name && c.text && c.text.toLowerCase().startsWith(String(n.name).toLowerCase().slice(0, 20)));
    if (!hit) { console.error(`?     ${n.name}: no element with that text`); continue; }
    const d = { x: hit.rect.x - n.x, y: hit.rect.y - n.y, w: hit.rect.width - n.width, h: hit.rect.height - n.height };
    const off = Object.values(d).some(v => Math.abs(v) > tol);
    if (off) bad++;
    console.error(`${off ? 'DIFF ' : 'ok   '} ${n.name}: Δx ${d.x.toFixed(1)} Δy ${d.y.toFixed(1)} Δw ${d.w.toFixed(1)} Δh ${d.h.toFixed(1)}`);
  }
  console.error(`yoo-measure: ${list.length} nodes compared, ${bad} beyond ${tol}px`);
  process.exit(bad ? 1 : 0);
}
