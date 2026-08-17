// NOTE (2026-08-17, post-recalibration): this is the HISTORICAL harness whose 0.03
// single-vote run produced the false negative recorded in the qBittorrent cell.
// Kept as-run. The current decision path is coverage-guard v2 (judgeCrop: 0.01 +
// edge vote) — see campaign/linux/recalibration-check.mjs for the corpus run.
// Run coverage-guard's contentEnergy on the qBittorrent suspect region
// (SpeedPlotView custom-paint = the OBS mimicry shape) + a genuinely-empty control.
import sharp from 'sharp';
import { contentEnergy, selfConsistency } from '/home/leandre/prepixel/src/coverage-guard.mjs';
import fs from 'node:fs';

const [png, outDir] = process.argv.slice(2);
const REGIONS = [
  { label: 'SpeedPlotView (custom-paint graph, AT-SPI: nameless filler kids=0)',
    rect: [154, 313, 1038, 407], hasReadableContent: false, tag: 'graph' },
  { label: 'empty transfer table body (structure ALSO says empty: "Tous (0)")',
    rect: [154, 110, 1030, 150], hasReadableContent: false, tag: 'table' },
];
const out = [];
for (const r of REGIONS) {
  const [x, y, w, h] = r.rect;
  const crop = await sharp(png).extract({ left: x, top: y, width: w, height: h }).png().toBuffer();
  fs.writeFileSync(`${outDir}/guard-crop-${r.tag}.png`, crop);
  const energy = await contentEnergy(crop);
  const silentRisk = energy >= 0.03;
  out.push({
    ...r, energy: +energy.toFixed(3),
    verdict: r.hasReadableContent ? 'ok' : silentRisk ? 'SILENT->declare-opaque' : 'genuinely-empty',
    line: silentRisk
      ? `[pixels] group ${x},${y},${w},${h} "${r.label}" [unverified: pixels show content]`
      : `group ${x},${y},${w},${h} "${r.label}" (empty, pixel-confirmed)`,
  });
}
// guard B on the sidebar view text: counts declare 0 and rows are 0 -> consistent
const viewText = fs.readFileSync(`${outDir}/qbt-sidebar-view.txt`, 'utf8');
const b = selfConsistency(viewText);
console.log(JSON.stringify({ guardA: out, guardB_flags: b }, null, 1));
