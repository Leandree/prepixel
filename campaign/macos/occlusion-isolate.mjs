// Isolate the occlusion effect from the DPR effect: click the button's TRUE css centre.
import { chromium } from 'playwright-core';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0];
const cdp = await ctx.newCDPSession(page);
await page.goto('file:///Users/leandre/dev/prepixel/pages/occlusion.html');
await page.waitForTimeout(200);
await page.evaluate(() => {
  window.__hit = null;
  document.getElementById('real').addEventListener('click', () => { window.__hit = 'real-button'; });
  document.getElementById('overlay').addEventListener('click', () => { window.__hit = 'overlay'; });
});
// true CSS box of the button, straight from the page
const box = await page.evaluate(() => { const r = document.getElementById('real').getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; });
const cx = box.x + box.w/2, cy = box.y + box.h/2;
const topAt = await page.evaluate(([px,py]) => { const e = document.elementFromPoint(px,py); return e ? (e.id||e.tagName) : null; }, [cx,cy]);
for (const type of ['mousePressed','mouseReleased'])
  await cdp.send('Input.dispatchMouseEvent', { type, x: cx, y: cy, button: 'left', clickCount: 1 });
await page.waitForTimeout(200);
const fired = await page.evaluate(() => window.__hit);
// what does DOMSnapshot report for the same element? (DPR check, no metrics override at all)
const snap = await cdp.send('DOMSnapshot.captureSnapshot', { computedStyles: ['opacity','visibility'] });
const dpr = await page.evaluate(() => devicePixelRatio);
console.log(JSON.stringify({ css_box: box, click_at: [cx,cy], element_on_top: topAt, handler_fired: fired, devicePixelRatio: dpr }, null, 1));
