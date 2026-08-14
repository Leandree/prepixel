// T5 retry with devicePixelRatio correction + native-window cross-check setup.
import { chromium } from 'playwright-core';
import { distillDomSnapshot } from '/Users/leandre/dev/prepixel/src/capture.mjs';

const PAGES = 'file:///Users/leandre/dev/prepixel/pages';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0];

async function snap(p) {
  const cdp = await ctx.newCDPSession(p);
  const s = await cdp.send('DOMSnapshot.captureSnapshot', { computedStyles: ['opacity', 'visibility'], includeInputValues: true });
  await cdp.detach();
  return distillDomSnapshot(s);
}

await page.goto(`${PAGES}/clicktarget.html`);
const dpr = await page.evaluate(() => devicePixelRatio);
const view = await snap(page);
const m = view.match(/button (\d+),(\d+),(\d+),(\d+)/i);
const [x, y, w, h] = m.slice(1).map(Number);
const cx = (x + w / 2) / dpr, cy = (y + h / 2) / dpr;
const cdp5 = await ctx.newCDPSession(page);
for (const type of ['mousePressed', 'mouseReleased'])
  await cdp5.send('Input.dispatchMouseEvent', { type, x: cx, y: cy, button: 'left', clickCount: 1 });
await page.waitForTimeout(300);
const after = await snap(page);
console.log(JSON.stringify({ dpr, device_box: [x, y, w, h], css_click: [cx, cy], effect: after.includes('CLICKED') }));

// leave testapp on screen for the native AX probe + winshot
await page.goto(`${PAGES}/testapp.html`);
await page.waitForTimeout(500);
