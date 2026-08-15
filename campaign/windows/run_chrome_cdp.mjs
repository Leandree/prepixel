// Cell: windows-chrome-cdp. Google Chrome on Windows, isolated instance,
// temp profile, CDP. Reuses the repo's hardened distiller so numbers are
// directly comparable with the Linux/macOS reference cells.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';
import { distillHardened } from '../../src/distill-hardened.mjs';
import { imageTokens } from '../../src/image-tokens.mjs';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const ART = path.join(ROOT, 'campaign', 'results', 'artifacts', 'windows');
const textTokens = s => Math.ceil(s.length / 4);
const PORT = 9231;
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PROFILE = path.join(process.env.TEMP, 'pipeline-tap-chrome-profile');
const out = { cell: 'windows-chrome-cdp' };

const proc = spawn(CHROME, [
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
  '--no-first-run', '--no-default-browser-check', '--window-size=1300,900',
  '--window-position=40,40', 'about:blank',
], { stdio: 'ignore', detached: false });

// fresh-endpoint lesson: poll /json/version until it answers
let version = null;
for (let i = 0; i < 40; i++) {
  try {
    const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
    version = await r.json(); break;
  } catch { await new Promise(r => setTimeout(r, 500)); }
}
if (!version) { console.log(JSON.stringify({ error: 'CDP endpoint never answered' })); process.exit(1); }
out.stack_signature = `http://127.0.0.1:${PORT}/json/version -> ${version.Browser}, Protocol ${version['Protocol-Version']}`;

const browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`);
const ctx = browser.contexts()[0];
const page = ctx.pages()[0] ?? await ctx.newPage();
await page.setViewportSize({ width: 1280, height: 800 });
const pageUrl = f => 'file:///' + path.join(ROOT, 'pages', f).replace(/\\/g, '/');

await page.goto(pageUrl('testapp.html'));
await page.waitForTimeout(400);
out.dpr = await page.evaluate(() => devicePixelRatio);

// --- baseline view + measurements -------------------------------------------
let t0 = performance.now();
let view = await distillHardened(page);
out.capture_latency_ms = +(performance.now() - t0).toFixed(1);
out.view_bytes = Buffer.byteLength(view);
out.view_tokens = textTokens(view);
fs.writeFileSync(path.join(ART, 'chrome-cdp-view-testapp.txt'), view);
const png = await page.screenshot();
fs.writeFileSync(path.join(ART, 'chrome-cdp-shot-testapp.png'), png);
out.screenshot_tokens = imageTokens(1280, 800);
out.screenshot_bytes = png.length;

// --- T1: known text ----------------------------------------------------------
out.t1 = {
  pass: ['Dupont SARL', '€2,105.90', '3 open orders'].every(s => view.includes(s)),
};

// --- T2: enumerate vs mechanical ground truth --------------------------------
const inter = view.split('\n').filter(l => /^(a|button|input|select|textarea|summary|label) /.test(l));
out.t2 = { interactive_lines: inter.length, expected: 10, pass: inter.length === 10 };

// --- T3: live value ----------------------------------------------------------
await page.click('#customer');
await page.keyboard.type('CDP-LIVE-77x');
await page.waitForTimeout(200);
const view3 = await distillHardened(page);
const valLine = view3.split('\n').find(l => l.includes('CDP-LIVE-77x'));
const d3 = diffBytes(view, view3);
out.t3 = { pass: !!valLine, value_line: valLine, diff_bytes: d3 };

// --- T5: blind click the #1043 Ship button from the view alone ---------------
// find the table row's text line for #1043, then the nearest button line on
// the same row (y overlap) — pure arithmetic on published lines.
const lines = view3.split('\n');
const row = lines.find(l => l.startsWith('text') && l.includes('#1043'));
const rowY = row ? parseInt(row.split(' ')[1].split(',')[1]) : null;
const btn = lines.filter(l => l.startsWith('button'))
  .map(l => ({ l, box: l.split(' ')[1].split(',').map(Number) }))
  .find(b => Math.abs(b.box[1] - rowY) < 20);
let t5 = { pass: false, row_line: row, button_line: btn?.l };
if (btn) {
  const [x, y, w, h] = btn.box;
  const cdp = await ctx.newCDPSession(page);
  const cx = x + w / 2, cy = y + h / 2;
  for (const type of ['mousePressed', 'mouseReleased'])
    await cdp.send('Input.dispatchMouseEvent', { type, x: cx, y: cy, button: 'left', clickCount: 1 });
  await page.waitForTimeout(400);
  const after = await distillHardened(page);
  t5.badge_shipped = after.includes('Shipped');
  t5.toast_seen = after.includes('marked as shipped');
  t5.pass = t5.badge_shipped && t5.toast_seen;
  t5.diff_bytes = diffBytes(view3, after);
  fs.writeFileSync(path.join(ART, 'chrome-cdp-view-after-ship.txt'), after);
}
out.t5 = t5;

// --- T4: living screen (feed at 1 Hz), then idle -----------------------------
await page.evaluate(() => window.startFeed(1000));
let prev = await distillHardened(page);
const ticks = [];
for (let i = 0; i < 5; i++) {
  await page.waitForTimeout(1000);
  const cur = await distillHardened(page);
  ticks.push(diffBytes(prev, cur));
  prev = cur;
}
await page.evaluate(() => window.stopFeed());
await page.waitForTimeout(300);
const i1 = await distillHardened(page);
await page.waitForTimeout(1000);
const i2 = await distillHardened(page);
out.t4 = { tick_diff_bytes: ticks, idle_diff_bytes: diffBytes(i1, i2),
           rescreenshot_tokens_per_tick: out.screenshot_tokens };

// --- T6: pictorial + occlusion honesty --------------------------------------
await page.goto(pageUrl('allcanvas.html'));
await page.waitForTimeout(300);
const cv = await distillHardened(page);
out.t6_allcanvas_view = cv;
await page.goto(pageUrl('occlusion.html'));
await page.waitForTimeout(300);
const ov = await distillHardened(page);
out.t6_occlusion = {
  occluded_tags: ov.split('\n').filter(l => l.includes('[occluded]')).length,
  pixels_lines: ov.split('\n').filter(l => l.startsWith('[pixels]')).length,
};
fs.writeFileSync(path.join(ART, 'chrome-cdp-view-occlusion.txt'), ov);

// --- hard text: mechanical self-check against the page's own textContent ----
await page.goto(pageUrl('hardtext.html'));
await page.waitForTimeout(300);
const hv = await distillHardened(page);
fs.writeFileSync(path.join(ART, 'chrome-cdp-view-hardtext.txt'), hv);
const groundLines = await page.evaluate(() =>
  [...document.querySelectorAll('body *')].map(e => e.childNodes.length && [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim()).join('')).filter(Boolean));
const missing = groundLines.filter(t => t && t.length > 1 && !hv.includes(t));
out.hardtext = { ground_lines: groundLines.length, missing: missing.slice(0, 5), missing_count: missing.length };

function diffBytes(a, b) {
  const A = a.split('\n'), B = b.split('\n');
  const sa = new Set(A), sb = new Set(B);
  let n = 0;
  for (const l of B) if (!sa.has(l)) n += Buffer.byteLength(l) + 1;
  for (const l of A) if (!sb.has(l)) n += 2; // removal marker cost
  return n;
}

await browser.close();
proc.kill();
console.log(JSON.stringify(out, null, 1));
