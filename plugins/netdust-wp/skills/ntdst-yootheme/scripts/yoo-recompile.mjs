#!/usr/bin/env node
// yoo-recompile.mjs — click the Styler's "Recompile style" so a LESS change reaches
// css/theme.*.css without a human. YOOtheme has no server-side compiler.
//
//   WP_USER=… WP_PASS=… node yoo-recompile.mjs --url=https://site.ddev.site [--login=/wp/wp-login.php]
//                                              [--css=app/content/themes/yootheme/css] [--expect-change]
//
// Logs in, opens the YOOtheme customizer (admin-ajax.php?action=yootheme&yootheme=customizer —
// NOT customize.php), opens the Style panel, clicks "Recompile style" (any UI language),
// waits for the yootheme=theme/style POST, and prints the md5 of every css/theme.*.css
// before and after. --expect-change exits 1 when no file changed. Use a throwaway admin.
import { createRequire } from 'node:module';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';

const arg = (k, d) => (process.argv.find(a => a.startsWith(`--${k}=`)) ?? `=${d}`).split('=').slice(1).join('=');
const site = arg('url', '').replace(/\/$/, ''); if (!site) { console.error('--url is required'); process.exit(2); }
const login = arg('login', '/wp/wp-login.php'), cssDir = arg('css', 'app/content/themes/yootheme/css');
const user = process.env.WP_USER, pass = process.env.WP_PASS;
if (!user || !pass) { console.error('set WP_USER and WP_PASS (a throwaway admin)'); process.exit(2); }
const md5s = () => Object.fromEntries(readdirSync(cssDir).filter(f => /^theme\..*\.css$/.test(f)).map(f => [f, createHash('md5').update(readFileSync(join(cssDir, f))).digest('hex').slice(0, 12) + ' @' + statSync(join(cssDir, f)).mtime.toISOString().slice(11, 19)]));
const before = md5s();
const { chromium } = createRequire(process.cwd() + '/')('playwright');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, ignoreHTTPSErrors: true });
await page.goto(site + login);
await page.fill('#user_login', user); await page.fill('#user_pass', pass);
await Promise.all([page.waitForNavigation(), page.click('#wp-submit')]);
const admin = login.replace(/wp-login\.php$/, 'wp-admin/admin-ajax.php?action=yootheme&yootheme=customizer');
await page.goto(site + admin, { waitUntil: 'networkidle' });
await page.getByText(/^(Style|Stijl|Stil)$/).first().click();
const btn = page.getByText(/Recompile style|opnieuw compileren|neu kompilieren|Recompiler/i).first();
await btn.waitFor({ timeout: 15000 });
await btn.scrollIntoViewIfNeeded();
// the slash in `yootheme=theme/style` arrives URL-encoded
const saved = page.waitForResponse(r => /yootheme=theme(%2F|\/)style/.test(r.url()) && r.request().method() === 'POST', { timeout: 90000 });
await btn.click({ force: true });
const res = await saved;
console.error(`style POST → ${res.status()}`);
await page.waitForTimeout(1500);
await browser.close();
const after = md5s();
let changed = 0;
for (const f of new Set([...Object.keys(before), ...Object.keys(after)])) {
  const same = before[f] === after[f]; if (!same) changed++;
  console.log(`${same ? '=' : '≠'} ${f}  ${before[f] ?? '-'} → ${after[f] ?? '-'}`);
}
console.log(`yoo-recompile: ${changed} stylesheet(s) changed (md5 or mtime)`);
if (process.argv.includes('--expect-change') && !changed) process.exit(1);
