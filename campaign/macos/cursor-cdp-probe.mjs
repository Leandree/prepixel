import { chromium } from 'playwright-core';
import { distillDomSnapshot, imgTokensClaude, textTokens } from '/Users/leandre/dev/prepixel/src/capture.mjs';
import fs from 'node:fs';
const ART = '/Users/leandre/dev/prepixel/campaign/results/artifacts/macos';

const browser = await chromium.connectOverCDP('http://127.0.0.1:9224');
const ctx = browser.contexts()[0];
const pages = ctx.pages();
console.log(JSON.stringify({ pages: pages.map(p => p.url().slice(0, 90)) }));
const page = pages[0];

const cdp = await ctx.newCDPSession(page);
const t0 = Date.now();
const snap = await cdp.send('DOMSnapshot.captureSnapshot', { computedStyles: ['opacity','visibility'], includeInputValues: true });
const ms = Date.now() - t0;
const view = distillDomSnapshot(snap);
fs.writeFileSync(`${ART}/cursor-cdp-workbench-distilled.txt`, view);
const shot = await cdp.send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync(`${ART}/cursor-cdp-workbench.png`, Buffer.from(shot.data, 'base64'));
const vp = await page.evaluate(() => ({ w: innerWidth, h: innerHeight, dpr: devicePixelRatio }));
const lines = view.split('\n');
const interactive = lines.filter(l => /^(a|button|input|select|textarea) /.test(l));
// idle: 3 lectures espacées de 1s
let prev = new Set(lines); const idle = [];
for (let i = 0; i < 3; i++) {
  await page.waitForTimeout(1000);
  const s2 = distillDomSnapshot(await cdp.send('DOMSnapshot.captureSnapshot', { computedStyles: ['opacity','visibility'], includeInputValues: true }));
  const added = s2.split('\n').filter(l => !prev.has(l));
  idle.push(Buffer.byteLength(added.join('\n')));
  prev = new Set(s2.split('\n'));
}
console.log(JSON.stringify({
  ms, view_bytes: Buffer.byteLength(view), view_tokens: textTokens(view),
  screenshot_tokens_css: imgTokensClaude(vp.w, vp.h), dpr: vp.dpr,
  total_lines: lines.length, interactive_count: interactive.length,
  interactive_sample: interactive.slice(0, 8), text_sample: lines.filter(l => l.startsWith('text')).slice(0, 8),
  idle_diff_bytes: idle,
}, null, 1));
