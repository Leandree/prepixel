// Offline acceptance for the CDP channel (P1). Launches a LOCAL headless
// Chromium on a debug port, serves a fixture page that carries one instance
// of every gap the channel is supposed to close, runs cdp_view.mjs against
// it as a subprocess, and asserts on the records.
//
// Local, because the only other Chromium available is inside a VM that is
// currently producing measured cells — a test must never be the reason a
// cell moves.
//
// Run: node campaign/osworld/test_cdp_view.mjs
import { chromium } from 'playwright-core';
import { execFileSync } from 'node:child_process';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PORT = 9321;          // deliberately not 9222/9223: those are the VMs
const HTTP_PORT = 9322;

const FIXTURE = `<!doctype html><meta charset=utf-8><title>Fixture</title>
<style>body{margin:0;font:14px sans-serif}
 .tall{height:2400px}
 #hidden{display:none}
 #cover{position:fixed;left:0;top:0;width:100%;height:40px;background:#333;z-index:9}
 #bg{width:80px;height:40px;background-image:url(data:image/gif;base64,R0lGODlhAQABAAAAACw=)}
</style>
<div id=cover></div>
<h1>Fixture heading</h1>
<label for=q>Search terms</label>
<input id=q type=text value="typed value here">
<input id=cb type=checkbox checked>
<input id=cb2 type=checkbox>
<button aria-pressed="true">Pressed button</button>
<a href="/somewhere">A link</a>
<select id=sel><option>alpha</option><option selected>beta</option></select>
<div role=switch aria-checked="true" aria-label="Do not track">toggle</div>
<div role=button aria-expanded="true" aria-label="Expander">expand</div>
<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" alt="An image">
<canvas width=50 height=20></canvas>
<div id=bg></div>
<p id=hidden>never visible</p>
<div class=tall></div>
<button id=below>Below the fold</button>
<iframe srcdoc="<p>inside same-origin frame</p>" width=200 height=60></iframe>
`;

let failures = 0;
const check = (cond, what, detail) => {
  if (cond) { console.log(`  ok   ${what}`); return; }
  failures += 1;
  console.log(`  FAIL ${what}${detail ? ' — ' + detail : ''}`);
};

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
  res.end(FIXTURE);
});
await new Promise((r) => server.listen(HTTP_PORT, '127.0.0.1', r));

const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.PW_CHROME || '/home/leandre/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',
  args: [`--remote-debugging-port=${PORT}`],
});
const page = await browser.newPage();
await page.setViewportSize({ width: 1200, height: 800 });
await page.goto(`http://127.0.0.1:${HTTP_PORT}/`);
await page.focus('#q');

const raw = execFileSync('node', [
  path.join(HERE, 'cdp_view.mjs'),
  '--endpoint', `http://127.0.0.1:${PORT}`,
  '--offset', '100,200',
], { encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 });

let out;
try { out = JSON.parse(raw); } catch (e) {
  console.log('UNPARSEABLE OUTPUT:', raw.slice(0, 800));
  process.exit(1);
}

console.log(`\ncdp_view: ok=${out.ok} records=${out.records?.length} ` +
            `offscreen=${out.meta?.offscreen_emitted}`);
if (!out.ok) { console.log('error:', out.error); process.exit(1); }

const R = out.records;
const find = (p) => R.find(p);
const line = (needle) => R.find((r) => r.line.includes(needle));

console.log('\nassertions:');
// The whole reason this channel exists: a field's actual text.
check(!!find((r) => r.role === 'entry' && r.value === 'typed value here'),
      'entry carries its typed value',
      JSON.stringify(find((r) => r.role === 'entry')));
check(!!find((r) => r.role === 'entry' && r.label === 'Search terms'),
      'entry takes its name from <label for>');
check(!!find((r) => r.role === 'entry' && r.states.focused === true),
      'focused entry is marked focused');

// Toggle state read, not inferred.
check(!!find((r) => r.role === 'check-box' && r.states.checked === true),
      'checked checkbox reads checked:true');
check(!!find((r) => r.role === 'check-box' && r.states.checked === false),
      'unchecked checkbox reads checked:false');
check(!!find((r) => r.role === 'toggle-button' &&
                    r.states.checked === true &&
                    r.label === 'Do not track'),
      'aria switch maps to toggle-button with state');
check(!!find((r) => r.role === 'push-button' && r.states.pressed === true),
      'aria-pressed becomes pressed');
check(!!find((r) => r.role === 'push-button' && r.states.expanded === true &&
                    r.label === 'Expander'),
      'aria-expanded becomes expanded');

// Role vocabulary is the platform's, not HTML's.
check(!!find((r) => r.role === 'link' && r.label === 'A link'),
      'anchor maps to link, named by its text');
check(!!find((r) => r.role === 'combo-box' && r.value === 'beta'),
      'select maps to combo-box carrying the selected option',
      JSON.stringify(find((r) => r.role === 'combo-box')));
check(!!find((r) => r.role === 'heading' && r.label === 'Fixture heading'),
      'h1 maps to heading');

// Below the fold: present, marked, in PAGE coordinates.
const below = find((r) => r.kind === 'offscreen' &&
                          r.label === 'Below the fold');
check(!!below, 'below-the-fold button is emitted as offscreen');
check(!!below && below.line.startsWith('[offscreen] '),
      'offscreen line is prefixed');
check(!!below && below.rect[1] > 2000,
      'offscreen rect is in page coords (y > 2000), not screen',
      below && String(below.rect));

// Blind spots declared, hidden content dropped, occlusion flagged.
check(!!find((r) => r.kind === 'pixels' && r.role === 'image' &&
                    r.label === 'An image'), 'img declared as [pixels]');
check(!!find((r) => r.kind === 'pixels' && r.role === 'canvas'),
      'canvas declared as [pixels]');
check(!line('never visible'), 'display:none content is absent');
check(!!line('inside same-origin frame'),
      'same-origin iframe content is recursed');
check(!!R.find((r) => r.line.includes('[occluded]')),
      'the covered element is flagged [occluded]');

// The offset contract: on-screen records translated, offscreen ones not.
const h1 = find((r) => r.role === 'heading');
check(!!h1 && h1.rect[0] >= 100 && h1.rect[1] >= 200,
      'on-screen rects are translated by --offset', h1 && String(h1.rect));

// Grammar parity with the AT-SPI channel: same spelling, or the composed
// view shows phantom diffs at every channel boundary.
const cbLine = find((r) => r.role === 'check-box' &&
                           r.states.checked === true).line;
check(/^check-box \d+,\d+,\d+,\d+.* state=checked:true$/.test(cbLine),
      'state string matches _state_str spelling', cbLine);

// Chrome must survive the visit — the driver calls this every step.
const stillAlive = await page.evaluate(() => 1 + 1).catch(() => null);
check(stillAlive === 2, 'the page survives cdp_view disconnecting');

// ------------------------------------------------------------- the act side
// cdp_act must land on the SAME node the view described, which is the whole
// reason the view parks handles on the page.
const act = (rec, op, extra = []) => JSON.parse(execFileSync('node', [
  path.join(HERE, 'cdp_act.mjs'),
  '--endpoint', `http://127.0.0.1:${PORT}`,
  '--handle', String(rec.h), '--op', op, ...extra,
], { encoding: 'utf8' }));

console.log('\nact assertions:');
const entry = find((r) => r.role === 'entry' && r.value === 'typed value here');
const sv = act(entry, 'set_value', ['--value', 'replaced text']);
check(sv.ok && await page.$eval('#q', (e) => e.value) === 'replaced text',
      'set_value writes the field the view described', JSON.stringify(sv));

const cb2 = R.filter((r) => r.role === 'check-box')
  .find((r) => r.states.checked === false);
const tg = act(cb2, 'toggle', ['--to', 'true']);
check(tg.ok && await page.$eval('#cb2', (e) => e.checked) === true,
      'toggle reaches the asked state', JSON.stringify(tg));
const again = act(cb2, 'toggle', ['--to', 'true']);
check(again.ok && again.noop === true,
      'toggling to the state it already holds is a declared no-op',
      JSON.stringify(again));

const sel = find((r) => r.role === 'combo-box');
const svs = act(sel, 'set_value', ['--value', 'alpha']);
check(svs.ok && await page.$eval('#sel', (e) => e.value) === 'alpha',
      'set_value on a combo-box picks the option by its text',
      JSON.stringify(svs));

const st = act(below, 'scroll_to');
const scrolledY = await page.evaluate(() => scrollY);
check(st.ok && scrolledY > 1000,
      'scroll_to brings a below-the-fold element onto the screen',
      `${JSON.stringify(st)} scrollY=${scrolledY}`);

// A stale handle must SAY so rather than act on whatever is at that index.
await page.evaluate(() => { delete window.__prepixel; });
const stale = act(entry, 'click');
check(!stale.ok && /stale-handle/.test(stale.err || ''),
      'a handle from a page that has navigated reports stale-handle',
      JSON.stringify(stale));

await browser.close();
server.close();
console.log(failures ? `\n${failures} FAILURES` : '\nALL PASS');
process.exit(failures ? 1 : 0);
