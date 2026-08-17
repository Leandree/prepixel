// LINUX CONFIRMATION RUN of campaign/macos/web-battery.mjs — identical sites & method,
// only paths changed; Chrome 148 (playwright cache) headed under Xvfb, CDP :9223.
// Real-web battery: can an agent browse the actual internet from structure,
// and what does it cost vs screenshots?
//
// Per site we measure BOTH scopes, because they answer different questions:
//   - hardened view  : viewport-scoped, hit-tested  -> apples-to-apples vs ONE screenshot
//   - naive view     : whole document               -> the "no scrolling needed" advantage
// and we count how many screenshots pixels would need to cover the same document.
import { chromium } from 'playwright-core';
import { distillDomSnapshot, imgTokensClaude, textTokens } from '/home/leandre/prepixel/src/capture.mjs';
import { distillHardened } from '/home/leandre/prepixel/src/distill-hardened.mjs';
import { imageTokens } from '/home/leandre/prepixel/src/image-tokens.mjs';
import fs from 'node:fs';

const OUT = '/home/leandre/prepixel/results/web-battery-linux';
fs.mkdirSync(`${OUT}/views`, { recursive: true });
fs.mkdirSync(`${OUT}/shots`, { recursive: true });

const VW = 1280, VH = 800;
const SITES = [
  { id: 'wikipedia',    cat: 'reference',      url: 'https://en.wikipedia.org/wiki/Graphics_pipeline' },
  { id: 'mdn',          cat: 'reference',      url: 'https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API' },
  { id: 'hackernews',   cat: 'webapp',         url: 'https://news.ycombinator.com/' },
  { id: 'github',       cat: 'webapp',         url: 'https://github.com/torvalds/linux' },
  { id: 'duckduckgo',   cat: 'webapp',         url: 'https://duckduckgo.com/?q=graphics+pipeline' },
  { id: 'openstreetmap',cat: 'webapp-canvas',  url: 'https://www.openstreetmap.org/#map=13/48.8566/2.3522' },
  { id: 'excalidraw',   cat: 'webapp-canvas',  url: 'https://excalidraw.com/' },
  { id: 'apple',        cat: 'vitrine',        url: 'https://www.apple.com/' },
  { id: 'stripe',       cat: 'vitrine',        url: 'https://stripe.com/' },
  { id: 'vercel',       cat: 'vitrine',        url: 'https://vercel.com/' },
  { id: 'youtube-home', cat: 'media',          url: 'https://www.youtube.com/' },
  { id: 'youtube-watch',cat: 'media',          url: 'https://www.youtube.com/watch?v=jNQXAC9IVRw' },
  { id: 'bbc-news',     cat: 'presse',         url: 'https://www.bbc.com/news' },
  { id: 'lemonde',      cat: 'presse',         url: 'https://www.lemonde.fr/' },
  { id: 'amazon-fr',    cat: 'commerce',       url: 'https://www.amazon.fr/s?k=clavier+mecanique' },
  { id: 'leboncoin',    cat: 'commerce',       url: 'https://www.leboncoin.fr/' },
];

const CONSENT = /cookie|consent|accepter|accept all|tout accepter|privacy|rgpd|gdpr/i;

const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0] ?? await ctx.newPage();
const cdp = await ctx.newCDPSession(page);
await cdp.send('Emulation.setDeviceMetricsOverride', { width: VW, height: VH, deviceScaleFactor: 1, mobile: false });

const rows = [];
for (const site of SITES) {
  const row = { ...site };
  try {
    const t0 = Date.now();
    await page.goto(site.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3500);            // let JS/lazy content settle
    row.nav_ms = Date.now() - t0;
    row.final_url = page.url();
    row.title = await page.title();

    const tv = Date.now();
    const hardened = await distillHardened(page);
    row.view_ms = Date.now() - tv;

    const ts = Date.now();
    const snap = await cdp.send('DOMSnapshot.captureSnapshot', { computedStyles: ['opacity','visibility'], includeInputValues: true });
    const naive = distillDomSnapshot(snap);
    row.naive_ms = Date.now() - ts;

    const png = Buffer.from((await cdp.send('Page.captureScreenshot', { format: 'png' })).data, 'base64');
    fs.writeFileSync(`${OUT}/shots/${site.id}.png`, png);
    fs.writeFileSync(`${OUT}/views/${site.id}.hardened.txt`, hardened);
    fs.writeFileSync(`${OUT}/views/${site.id}.naive.txt`, naive);

    const doc = await page.evaluate(() => ({
      scrollH: document.documentElement.scrollHeight,
      nText: document.body ? document.body.innerText.length : 0,
      nCanvas: document.querySelectorAll('canvas').length,
      nVideo: document.querySelectorAll('video').length,
      nImg: document.querySelectorAll('img').length,
      nIframe: document.querySelectorAll('iframe').length,
    }));
    const screensToCover = Math.max(1, Math.ceil(doc.scrollH / VH));

    row.structured = {
      hardened_bytes: Buffer.byteLength(hardened), hardened_tokens: textTokens(hardened),
      hardened_lines: hardened ? hardened.split('\n').length : 0,
      naive_bytes: Buffer.byteLength(naive), naive_tokens: textTokens(naive),
      opaque_declared: (hardened.match(/^\[pixels\]/gm) || []).length,
      occluded_tagged: (hardened.match(/\[occluded\]/g) || []).length,
    };
    row.pixels = {
      png_bytes: png.length,
      viewport_tokens: imgTokensClaude(VW, VH),
      viewport_tokens_retina: imageTokens(VW*2, VH*2),
      viewport_tokens_retina_legacy: imageTokens(VW*2, VH*2, 'legacy'),
      screens_to_cover_page: screensToCover,
      fullpage_tokens: imgTokensClaude(VW, VH) * screensToCover,
    };
    row.page = doc;
    row.consent_banner = CONSENT.test(hardened.slice(0, 4000));
    row.ratio_viewport = +(row.pixels.viewport_tokens / Math.max(1, row.structured.hardened_tokens)).toFixed(2);
    row.ratio_fullpage = +(row.pixels.fullpage_tokens / Math.max(1, row.structured.naive_tokens)).toFixed(2);
    row.ok = true;
    console.error(`ok   ${site.id.padEnd(14)} view=${row.structured.hardened_tokens}tok naive=${row.structured.naive_tokens}tok shot=${row.pixels.viewport_tokens}tok x${row.ratio_viewport} screens=${screensToCover}`);
  } catch (e) {
    row.ok = false; row.error = String(e).split('\n')[0].slice(0, 200);
    console.error(`FAIL ${site.id.padEnd(14)} ${row.error}`);
  }
  rows.push(row);
}
await cdp.send('Emulation.clearDeviceMetricsOverride');
fs.writeFileSync(`${OUT}/web-battery.json`, JSON.stringify(rows, null, 2));

const ok = rows.filter(r => r.ok);
const sum = f => ok.reduce((a, r) => a + f(r), 0);
const summary = {
  n_sites: rows.length, n_ok: ok.length,
  avg_hardened_tokens: Math.round(sum(r => r.structured.hardened_tokens) / ok.length),
  avg_naive_tokens: Math.round(sum(r => r.structured.naive_tokens) / ok.length),
  viewport_shot_tokens: imgTokensClaude(VW, VH),
  avg_ratio_viewport: +(sum(r => r.ratio_viewport) / ok.length).toFixed(2),
  avg_screens_to_cover: +(sum(r => r.pixels.screens_to_cover_page) / ok.length).toFixed(1),
  avg_ratio_fullpage: +(sum(r => r.ratio_fullpage) / ok.length).toFixed(2),
  sites_with_consent_banner: ok.filter(r => r.consent_banner).map(r => r.id),
  sites_with_canvas_or_video: ok.filter(r => r.page.nCanvas || r.page.nVideo).map(r => r.id),
};
fs.writeFileSync(`${OUT}/web-battery-summary.json`, JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 1));
process.exit(0);
