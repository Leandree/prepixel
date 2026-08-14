// macOS Chrome CDP battery — T1..T6 against repo test pages, mirroring the Linux chromium cell.
import { chromium } from 'playwright-core';
import { distillDomSnapshot, imgTokensClaude, textTokens } from '/Users/leandre/dev/prepixel/src/capture.mjs';
import { distillHardened } from '/Users/leandre/dev/prepixel/src/distill-hardened.mjs';
import fs from 'node:fs';

const PAGES = 'file:///Users/leandre/dev/prepixel/pages';
const ART = '/Users/leandre/dev/prepixel/campaign/results/artifacts/macos';
const R = {};
const now = () => Date.now();

const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0] ?? await ctx.newPage();

async function snap(p) {
  const cdp = await ctx.newCDPSession(p);
  const t0 = now();
  const s = await cdp.send('DOMSnapshot.captureSnapshot', {
    computedStyles: ['opacity', 'visibility'], includeInputValues: true, includeDOMRects: true,
  });
  const dt = now() - t0;
  await cdp.detach();
  const view = distillDomSnapshot(s);
  return { view, ms: dt };
}

// ---------- T1: known text, char-exact ----------
await page.goto(`${PAGES}/article.html`);
const t1truth = await page.evaluate(() => document.querySelector('h1').textContent.trim());
const t1 = await snap(page);
R.t1 = { truth: t1truth, found: t1.view.includes(t1truth), ms: t1.ms };

// ---------- T2: enumerate on testapp ----------
await page.goto(`${PAGES}/testapp.html`);
const t2 = await snap(page);
fs.writeFileSync(`${ART}/chrome-cdp-testapp-distilled.txt`, t2.view);
const cdp2 = await ctx.newCDPSession(page);
const shot = await cdp2.send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync(`${ART}/chrome-cdp-testapp.png`, Buffer.from(shot.data, 'base64'));
const vp = page.viewportSize() ?? await page.evaluate(() => ({ width: innerWidth, height: innerHeight }));
const interactiveLines = t2.view.split('\n').filter(l => /^(A|BUTTON|INPUT|SELECT|TEXTAREA)/i.test(l.trim().split(' ')[0]) || /^(a|button|input|select)\b/.test(l));
R.t2 = {
  view_bytes: Buffer.byteLength(t2.view), view_tokens: textTokens(t2.view),
  screenshot_tokens: imgTokensClaude(vp.width, vp.height), ms: t2.ms,
  interactive_count: interactiveLines.length,
  sample: interactiveLines.slice(0, 12),
};

// ---------- T3: live input value ----------
await page.click('#customer');
await page.keyboard.type('T3-KJQ-77 Nouvelle Boîte SARL');
const t3 = await snap(page);
R.t3 = { visible: t3.view.includes('T3-KJQ-77'), ms: t3.ms };

// ---------- T4: living screen (feed 1 Hz), then idle ----------
await page.evaluate(() => window.startFeed(700));
const samples = [];
let prevLines = new Set((await snap(page)).view.split('\n'));
for (let i = 0; i < 5; i++) {
  await page.waitForTimeout(700);
  const s = await snap(page);
  const lines = s.view.split('\n');
  const added = lines.filter(l => !prevLines.has(l));
  samples.push({ diff_bytes: Buffer.byteLength(added.join('\n')), ms: s.ms });
  prevLines = new Set(lines);
}
await page.evaluate(() => window.stopFeed());
await page.waitForTimeout(1600); // let toast fade + last tick settle
prevLines = new Set((await snap(page)).view.split('\n'));
const idle = [];
for (let i = 0; i < 3; i++) {
  await page.waitForTimeout(700);
  const s = await snap(page);
  const added = s.view.split('\n').filter(l => !prevLines.has(l));
  idle.push(Buffer.byteLength(added.join('\n')));
  prevLines = new Set(s.view.split('\n'));
}
R.t4 = { per_tick_diff_bytes: samples.map(s => s.diff_bytes), idle_diff_bytes: idle };

// ---------- T5: blind click from channel coords only ----------
await page.goto(`${PAGES}/clicktarget.html`);
const t5v = await snap(page);
const m = t5v.view.match(/button (\d+),(\d+),(\d+),(\d+)/i) || t5v.view.match(/BUTTON (\d+),(\d+),(\d+),(\d+)/);
let t5 = { found_box: !!m };
if (m) {
  const [x, y, w, h] = m.slice(1).map(Number);
  const cdp5 = await ctx.newCDPSession(page);
  const cx = x + w / 2, cy = y + h / 2;
  for (const type of ['mousePressed', 'mouseReleased'])
    await cdp5.send('Input.dispatchMouseEvent', { type, x: cx, y: cy, button: 'left', clickCount: 1 });
  await page.waitForTimeout(300);
  const after = await snap(page);
  t5 = { found_box: true, box: [x, y, w, h], clicked_at: [cx, cy], effect: after.view.includes('CLICKED') };
}
R.t5 = t5;

// ---------- T6: canvas = declared opaque rect, croppable ----------
await page.goto(`${PAGES}/allcanvas.html`);
const t6 = await snap(page);
fs.writeFileSync(`${ART}/chrome-cdp-allcanvas-distilled.txt`, t6.view);
const canvasDecl = t6.view.split('\n').filter(l => /canvas/i.test(l));
const fabricated = /SCORE|LEVEL/.test(t6.view); // canvas pixels leaking as text would be silent fabrication
const mm = t6.view.match(/canvas (\d+),(\d+),(\d+),(\d+)/i);
let cropTokens = null;
if (mm) {
  const [x, y, w, h] = mm.slice(1).map(Number);
  const cdp6 = await ctx.newCDPSession(page);
  const crop = await cdp6.send('Page.captureScreenshot', { format: 'png', clip: { x, y, width: Math.min(w, vp.width), height: Math.min(h, vp.height), scale: 1 } });
  fs.writeFileSync(`${ART}/chrome-cdp-canvas-crop.png`, Buffer.from(crop.data, 'base64'));
  cropTokens = imgTokensClaude(Math.min(w, vp.width), Math.min(h, vp.height));
}
R.t6 = { declared: canvasDecl, fabricated_text: fabricated, crop_tokens: cropTokens, view_bytes: Buffer.byteLength(t6.view) };

// ---------- hardened distiller sanity on occlusion page ----------
await page.goto(`${PAGES}/occlusion.html`);
const hard = await distillHardened(page);
R.occlusion = { hardened_view_bytes: Buffer.byteLength(hard), mentions_occluded: /occlu|hidden|covered/i.test(hard) };
fs.writeFileSync(`${ART}/chrome-cdp-occlusion-hardened.txt`, hard);

console.log(JSON.stringify(R, null, 1));
