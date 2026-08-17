// coverage-guard — the router mitigation that converts SILENT divergences into
// EXPLICIT ones. This is the answer to the silent cells the campaign found
// (FL Studio / OBS / rekordbox on Windows, Zoom's stage on macOS, qBittorrent's
// speed graph on Linux): a named container whose structure reads "empty" while
// the screen shows painted content, with nothing declaring the blind spot.
//
// It is channel-agnostic (works over UIA / AX / AT-SPI / CDP structure alike):
// the router hands it per-region rectangles + whether structure exposed readable
// content there, plus a way to grab that region's pixels. Two independent guards:
//
//  (A) pixel spot-check — for any region structure calls empty/opaque-unknown,
//      measure "content energy" AND "edge fraction" from a per-region pixel
//      crop. Either signal + empty structure  ->  flag
//      `[unverified: pixels show content]`. This is the general converter; it
//      needs no app knowledge.
//  (B) self-consistency — a list/table that declares item COUNT > 0 but exposes
//      0 rows contradicts itself (rekordbox: '32 Tracks' + 0 rows). Flag from the
//      view alone, no pixels needed.
//
// Neither guard tries to READ the hidden content — it only makes the blind spot
// DECLARED, so the router falls back to a pixel crop instead of reading "empty".
//
// CALIBRATION (2026-08-17, recalibrated on the full campaign corpus). The
// measured spectrum of real painted content across the three OSes is
// 0.06–0.07 (FL/OBS dense panes), 0.036 (Swing waveform), 0.029 (a full Flutter
// login UI), 0.020 (qBittorrent's sparse line-art chart), while every
// genuinely-empty control measures 0.000 on both metrics. The original 0.03
// threshold — set to split 0.06 from 0.00 — sat in the MIDDLE of that content
// distribution and missed the sparse end. Both thresholds are therefore 0.01,
// and the two metrics vote independently (either one fires): energy sees area
// coverage, edge fraction sees thin lines and small text that area statistics
// dilute. KNOWN LIMITS, kept on purpose: (1) crops MUST come from the window's
// own surface (PrintWindow / CGWindowListCreateImage per window / XComposite
// NameWindowPixmap), never a screen crop — an overlapping or transparent window
// otherwise donates its ink to the region under test (measured: 0.042 vs 0.021
// on Linux occlusion, 129x on macOS transparency); (2) both metrics are
// area-relative, so a small painted band inside a huge declared rect is diluted
// (macOS measured 4.7x); (3) guard A only fires where structure is EMPTY — it
// cannot see the macOS-Swing SUBSTITUTION class (a plausible wrong string in a
// populated node) nor act-side failures, which need their own guards.
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

// edge fraction of a PNG crop, at full resolution: fraction of adjacent pixel
// pairs (horizontal + vertical) differing by >24 on any channel. Thin curves,
// grid lines and small text produce edges far in excess of their area, which is
// exactly what the downsampled energy metric dilutes away.
export async function edgeFraction(pngBuffer) {
  const { data, info } = await sharp(pngBuffer)
    .removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const { width: w, height: h } = info;
  let edges = 0, pairs = 0;
  const px = (x, y, c) => data[(y * w + x) * 3 + c];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (x + 1 < w) {
      pairs++;
      if (Math.abs(px(x, y, 0) - px(x + 1, y, 0)) > 24 || Math.abs(px(x, y, 1) - px(x + 1, y, 1)) > 24
        || Math.abs(px(x, y, 2) - px(x + 1, y, 2)) > 24) edges++;
    }
    if (y + 1 < h) {
      pairs++;
      if (Math.abs(px(x, y, 0) - px(x, y + 1, 0)) > 24 || Math.abs(px(x, y, 1) - px(x, y + 1, 1)) > 24
        || Math.abs(px(x, y, 2) - px(x, y + 1, 2)) > 24) edges++;
    }
  }
  return pairs ? edges / pairs : 0; // 0..1
}

// The single decision path shared by pixelSpotCheck and any verification
// harness: judge one crop, return both raw metrics and the verdict.
export async function judgeCrop(pngBuffer, { threshold = 0.01, edgeThreshold = 0.01 } = {}) {
  const energy = await contentEnergy(pngBuffer);
  const edge = await edgeFraction(pngBuffer);
  return {
    energy: +energy.toFixed(3),
    edge: +edge.toFixed(4),
    silentRisk: energy >= threshold || edge >= edgeThreshold,
  };
}

// Guard A: for each suspect region, crop pixels and flag if content is present.
// suspects: [{ label, rect:[x,y,w,h], hasReadableContent:bool }]
export async function pixelSpotCheck(page, suspects, { threshold = 0.01, edgeThreshold = 0.01 } = {}) {
  const out = [];
  for (const s of suspects) {
    if (s.hasReadableContent) { out.push({ ...s, verdict: 'ok' }); continue; }
    const [x, y, w, h] = s.rect;
    let j = { energy: -1, edge: -1, silentRisk: false };
    try {
      const png = await page.screenshot({ clip: { x, y, width: w, height: h } });
      j = await judgeCrop(png, { threshold, edgeThreshold });
    } catch { /* unreadable region: keep sentinel values */ }
    out.push({
      ...s, energy: j.energy, edge: j.edge,
      verdict: j.silentRisk ? 'SILENT->declare-opaque' : 'genuinely-empty',
      line: j.silentRisk
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
