// Cell: windows-web-battery-cdp. The 16-site real-web battery, Windows Chrome,
// exact replication of the macOS protocol (same URLs, same hardened distiller,
// same metrics). Isolated instance, temp profile, logged out.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';
import { distillHardened } from '../../src/distill-hardened.mjs';
import { imageTokens } from '../../src/image-tokens.mjs';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const OUT = path.join(ROOT, 'results', 'web-battery-windows');
fs.mkdirSync(path.join(OUT, 'views'), { recursive: true });
fs.mkdirSync(path.join(OUT, 'shots'), { recursive: true });
const textTokens = s => Math.ceil(s.length / 4);

const SITES = [
  ['wikipedia', 'reference', 'https://en.wikipedia.org/wiki/Graphics_pipeline'],
  ['mdn', 'reference', 'https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API'],
  ['hackernews', 'webapp', 'https://news.ycombinator.com/'],
  ['github', 'webapp', 'https://github.com/torvalds/linux'],
  ['duckduckgo', 'webapp', 'https://duckduckgo.com/?q=graphics+pipeline'],
  ['openstreetmap', 'webapp-canvas', 'https://www.openstreetmap.org/#map=13/48.8566/2.3522'],
  ['excalidraw', 'webapp-canvas', 'https://excalidraw.com/'],
  ['apple', 'vitrine', 'https://www.apple.com/'],
  ['stripe', 'vitrine', 'https://stripe.com/'],
  ['vercel', 'vitrine', 'https://vercel.com/'],
  ['youtube-home', 'media', 'https://www.youtube.com/'],
  ['youtube-watch', 'media', 'https://www.youtube.com/watch?v=jNQXAC9IVRw'],
  ['bbc-news', 'presse', 'https://www.bbc.com/news'],
  ['lemonde', 'presse', 'https://www.lemonde.fr/'],
  ['amazon-fr', 'commerce', 'https://www.amazon.fr/s?k=clavier+mecanique'],
  ['leboncoin', 'commerce', 'https://www.leboncoin.fr/'],
];

const PORT = 9236;
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PROFILE = path.join(process.env.TEMP, 'ptap-webbattery-profile');
const proc = spawn(CHROME, [
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
  '--no-first-run', '--no-default-browser-check', '--window-size=1300,900',
  '--window-position=580,60', '--lang=fr', 'about:blank',
], { stdio: 'ignore' });
let ok = false;
for (let i = 0; i < 40 && !ok; i++) {
  try { await fetch(`http://127.0.0.1:${PORT}/json/version`); ok = true; }
  catch { await new Promise(r => setTimeout(r, 500)); }
}
const browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`);
const ctx = browser.contexts()[0];
const page = ctx.pages()[0] ?? await ctx.newPage();
await page.setViewportSize({ width: 1280, height: 800 });

const rows = [];
for (const [id, cat, url] of SITES) {
  const row = { id, cat, url, ok: false };
  try {
    const t0 = Date.now();
    await page.goto(url, { timeout: 45000, waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(4000);
    row.nav_ms = Date.now() - t0;
    row.final_url = page.url().slice(0, 120);
    row.title = (await page.title()).slice(0, 80);
    const tv = Date.now();
    const view = await distillHardened(page);
    row.view_ms = Date.now() - tv;
    fs.writeFileSync(path.join(OUT, 'views', `${id}.hardened.txt`), view);
    const png = await page.screenshot();
    fs.writeFileSync(path.join(OUT, 'shots', `${id}.png`), png);
    const lines = view.split('\n');
    row.structured = {
      hardened_bytes: Buffer.byteLength(view),
      hardened_tokens: textTokens(view),
      hardened_lines: lines.length,
      opaque_declared: lines.filter(l => l.startsWith('[pixels]')).length,
      occluded_tagged: lines.filter(l => l.includes('[occluded]')).length,
    };
    row.pixels = {
      png_bytes: png.length,
      viewport_tokens: imageTokens(1280, 800, 'legacy') === 1366 ? 1366 : Math.ceil(1280 * 800 / 750),
      viewport_tokens_retina: imageTokens(2560, 1600, 'highres'),
    };
    row.page = await page.evaluate(() => ({
      scrollH: document.documentElement.scrollHeight,
      nText: document.body.innerText.length,
      nCanvas: document.querySelectorAll('canvas').length,
      nVideo: document.querySelectorAll('video').length,
      nImg: document.querySelectorAll('img').length,
      nIframe: document.querySelectorAll('iframe').length,
    }));
    row.pixels.screens_to_cover_page = Math.max(1, Math.ceil(row.page.scrollH / 800));
    row.consent_banner = /consent|cookie|accepter|Accepter|Tout accepter|Accept all/i.test(view);
    row.ratio_viewport = +(row.pixels.viewport_tokens / row.structured.hardened_tokens).toFixed(2);
    row.ok = true;
  } catch (e) {
    row.error = String(e.message || e).slice(0, 160);
  }
  rows.push(row);
  console.error(`${id}: ${row.ok ? row.structured.hardened_tokens + ' tok, ratio ' + row.ratio_viewport : 'ERR ' + row.error}`);
}

const okRows = rows.filter(r => r.ok);
const tot_struct = okRows.reduce((a, r) => a + r.structured.hardened_tokens, 0);
const tot_pix = okRows.length * 1366;
const ratios = okRows.map(r => r.ratio_viewport).sort((a, b) => a - b);
const median = ratios.length % 2 ? ratios[(ratios.length - 1) / 2]
  : (ratios[ratios.length / 2 - 1] + ratios[ratios.length / 2]) / 2;
const summary = {
  n_ok: okRows.length, n_err: rows.length - okRows.length,
  total_structured_tokens: tot_struct, total_pixel_tokens: tot_pix,
  ratio_of_totals: +(tot_pix / tot_struct).toFixed(2),
  median_per_site_ratio: +median.toFixed(2),
  mean_per_site_ratio: +(ratios.reduce((a, b) => a + b, 0) / ratios.length).toFixed(2),
  sites_structure_ahead: ratios.filter(r => r > 1).length,
  consent_banners: okRows.filter(r => r.consent_banner).length,
  canvas_or_video_sites: okRows.filter(r => r.page.nCanvas + r.page.nVideo > 0).length,
};
fs.writeFileSync(path.join(OUT, 'web-battery.json'), JSON.stringify(rows, null, 1));
fs.writeFileSync(path.join(OUT, 'web-battery-summary.json'), JSON.stringify(summary, null, 1));
await browser.close();
proc.kill();
console.log(JSON.stringify(summary, null, 1));
