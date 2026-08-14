// Visual-content eval: the structured view declares opaque regions; the agent
// pulls TARGETED CROPS of those rects and interprets them with vision, paying
// tokens only for the declared rectangles. Random content, mechanical check.
import { launch, capturePage, imgTokensClaude } from './capture.mjs';
import fs from 'node:fs';
import path from 'node:path';

const HERE = import.meta.dirname;
const RES = path.join(HERE, '../results');
const R = (arr) => arr[Math.floor(Math.random() * arr.length)];
const COLORS = { red: '#d62828', blue: '#1d4ed8', green: '#15803d', orange: '#ea8004', purple: '#7c3aed' };

// --- random pictorial content (unknowable in advance) -----------------------
// Image: N shapes, random kind+color, laid out on a grid
const nShapes = 2 + Math.floor(Math.random() * 4); // 2..5
const shapes = Array.from({ length: nShapes }, () => ({ kind: R(['circle', 'square', 'triangle']), color: R(Object.keys(COLORS)) }));
const svgShape = (s, i) => {
  const cx = 45 + i * 62, cy = 60, c = COLORS[s.color];
  if (s.kind === 'circle') return `<circle cx="${cx}" cy="${cy}" r="24" fill="${c}"/>`;
  if (s.kind === 'square') return `<rect x="${cx - 22}" y="${cy - 22}" width="44" height="44" fill="${c}"/>`;
  return `<polygon points="${cx},${cy - 26} ${cx - 25},${cy + 22} ${cx + 25},${cy + 22}" fill="${c}"/>`;
};
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="360" height="120"><rect width="360" height="120" fill="#f4f1ea"/>${shapes.map(svgShape).join('')}</svg>`;

// Canvas "game HUD": random score + random number of invaders
const score = 1000 + Math.floor(Math.random() * 9000);
const invaders = 2 + Math.floor(Math.random() * 5); // 2..6

const html = `<!doctype html><html><head><meta charset="utf-8"><title>Mixed content</title></head>
<body style="font-family:sans-serif;margin:20px">
  <h2>Rapport hebdo</h2>
  <p>Statut du pipeline : <strong>OK</strong> — dernier build 14:02</p>
  <h3>Illustration produit</h3>
  <img id="illu" width="360" height="120" src="data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}" alt="">
  <h3>Mini-jeu (canvas)</h3>
  <canvas id="game" width="420" height="140"></canvas>
  <script>
    const ctx = document.getElementById('game').getContext('2d');
    ctx.fillStyle = '#0b0b1a'; ctx.fillRect(0,0,420,140);
    ctx.fillStyle = '#0f0'; ctx.font = 'bold 22px monospace';
    ctx.fillText('SCORE ${score}', 12, 32);
    ctx.fillStyle = '#e6e6e6';
    for (let i = 0; i < ${invaders}; i++) { const x = 20 + i * 55; ctx.fillRect(x, 80, 34, 24); ctx.fillRect(x+8, 70, 18, 10); }
  </script>
</body></html>`;
fs.writeFileSync(path.join(HERE, '../pages/eval-visual.html'), html);
fs.writeFileSync(path.join(RES, 'eval-visual-truth.json'), JSON.stringify({ shapes, nShapes, score, invaders }, null, 2));

// --- capture: structured view + targeted crops of declared opaque rects -----
const { browser, page, cdp } = await launch();
await page.goto('file://' + path.join(HERE, '../pages/eval-visual.html'), { waitUntil: 'networkidle' });
await page.waitForTimeout(400);
const { result, domDistilled } = await capturePage(page, cdp, 'eval-visual');

const opaque = domDistilled.split('\n').filter(l => l.startsWith('[pixels]'));
let cropTokens = 0;
for (const [i, line] of opaque.entries()) {
  const [x, y, w, h] = line.split(' ')[2].split(',').map(Number);
  await page.screenshot({ path: path.join(RES, `eval-visual-crop${i}.png`), clip: { x, y, width: w, height: h } });
  cropTokens += imgTokensClaude(w, h);
}
await browser.close();

console.log('================= STRUCTURED VIEW (only input, + crops of [pixels] rects) =================');
console.log(domDistilled);
console.log('================= TOKEN ACCOUNTING =================');
console.log(`full screenshot: ${result.screenshot.tokensClaude} tok`);
console.log(`structured view: ${result.domSnapshot.tokensDistilled} tok + targeted crops: ${cropTokens} tok = ${result.domSnapshot.tokensDistilled + cropTokens} tok`);
console.log('================= TASKS (answer from view + crops ONLY) =================');
console.log('V1. Image "Illustration produit": how many shapes, and list each as kind+color in order left→right?');
console.log('V2. Canvas "Mini-jeu": what is the SCORE displayed?');
console.log('V3. Canvas "Mini-jeu": how many invaders (white blocky sprites) are shown?');
console.log('Write results/eval-visual-answers.json: {"v1": [{"kind":"circle","color":"red"},...], "v2": 1234, "v3": n}');
