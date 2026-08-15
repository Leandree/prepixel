import { chromium } from 'playwright-core';
import { distillDomSnapshot, imgTokensClaude } from '/Users/leandre/dev/prepixel/src/capture.mjs';
import { distillHardened } from '/Users/leandre/dev/prepixel/src/distill-hardened.mjs';
import fs from 'node:fs';
const ART='/Users/leandre/dev/prepixel/campaign/results/artifacts/macos';
const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0];
const cdp = await ctx.newCDPSession(page);
await cdp.send('Emulation.setDeviceMetricsOverride',{width:1280,height:800,deviceScaleFactor:1,mobile:false});
const out={};
for (const name of ['allcanvas','opaque']) {
  await page.goto(`file:///Users/leandre/dev/prepixel/pages/${name}.html`);
  await page.waitForTimeout(250);
  const snap = await cdp.send('DOMSnapshot.captureSnapshot',{computedStyles:['opacity','visibility']});
  const naive = distillDomSnapshot(snap);
  const hardened = await distillHardened(page);
  const png = Buffer.from((await cdp.send('Page.captureScreenshot',{format:'png'})).data,'base64');
  fs.writeFileSync(`${ART}/${name}-view.txt`, hardened);
  fs.writeFileSync(`${ART}/${name}.png`, png);
  // does the structured view fabricate any of the canvas-painted text?
  const painted = ['SCORE','LEVEL','7788'];
  out[name] = {
    naive_bytes: Buffer.byteLength(naive), naive: naive.slice(0,300),
    hardened_bytes: Buffer.byteLength(hardened), hardened: hardened.slice(0,300),
    screenshot_tokens: imgTokensClaude(1280,800), png_bytes: png.length,
    fabricated_painted_text: painted.filter(p => naive.includes(p) || hardened.includes(p)),
  };
}
await cdp.send('Emulation.clearDeviceMetricsOverride');
console.log(JSON.stringify(out,null,1));
process.exit(0);
