// macOS silent-divergence hunt — the adversarial safety stress test.
// Part 1 (in-window, CDP): naive distilled view vs hardened distiller on occlusion.html.
// Part 2 (in-window, ground truth): does a blind click at the naive coords actually
//   reach the intended button? Verified by the page's own state, not by a screenshot.
import { chromium } from 'playwright-core';
import { distillDomSnapshot } from '/Users/leandre/dev/prepixel/src/capture.mjs';
import { distillHardened } from '/Users/leandre/dev/prepixel/src/distill-hardened.mjs';
import fs from 'node:fs';

const ART = '/Users/leandre/dev/prepixel/campaign/results/artifacts/macos';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0];
const cdp = await ctx.newCDPSession(page);
await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });

await page.goto('file:///Users/leandre/dev/prepixel/pages/occlusion.html');
await page.waitForTimeout(200);
// instrument the button so we can detect whether a click truly reached it
await page.evaluate(() => {
  window.__hit = null;
  document.getElementById('real').addEventListener('click', () => { window.__hit = 'real-button'; });
  document.getElementById('overlay').addEventListener('click', () => { window.__hit = 'overlay'; });
});

const snap = await cdp.send('DOMSnapshot.captureSnapshot', { computedStyles: ['opacity','visibility'], includeInputValues: true });
const naive = distillDomSnapshot(snap);
const hardened = await distillHardened(page);
fs.writeFileSync(`${ART}/occlusion-naive.txt`, naive);
fs.writeFileSync(`${ART}/occlusion-hardened.txt`, hardened);

const SECRETS = ['INVISIBLE-OPACITY-SECRET', 'HIDDEN-SECRET', 'OFFSCREEN-SECRET'];
const leak = v => Object.fromEntries(SECRETS.map(s => [s, v.includes(s)]));

// naive coords for the button
const m = naive.match(/button (\d+),(\d+),(\d+),(\d+)/i);
const [x,y,w,h] = m.slice(1).map(Number);
const cx = x + w/2, cy = y + h/2;
// who is actually on top at that point? (page's own hit test = ground truth)
const topAt = await page.evaluate(([px,py]) => {
  const el = document.elementFromPoint(px,py);
  return el ? (el.id || el.tagName) : null;
}, [cx, cy]);
// dispatch a real click there and see which handler fires
for (const type of ['mousePressed','mouseReleased'])
  await cdp.send('Input.dispatchMouseEvent', { type, x: cx, y: cy, button: 'left', clickCount: 1 });
await page.waitForTimeout(200);
const whoGotIt = await page.evaluate(() => window.__hit);

const out = {
  naive: {
    bytes: Buffer.byteLength(naive),
    lists_button: /button/i.test(naive),
    button_box: [x,y,w,h],
    secrets_leaked: leak(naive),
  },
  hardened: {
    bytes: Buffer.byteLength(hardened),
    marks_occluded: /occluded/i.test(hardened),
    secrets_leaked: leak(hardened),
    text: hardened,
  },
  ground_truth: { element_on_top_at_naive_click_point: topAt, handler_that_fired: whoGotIt },
};
console.log(JSON.stringify(out, null, 1));
await cdp.send('Emulation.clearDeviceMetricsOverride');
