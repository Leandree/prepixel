// Experiment 2: cost of perceiving CHANGE.
// After each interaction: (a) full re-screenshot cost, (b) structured diff cost
// (line diff of the distilled DOM view). Includes a "living screen" scenario.
import { launch, capturePage, textTokens, imgTokensClaude } from './capture.mjs';
import fs from 'node:fs';
import path from 'node:path';

const url = 'file://' + path.resolve(import.meta.dirname, '../pages/testapp.html');

// simple line-set diff (order-insensitive enough for our distilled views)
function lineDiff(before, after) {
  const a = before.split('\n'), b = after.split('\n');
  const ca = new Map(), cb = new Map();
  for (const l of a) ca.set(l, (ca.get(l) || 0) + 1);
  for (const l of b) cb.set(l, (cb.get(l) || 0) + 1);
  const removed = [], added = [];
  for (const [l, n] of ca) { const d = n - (cb.get(l) || 0); for (let i = 0; i < d; i++) removed.push('- ' + l); }
  for (const [l, n] of cb) { const d = n - (ca.get(l) || 0); for (let i = 0; i < d; i++) added.push('+ ' + l); }
  return [...removed, ...added].join('\n');
}

async function domView(page, cdp) {
  const t0 = Date.now();
  const snap = await cdp.send('DOMSnapshot.captureSnapshot', { computedStyles: ['opacity', 'visibility'], includeDOMRects: true });
  const { distillDomSnapshot } = await import('./capture.mjs');
  return { view: distillDomSnapshot(snap), ms: Date.now() - t0 };
}

const { browser, page, cdp } = await launch();
await page.goto(url, { waitUntil: 'networkidle' });
await page.waitForTimeout(300);

const vp = page.viewportSize();
const shotTokens = imgTokensClaude(vp.width, vp.height); // constant per full screenshot
const steps = [];
let { view: prev } = await domView(page, cdp);

async function step(name, action, settleMs = 250) {
  await action();
  await page.waitForTimeout(settleMs);
  const { view, ms } = await domView(page, cdp);
  const diff = lineDiff(prev, view);
  steps.push({
    name,
    diffLines: diff ? diff.split('\n').length : 0,
    diffBytes: diff.length,
    diffTokens: diff ? textTokens(diff) : 0,
    screenshotTokens: shotTokens,
    captureMs: ms,
    diffPreview: diff.split('\n').slice(0, 6).join('\n'),
  });
  prev = view;
}

await step('click Ship #1043 (badge + toast)', () => page.click('button[data-id="1043"]'));
await step('toast disappears (idle wait)', () => Promise.resolve(), 1800);
await step('type customer name', () => page.fill('#customer', 'Durand SAS'));
await step('submit form (new row + toast)', () => page.click('#addBtn'));
await step('no-op (nothing changed)', () => Promise.resolve(), 400);

// --- living screen: feed updating on its own -------------------------------
await page.evaluate(() => window.startFeed(400));
const living = { samples: [], screenshotPolicyTokens: 0, diffPolicyTokens: 0 };
let lprev = (await domView(page, cdp)).view;
const T = 6; // seconds observed
for (let i = 0; i < T; i++) {
  await page.waitForTimeout(1000);
  const { view } = await domView(page, cdp);
  const diff = lineDiff(lprev, view);
  const dTok = diff ? textTokens(diff) : 0;
  living.samples.push({ second: i + 1, diffTokens: dTok, diffLines: diff ? diff.split('\n').length : 0 });
  living.screenshotPolicyTokens += shotTokens; // 1 fps screenshot policy
  living.diffPolicyTokens += dTok;             // structured diff policy
  lprev = view;
}
await page.evaluate(() => window.stopFeed());

const out = { screenshotTokensPerFrame: shotTokens, steps, living };
fs.writeFileSync(path.resolve(import.meta.dirname, '../results/diffs.json'), JSON.stringify(out, null, 2));
console.log(JSON.stringify(out, null, 2));
await browser.close();
