import { chromium } from 'playwright-core';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0];
await page.goto('file:///Users/leandre/dev/prepixel/pages/testapp.html');
const s1 = await ctx.newCDPSession(page);
const w1 = await s1.send('Browser.getWindowForTarget');
await s1.send('Browser.setWindowBounds', { windowId: w1.windowId, bounds: { left: 60, top: 80, width: 900, height: 700 } });
// a REAL second OS window
const t2 = await s1.send('Target.createTarget', { url: 'file:///Users/leandre/dev/prepixel/pages/clicktarget.html', newWindow: true });
await new Promise(r => setTimeout(r, 900));
const p2 = ctx.pages().find(p => p.url().includes('clicktarget'));
const s2 = await ctx.newCDPSession(p2);
const w2 = await s2.send('Browser.getWindowForTarget');
await s2.send('Browser.setWindowBounds', { windowId: w2.windowId, bounds: { left: 400, top: 300, width: 700, height: 520 } });
await new Promise(r => setTimeout(r, 800));
console.log(JSON.stringify({
  back_window: w1.windowId, front_window: w2.windowId,
  back: (await s1.send('Browser.getWindowBounds', {windowId: w1.windowId})).bounds,
  front: (await s2.send('Browser.getWindowBounds', {windowId: w2.windowId})).bounds,
}));
process.exit(0);
