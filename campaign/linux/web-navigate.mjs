// LINUX CONFIRMATION RUN of campaign/macos/web-navigate.mjs — identical steps & router,
// only paths changed; Chrome 148 (playwright cache) headed under Xvfb, CDP :9223.
// "Can we actually browse the real web this way?" — blind navigation on live sites.
//
// Rule of the game: everything the router decides comes from the STRUCTURED VIEW
// ONLY (the lines the distiller published: tag, box, text). The click is dispatched
// at those coordinates. No screenshot is consulted anywhere in the decision loop —
// screenshots are taken AFTER each step purely as evidence for a human reader.
//
// Round 1 of this probe scored 3/6 and every one of the three "failures" was the
// ROUTER's fault, not the channel's, which is exactly why they are worth encoding:
//   - it matched text lines and ignored the interactive line whose box CONTAINS the
//     text, so it aimed at MDN's "Tutorial" believing it was a link when the view
//     had already published `summary 16,409,224,32` one line above. Clicking it
//     toggled the disclosure widget — correct behaviour, wrong expectation.
//     => fixed here by joining text to its innermost enclosing interactive line and
//        reading the affordance off the tag (a = navigate, summary/button = act).
//   - it expected a "Pull requests" tab on torvalds/linux, which has PRs disabled.
//     The view did not invent one. That is the desired failure mode, so it is now a
//     first-class expectation (`absent`) instead of a failure.
// Both fixes are pure router logic: no extra DOM access, no new data in the view.
import { chromium } from 'playwright-core';
import { distillHardened } from '/home/leandre/prepixel/src/distill-hardened.mjs';
import { imageTokens } from '/home/leandre/prepixel/src/image-tokens.mjs';
import fs from 'node:fs';

const OUT = '/home/leandre/prepixel/results/web-battery-linux';
const SHOTS = `${OUT}/nav-shots`, VIEWS = `${OUT}/nav-views`;
for (const d of [SHOTS, VIEWS]) fs.mkdirSync(d, { recursive: true });

const VW = 1280, VH = 800;
const SHOT_TOKENS = imageTokens(VW, VH);
const tok = s => Math.ceil(s.length / 4);
const INTERACTIVE_RE = /^(a|button|summary|input|select|textarea|label) (-?\d+),(-?\d+),(\d+),(\d+)/;
const TEXT_RE = /^text (-?\d+),(-?\d+),(\d+),(\d+) "(.*?)"( \[occluded\])?$/;

const STEPS = [
  { id: 'hn-newest', url: 'https://news.ycombinator.com/',
    pick: /"new"$/, kind: 'navigate', expect: /newest/, why: 'tiny text link in a dense header' },
  { id: 'wikipedia-link', url: 'https://en.wikipedia.org/wiki/Graphics_pipeline',
    pick: /"Rasterisation"|"Rasterization"/, kind: 'navigate', expect: /Rasteri[sz]ation/, why: 'in-article link among competing occurrences' },
  { id: 'github-insights', url: 'https://github.com/torvalds/linux',
    pick: /"Insights"$/, kind: 'navigate', expect: /\/pulse|graphs/, why: 'app-shell nav tab on a JS-heavy page' },
  { id: 'github-absent-pr', url: 'https://github.com/torvalds/linux',
    pick: /"Pull requests"/, kind: 'absent', why: 'NEGATIVE CONTROL: this repo has PRs disabled; a correct view must not offer the tab' },
  { id: 'mdn-tutorial', url: 'https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API',
    pick: /"Tutorial"$/, kind: 'toggle', why: 'disclosure widget that LOOKS like a link in the text stream' },
  { id: 'mdn-navigate', url: 'https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API',
    pick: /"Canvas tutorial"/, kind: 'navigate', expect: /Tutorial/i, why: 'the real link, two lines below the decoy' },
  { id: 'ddg-images', url: 'https://duckduckgo.com/?q=gpu+rasterization',
    pick: /"Images"$/, kind: 'navigate', expect: /images/i, why: 'result-page filter tab' },
  { id: 'hn-scrolled', url: 'https://news.ycombinator.com/',
    pick: /"More"$/, kind: 'navigate', expect: /\?p=2|next=/, why: 'BELOW THE FOLD — forces scroll-and-search', maxScrolls: 6 },
];

const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0] ?? await ctx.newPage();
const cdp = await ctx.newCDPSession(page);
await cdp.send('Emulation.setDeviceMetricsOverride', { width: VW, height: VH, deviceScaleFactor: 1, mobile: false });

// The router's aim step, working purely on published lines: take the matched text
// box, then pick the SMALLEST interactive box that contains its centre. The tag of
// that box is the affordance — this is the join the first round was missing.
function aim(view, textLine) {
  const t = textLine.match(TEXT_RE);
  if (!t) return null;
  const [x, y, w, h] = t.slice(1, 5).map(Number);
  const cx = x + w / 2, cy = y + h / 2;
  let best = null;
  for (const l of view.split('\n')) {
    const m = l.match(INTERACTIVE_RE);
    if (!m) continue;
    const [bx, by, bw, bh] = m.slice(2, 6).map(Number);
    if (cx < bx || cx > bx + bw || cy < by || cy > by + bh) continue;
    if (!best || bw * bh < best.area) best = { tag: m[1], box: [bx, by, bw, bh], area: bw * bh, line: l };
  }
  return { text_box: [x, y, w, h], centre: [cx, cy], control: best,
           affordance: best ? (best.tag === 'a' ? 'navigate' : best.tag === 'summary' ? 'toggle' : 'act') : 'text-only' };
}

const results = [];
for (const s of STEPS) {
  const r = { id: s.id, url: s.url, why: s.why, pick: String(s.pick), kind: s.kind, expect: s.expect ? String(s.expect) : null };
  try {
    await page.goto(s.url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3500);

    // search phase: read, and scroll only if the step allows it
    let view = '', hit = null, scrolls = 0, viewTokens = 0, viewsRead = 0;
    for (;;) {
      view = await distillHardened(page);
      viewsRead++; viewTokens += tok(view);
      const hits = view.split('\n').filter(l => TEXT_RE.test(l) && s.pick.test(l));
      if (hits.length) { hit = hits.find(l => !/\[occluded\]/.test(l)) || hits[0]; r.candidates = hits.slice(0, 3); break; }
      if (scrolls >= (s.maxScrolls ?? 0)) break;
      await page.evaluate(h => scrollBy(0, h * 0.9), VH);
      await page.waitForTimeout(700); scrolls++;
    }
    Object.assign(r, { scrolls, views_read: viewsRead, view_tokens_spent: viewTokens,
                       shot_tokens_equivalent: viewsRead * SHOT_TOKENS, final_view_tokens: tok(view) });
    fs.writeFileSync(`${VIEWS}/${s.id}.txt`, view);

    if (s.kind === 'absent') {
      r.ok = !hit;
      r.detail = hit ? `the view offered a control that does not exist on this page: ${hit}`
                     : 'view correctly reports the control as absent — no fabricated affordance';
      results.push(r); console.error(`${r.ok ? 'ok  ' : 'FAIL'} ${s.id.padEnd(17)} ${r.detail.slice(0, 70)}`); continue;
    }
    if (!hit) { r.ok = false; r.reason = 'target never appeared in the structured view'; results.push(r); console.error(`FAIL ${s.id} — ${r.reason}`); continue; }
    if (/\[occluded\]/.test(hit)) { r.ok = false; r.reason = 'every occurrence is declared [occluded] — a correct router refuses to aim'; results.push(r); console.error(`FAIL ${s.id} — ${r.reason}`); continue; }

    const a = aim(view, hit);
    r.chosen_line = hit; r.aim = a;
    // The affordance the view published must match what the step expects to happen.
    if (a.affordance !== s.kind) {
      r.ok = false;
      r.reason = `view declares affordance '${a.affordance}' (<${a.control?.tag}>), step expected '${s.kind}' — router must not treat these alike`;
      results.push(r); console.error(`FAIL ${s.id} — ${r.reason}`); continue;
    }

    const [cx, cy] = a.control ? [a.control.box[0] + a.control.box[2] / 2, a.control.box[1] + a.control.box[3] / 2] : a.centre;
    r.click_at = [cx, cy];
    const before = page.url(), viewBefore = view;
    for (const type of ['mousePressed', 'mouseReleased'])
      await cdp.send('Input.dispatchMouseEvent', { type, x: cx, y: cy, button: 'left', clickCount: 1 });
    await page.waitForTimeout(4000);
    r.url_before = before; r.url_after = page.url(); r.title_after = await page.title();

    if (s.kind === 'toggle') {
      const viewAfter = await distillHardened(page);
      r.view_delta_lines = viewAfter.split('\n').length - viewBefore.split('\n').length;
      r.ok = r.url_after === before && r.view_delta_lines !== 0;
      r.detail = `disclosure toggled in place: URL unchanged, view changed by ${r.view_delta_lines} lines — the effect is visible IN the channel, no screenshot needed to confirm it`;
      if (!r.ok) r.reason = 'expected an in-place view change with no navigation';
    } else {
      r.ok = s.expect.test(r.url_after) || s.expect.test(r.title_after);
      if (!r.ok) r.reason = 'click landed, but the browser ended up somewhere else';
    }
    await page.screenshot({ path: `${SHOTS}/${s.id}-after.png` });
  } catch (e) {
    r.ok = false; r.reason = String(e).split('\n')[0].slice(0, 180);
  }
  results.push(r);
  console.error(`${r.ok ? 'ok  ' : 'FAIL'} ${s.id.padEnd(17)} scroll=${r.scrolls ?? '-'} ${r.url_after || r.reason || ''}`);
}

await cdp.send('Emulation.clearDeviceMetricsOverride');
const summary = {
  passed: results.filter(x => x.ok).length, total: results.length,
  by_kind: Object.fromEntries(['navigate', 'toggle', 'absent'].map(k => {
    const rs = results.filter(x => x.kind === k);
    return [k, `${rs.filter(x => x.ok).length}/${rs.length}`];
  })),
  viewport_shot_tokens: SHOT_TOKENS,
  total_view_tokens_spent: results.reduce((a, x) => a + (x.view_tokens_spent || 0), 0),
  total_shot_tokens_equivalent: results.reduce((a, x) => a + (x.shot_tokens_equivalent || 0), 0),
  scrolled_steps: results.filter(x => x.scrolls > 0).map(x => ({ id: x.id, scrolls: x.scrolls, views: x.views_read })),
};
fs.writeFileSync(`${OUT}/web-navigation.json`, JSON.stringify({ summary, steps: results }, null, 2));
console.log(JSON.stringify(summary, null, 1));
process.exit(0);
