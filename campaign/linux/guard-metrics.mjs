// Why does contentEnergy miss the qBittorrent speed graph, and is the signal
// recoverable? Three metrics per crop:
//   a) contentEnergy as shipped (64x64 downsample + modal-color deviation)
//   b) same metric at full resolution (no downsample)
//   c) edge fraction at full resolution (adjacent-pixel |delta|>24 on any channel)
import sharp from 'sharp';
import { contentEnergy } from '/home/leandre/prepixel/src/coverage-guard.mjs';

async function metrics(pngPath) {
  const asShipped = await contentEnergy(await sharp(pngPath).png().toBuffer());
  const { data, info } = await sharp(pngPath).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const { width: w, height: h } = info;
  // modal color, full res
  const hist = new Map();
  for (let i = 0; i < data.length; i += 3) {
    const k = (data[i] >> 4) << 8 | (data[i + 1] >> 4) << 4 | (data[i + 2] >> 4);
    hist.set(k, (hist.get(k) || 0) + 1);
  }
  let modeK = 0, modeC = -1;
  for (const [k, c] of hist) if (c > modeC) { modeC = c; modeK = k; }
  const mr = ((modeK >> 8) & 15) << 4, mg = ((modeK >> 4) & 15) << 4, mb = (modeK & 15) << 4;
  let ink = 0, edges = 0, pairs = 0;
  const px = (x, y, c) => data[(y * w + x) * 3 + c];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = (y * w + x) * 3;
    if (Math.abs(data[i] - mr) + Math.abs(data[i + 1] - mg) + Math.abs(data[i + 2] - mb) > 48) ink++;
    if (x + 1 < w) { pairs++;
      if (Math.abs(px(x,y,0)-px(x+1,y,0)) > 24 || Math.abs(px(x,y,1)-px(x+1,y,1)) > 24 || Math.abs(px(x,y,2)-px(x+1,y,2)) > 24) edges++; }
    if (y + 1 < h) { pairs++;
      if (Math.abs(px(x,y,0)-px(x,y+1,0)) > 24 || Math.abs(px(x,y,1)-px(x,y+1,1)) > 24 || Math.abs(px(x,y,2)-px(x,y+1,2)) > 24) edges++; }
  }
  return { energy_64x64_as_shipped: +asShipped.toFixed(4),
           energy_fullres: +(ink / (w * h)).toFixed(4),
           edge_fraction_fullres: +(edges / pairs).toFixed(4), w, h };
}

for (const p of process.argv.slice(2)) {
  console.log(p.split('/').pop(), JSON.stringify(await metrics(p)));
}
