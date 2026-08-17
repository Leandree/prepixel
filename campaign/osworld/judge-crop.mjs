// Thin CLI over the SHIPPED coverage-guard decision path, so the OSWorld
// campaign's guard verdicts are byte-identical to the desktop campaign's.
// Usage: node judge-crop.mjs <screenshot.png> <x> <y> <w> <h>
// Prints judgeCrop's JSON ({energy, edge, silentRisk}) on stdout.
// KNOWN DEVIATION (documented in the returns file): the crop comes from the
// VM's full-screen screenshot, not a per-window surface — OSWorld's obs API
// exposes no per-window capture. Single-app fullscreen VM ≈ equivalent.
import sharp from '/home/leandre/prepixel/node_modules/sharp/lib/index.js';
import { judgeCrop } from '/home/leandre/prepixel/src/coverage-guard.mjs';

const [png, x, y, w, h] = process.argv.slice(2);
const crop = await sharp(png)
  .extract({ left: +x, top: +y, width: +w, height: +h })
  .png().toBuffer();
console.log(JSON.stringify(await judgeCrop(crop)));
