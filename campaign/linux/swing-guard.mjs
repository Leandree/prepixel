import sharp from 'sharp';
import fs from 'node:fs';
import { contentEnergy } from '/home/leandre/prepixel/src/coverage-guard.mjs';

const A = '/home/leandre/prepixel/campaign/results/artifacts/linux-atspi';
const buf = fs.readFileSync(`${A}/xcomp-swing-window.ppm`);
const m = buf.subarray(0, 64).toString('latin1').match(/^P6\s+(\d+)\s+(\d+)\s+255\s/);
const [w, h] = [+m[1], +m[2]];
const raw = buf.subarray(m[0].length);
await sharp(raw, { raw: { width: w, height: h, channels: 3 } }).png().toFile(`${A}/xcomp-swing-window.png`);
// suspect panel: desktop [65,455,890,220], window origin (60,40) -> window-rel [5,415]
const crop = await sharp(raw, { raw: { width: w, height: h, channels: 3 } })
  .extract({ left: 5, top: 415, width: 890, height: 220 }).png().toBuffer();
fs.writeFileSync(`${A}/guard-crop-swing-scope.png`, crop);
console.log('swing painted-panel energy:', (await contentEnergy(crop)).toFixed(3));
