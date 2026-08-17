// Recalibration check for src/coverage-guard.mjs (threshold 0.03 -> 0.01 + edge
// vote): run the NEW decision path (judgeCrop) over every guard crop the
// campaign kept on any OS, against ground truth established in the cells.
// Every real-content sample must flag; every genuinely-empty sample must not.
// The old decision (energy >= 0.03, no edge vote) is printed alongside so the
// delta is visible. Exits non-zero on any mismatch.
import sharp from 'sharp';
import { judgeCrop } from '/home/leandre/prepixel/src/coverage-guard.mjs';

const A = '/home/leandre/prepixel/campaign/results/artifacts';
const CORPUS = [
  // Windows — real apps, per-window PrintWindow captures (cells record energies 0.085-0.621)
  { p: `${A}/windows/guard-flstudio-region0.png`, truth: 'content', src: 'FL Studio region0 (windows-flstudio-uia)' },
  { p: `${A}/windows/guard-flstudio-region1.png`, truth: 'content', src: 'FL Studio region1' },
  { p: `${A}/windows/guard-flstudio-region2.png`, truth: 'content', src: 'FL Studio region2' },
  { p: `${A}/windows/guard-flstudio-region3.png`, truth: 'content', src: 'FL Studio region3' },
  { p: `${A}/windows/guard-flstudio-region4.png`, truth: 'content', src: 'FL Studio region4' },
  { p: `${A}/windows/guard-obs-region0.png`, truth: 'content', src: 'OBS preview (windows-obs-qt-uia, 0.245)' },
  { p: `${A}/windows/guard-swing-region0.png`, truth: 'content', src: 'Swing client area (windows-swing-jab, 0.186)' },
  // macOS — window surfaces
  { p: `${A}/macos/swing-window-surface.png`, truth: 'content', src: 'Swing window (macos-swing, substitution cell)' },
  { p: `${A}/macos/vibe-island-screen-region.png`, truth: 'excluded', src: 'overlay SCREEN crop (capture-path violation — per-window rule case, not a threshold case)' },
  // Linux — this campaign round
  { p: `${A}/linux-atspi/guard-crop-graph.png`, truth: 'content', src: 'qBittorrent chart (0.020 — the miss that triggered this recalibration)' },
  { p: `${A}/linux-atspi/guard-crop-swing-scope.png`, truth: 'content', src: 'Swing waveform panel (0.036)' },
  { p: `${A}/linux-atspi/xcomp-appflowy-window.png`, truth: 'content', src: 'AppFlowy full login UI (0.029)' },
  { p: `${A}/linux-atspi/xcomp-mousepad-window.png`, truth: 'content', src: 'Mousepad window, two text lines (sparse)' },
  { p: `${A}/linux-atspi/guard-crop-table.png`, truth: 'empty', src: 'qBittorrent empty table body (structure agrees: 0 items)' },
  // Derived empty controls: genuinely blank regions cropped from real window surfaces
  { p: `${A}/linux-atspi/xcomp-mousepad-window.png`, rect: [50, 300, 700, 250], truth: 'empty', src: 'Mousepad blank area (derived control)' },
  { p: `${A}/linux-atspi/xcomp-appflowy-window.png`, rect: [80, 610, 350, 80], truth: 'empty', src: 'AppFlowy blank margin (derived control)' },
];

let fails = 0;
const rows = [];
for (const c of CORPUS) {
  let buf = await sharp(c.p).png().toBuffer();
  if (c.rect) {
    const [left, top, width, height] = c.rect;
    buf = await sharp(buf).extract({ left, top, width, height }).png().toBuffer();
  }
  const j = await judgeCrop(buf);                       // NEW calibration (0.01 + edge vote)
  const oldFlag = j.energy >= 0.03;                     // OLD decision
  let ok = 'n/a';
  if (c.truth === 'content') ok = j.silentRisk;
  if (c.truth === 'empty') ok = !j.silentRisk;
  if (ok === false) fails++;
  rows.push({ src: c.src, truth: c.truth, energy: j.energy, edge: j.edge,
              new_flag: j.silentRisk, old_flag: oldFlag, ok });
}
console.table(rows);
const judged = rows.filter(r => r.ok !== 'n/a');
console.log(`${judged.filter(r => r.ok).length}/${judged.length} correct under new calibration; ` +
  `old calibration got ${judged.filter(r => (r.truth === 'content') === r.old_flag).length}/${judged.length}. ` +
  (fails ? `FAIL: ${fails} mismatches` : 'PASS: full separation, zero false positives'));
process.exit(fails ? 1 : 0);
