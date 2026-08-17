// coverage-guard — the router mitigation that converts SILENT divergences into
// EXPLICIT ones. This is the answer to the 3 silent cells Windows found
// (FL Studio / OBS / rekordbox): a named container whose structure reads "empty"
// while the screen shows painted content, with nothing declaring the blind spot.
//
// It is channel-agnostic (works over UIA / AX / AT-SPI / CDP structure alike):
// the router hands it per-region rectangles + whether structure exposed readable
// content there, plus a way to grab that region's pixels. Two independent guards:
//
//  (A) pixel spot-check — for any region structure calls empty/opaque-unknown,
//      measure "content energy" from a per-region pixel crop. High energy +
//      empty structure  ->  flag `[unverified: pixels show content]`. This is the
//      general converter; it needs no app knowledge.
//  (B) self-consistency — a list/table that declares item COUNT > 0 but exposes
//      0 rows contradicts itself (rekordbox: '32 Tracks' + 0 rows). Flag from the
//      view alone, no pixels needed.
//
// Neither guard tries to READ the hidden content — it only makes the blind spot
// DECLARED, so the router falls back to a pixel crop instead of reading "empty".
import sharp from 'sharp';

// content energy of a PNG crop: fraction of pixels that deviate from the modal
// (background) color. ~0 on a flat/empty pane; high where text/rows are painted.
export async function contentEnergy(pngBuffer) {
  const { data, info } = await sharp(pngBuffer)
    .removeAlpha().resize(64, 64, { fit: 'fill' }).raw().toBuffer({ resolveWithObject: true });
  const n = info.width * info.height;
  // modal color via coarse histogram (16 bins/channel)
  const hist = new Map();
  for (let i = 0; i < data.length; i += 3) {
    const k = (data[i] >> 4) << 8 | (data[i + 1] >> 4) << 4 | (data[i + 2] >> 4);
    hist.set(k, (hist.get(k) || 0) + 1);
  }
  let modeK = 0, modeC = -1;
  for (const [k, c] of hist) if (c > modeC) { modeC = c; modeK = k; }
  const mr = ((modeK >> 8) & 15) << 4, mg = ((modeK >> 4) & 15) << 4, mb = (modeK & 15) << 4;
  let ink = 0;
  for (let i = 0; i < data.length; i += 3) {
    if (Math.abs(data[i] - mr) + Math.abs(data[i + 1] - mg) + Math.abs(data[i + 2] - mb) > 48) ink++;
  }
  return ink / n; // 0..1
}

// Guard A: for each suspect region, crop pixels and flag if content is present.
// suspects: [{ label, rect:[x,y,w,h], hasReadableContent:bool }]
export async function pixelSpotCheck(page, suspects, { threshold = 0.03 } = {}) {
  const out = [];
  for (const s of suspects) {
    if (s.hasReadableContent) { out.push({ ...s, verdict: 'ok' }); continue; }
    const [x, y, w, h] = s.rect;
    let energy = 0;
    try {
      const png = await page.screenshot({ clip: { x, y, width: w, height: h } });
      energy = await contentEnergy(png);
    } catch { energy = -1; }
    const silentRisk = energy >= threshold;
    out.push({
      ...s, energy: +energy.toFixed(3),
      verdict: silentRisk ? 'SILENT->declare-opaque' : 'genuinely-empty',
      line: silentRisk
        ? `[pixels] group ${x},${y},${w},${h} "${s.label}" [unverified: pixels show content]`
        : `group ${x},${y},${w},${h} "${s.label}" (empty, pixel-confirmed)`,
    });
  }
  return out;
}

// Guard B: self-consistency on the structured view text (no pixels).
// Flags "declares N>0 items but 0 rows" (the rekordbox shape).
export function selfConsistency(viewText) {
  const flags = [];
  const countRe = /(\d+)\s+(tracks?|items?|results?|rows?|files?|messages?|projects?)/i;
  const lines = viewText.split('\n');
  const rowLines = lines.filter(l => /^(row|listitem|cell|treeitem)\b/i.test(l)).length;
  for (const l of lines) {
    const m = l.match(countRe);
    if (m && +m[1] > 0 && rowLines === 0) {
      flags.push({ claim: `${m[1]} ${m[2]}`, rowsExposed: 0, line: `${l.trim()}  [inconsistent: count>0 but 0 rows -> unexposed list, crop]` });
    }
  }
  return flags;
}
