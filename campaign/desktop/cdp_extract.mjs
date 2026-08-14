// Connect to an ALREADY-RUNNING Chromium via CDP and return the distilled DOM
// view of the target whose title matches argv[2]. Proves the router can, after
// picking the channel for the focused window, actually extract its content.
import { chromium } from 'playwright-core';
import { distillDomSnapshot } from '../../src/capture.mjs';

const titleNeedle = process.argv[2] || '';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9222');
let out = { matched: null, view: '', tokens: 0 };
for (const ctx of browser.contexts()) {
  for (const page of ctx.pages()) {
    const t = await page.title();
    if (!titleNeedle || t.includes(titleNeedle)) {
      const cdp = await ctx.newCDPSession(page);
      const snap = await cdp.send('DOMSnapshot.captureSnapshot', { computedStyles: ['opacity', 'visibility'], includeDOMRects: true });
      const view = distillDomSnapshot(snap);
      out = { matched: t, view, tokens: Math.ceil(view.length / 4) };
      break;
    }
  }
}
console.log(JSON.stringify(out, null, 2));
await browser.close();
