// pipeline-tap — PoC: comparing agent input representations for the same screen.
// Captures, for a given page: (1) screenshot pixels, (2) DOM snapshot (semantic layer),
// (3) Skia paint ops via LayerTree.snapshotCommandLog (display-list layer).
// Reports byte sizes and estimated LLM token costs for each.

import { chromium } from 'playwright-core';
import fs from 'node:fs';
import path from 'node:path';

const OUT = path.resolve(import.meta.dirname, '../results');

// --- token estimators -------------------------------------------------------
// Claude vision: tokens ≈ (w*h)/750 (docs formula)
export const imgTokensClaude = (w, h) => Math.ceil((w * h) / 750);
// Patch-based estimate (28x28 patches)
export const imgTokensPatch = (w, h) => Math.ceil(w / 28) * Math.ceil(h / 28);
// Text: rough 4 chars/token
export const textTokens = (s) => Math.ceil(s.length / 4);

// --- distillation: DOMSnapshot -> compact agent view ------------------------
// This mimics what an agent harness would actually feed the model: visible text
// + interactive elements with roles and boxes. Not the raw snapshot JSON.
export function distillDomSnapshot(snap) {
  const strings = snap.strings;
  const doc = snap.documents[0];
  const { nodes, layout } = doc;
  const s = (i) => (i >= 0 && i !== undefined ? strings[i] : '');
  // decode RareStringData (e.g. nodes.inputValue = {index:[], value:[]})
  const rare = (r) => { const m = new Map(); if (r) r.index.forEach((ni, k) => m.set(ni, s(r.value[k]))); return m; };
  const inputValues = rare(nodes.inputValue);
  const lines = [];

  const INTERACTIVE = new Set(['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA', 'SUMMARY', 'LABEL']);
  for (let li = 0; li < layout.nodeIndex.length; li++) {
    const ni = layout.nodeIndex[li];
    const box = layout.bounds[li].map(Math.round);
    if (box[2] === 0 || box[3] === 0) continue; // zero-size
    // skip invisible content (e.g. toast faded out): computedStyles = ['opacity','visibility']
    if (layout.styles && layout.styles[li]) {
      const [op, vis] = layout.styles[li].map(x => s(x));
      if (op === '0' || vis === 'hidden') continue;
    }
    const name = s(nodes.nodeName[ni]);
    const nodeType = nodes.nodeType[ni];
    const text = layout.text !== undefined ? s(layout.text[li]) : '';
    if (nodeType === 3) { // text node
      const t = (text || s(nodes.nodeValue[ni])).trim();
      if (t) lines.push(`text ${box.join(',')} "${t}"`);
    } else if (INTERACTIVE.has(name)) {
      var liveValue = inputValues.has(ni) ? ` value="${inputValues.get(ni)}"` : '';
      // find attributes
      const attrs = nodes.attributes[ni] || [];
      const kv = [];
      for (let a = 0; a < attrs.length; a += 2) {
        const k = s(attrs[a]);
        if (['id', 'type', 'value', 'placeholder', 'aria-label', 'href', 'role', 'name'].includes(k))
          kv.push(`${k}=${s(attrs[a + 1])}`);
      }
      lines.push(`${name.toLowerCase()} ${box.join(',')} ${kv.join(' ')}${liveValue}`.trim());
    }
  }
  return lines.join('\n');
}

// --- distillation: paint ops -> compact draw-command view -------------------
// Keeps op names + text/rect params, drops big byte arrays (rasterized images).
export function distillPaintOps(cmdLog) {
  const lines = [];
  const walk = (cmds, depth = 0) => {
    for (const c of cmds) {
      const m = c.method;
      const p = c.params || {};
      let detail = '';
      if (m === 'drawTextBlob') detail = `@${p.x},${p.y} color=${p.paint?.color ?? '?'}`; // NOTE: no text, no glyphs — content is gone at this level
      else if (m.startsWith('drawRect') || m === 'drawRRect') detail = JSON.stringify(p.rect ?? p.rrect ?? '');
      else if (m === 'drawImageRect') detail = `dst=${JSON.stringify(p.dst ?? '')}`;
      else if (m === 'drawPaint' || m === 'drawColor') detail = p.paint?.color ?? '';
      lines.push(`${'  '.repeat(depth)}${m} ${detail}`.trimEnd());
      if (c.params?.commands) walk(c.params.commands, depth + 1);
    }
  };
  walk(cmdLog);
  return lines.join('\n');
}

// --- main capture -----------------------------------------------------------
export async function capturePage(page, cdp, label) {
  const t0 = Date.now();
  const vp = page.viewportSize();

  // 1) screenshot
  const tShot0 = Date.now();
  const png = await page.screenshot({ type: 'png' });
  const tShot = Date.now() - tShot0;

  // 2) DOM snapshot
  const tDom0 = Date.now();
  const snap = await cdp.send('DOMSnapshot.captureSnapshot', {
    computedStyles: ['opacity', 'visibility'], includeDOMRects: true,
  });
  const tDom = Date.now() - tDom0;
  const domRaw = JSON.stringify(snap);
  const domDistilled = distillDomSnapshot(snap);

  // 3) paint ops via LayerTree — use the latest layer set tracked since launch()
  const tPaint0 = Date.now();
  let paintDistilled = '', paintRaw = '', paintErr = null, nOps = 0;
  try {
    // force a repaint so at least one fresh layerTreeDidChange fires, then settle
    await page.evaluate(() => { document.body.style.opacity = '0.999'; requestAnimationFrame(() => { document.body.style.opacity = '1'; }); }).catch(() => {});
    await page.waitForTimeout(150);
    const layers = cdp._latestLayers || [];
    const drawable = layers.filter(l => l.drawsContent && l.width > 0 && l.height > 0);
    const allOps = [];
    for (const l of drawable) {
      try {
        const { snapshotId } = await cdp.send('LayerTree.makeSnapshot', { layerId: l.layerId });
        const { commandLog } = await cdp.send('LayerTree.snapshotCommandLog', { snapshotId });
        allOps.push(...commandLog);
        await cdp.send('LayerTree.releaseSnapshot', { snapshotId });
      } catch { /* some layers refuse snapshotting */ }
    }
    nOps = allOps.length;
    paintRaw = JSON.stringify(allOps);
    paintDistilled = distillPaintOps(allOps);
  } catch (e) { paintErr = String(e.message || e); }
  const tPaint = Date.now() - tPaint0;

  const result = {
    label, viewport: vp, wallMs: Date.now() - t0,
    screenshot: {
      bytes: png.length, captureMs: tShot,
      tokensClaude: imgTokensClaude(vp.width, vp.height),
      tokensPatch: imgTokensPatch(vp.width, vp.height),
    },
    domSnapshot: {
      rawBytes: domRaw.length, distilledBytes: domDistilled.length,
      captureMs: tDom, tokensDistilled: textTokens(domDistilled),
    },
    paintOps: {
      rawBytes: paintRaw.length, distilledBytes: paintDistilled.length, nOps,
      captureMs: tPaint, tokensDistilled: textTokens(paintDistilled), error: paintErr,
    },
  };

  const base = path.join(OUT, label.replace(/[^a-z0-9-]/gi, '_'));
  fs.writeFileSync(`${base}.png`, png);
  fs.writeFileSync(`${base}.dom.txt`, domDistilled);
  fs.writeFileSync(`${base}.paint.txt`, paintDistilled);
  fs.writeFileSync(`${base}.paint.raw.json`, paintRaw || '[]');
  return { result, domDistilled, png };
}

export async function launch() {
  const browser = await chromium.launch({
    executablePath: '/opt/pw-browsers/chromium',
    headless: true,
    args: ['--force-color-profile=srgb', '--disable-lcd-text'],
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('DOM.enable');
  await cdp.send('Page.enable');
  await cdp.send('LayerTree.enable');
  cdp._latestLayers = [];
  cdp.on('LayerTree.layerTreeDidChange', (ev) => { if (ev.layers?.length) cdp._latestLayers = ev.layers; });
  return { browser, page, cdp };
}
