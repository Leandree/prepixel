// Compare a window's OWN surface (XCompositeNameWindowPixmap, via grabwin.c)
// with the screen crop at the same rect: convert both to PNG, measure divergence,
// and run the guard's content-energy on each — the macOS per-window-capture rule,
// demonstrated on X11.
import sharp from 'sharp';
import fs from 'node:fs';
import { contentEnergy } from '/home/leandre/prepixel/src/coverage-guard.mjs';

function readPPM(path) {
  const buf = fs.readFileSync(path);
  // P6\n<w> <h>\n255\n then raw RGB
  const m = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+255\s/);
  if (!m) throw new Error('not a P6 ppm: ' + path);
  const [w, h] = [+m[1], +m[2]];
  return { data: buf.subarray(m[0].length), w, h };
}

const prefix = process.argv[2];
const A = {}, out = {};
for (const k of ['window', 'screen']) {
  const p = readPPM(`${prefix}-${k}.ppm`);
  A[k] = p;
  await sharp(p.data, { raw: { width: p.w, height: p.h, channels: 3 } })
    .png().toFile(`${prefix}-${k}.png`);
  out[`energy_${k}`] = +(await contentEnergy(
    await sharp(p.data, { raw: { width: p.w, height: p.h, channels: 3 } }).png().toBuffer()
  )).toFixed(3);
}
let diff = 0;
const n = A.window.w * A.window.h;
for (let i = 0; i < A.window.data.length; i += 3) {
  const d = Math.abs(A.window.data[i] - A.screen.data[i])
          + Math.abs(A.window.data[i + 1] - A.screen.data[i + 1])
          + Math.abs(A.window.data[i + 2] - A.screen.data[i + 2]);
  if (d > 30) diff++;
}
out.divergent_pct = +(100 * diff / n).toFixed(1);
out.rect = `${A.window.w}x${A.window.h}`;
console.log(JSON.stringify(out, null, 1));
