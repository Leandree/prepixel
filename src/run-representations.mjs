// Experiment 1: same screen, three representations — sizes, tokens, capture latency.
import { launch, capturePage } from './capture.mjs';
import fs from 'node:fs';
import path from 'node:path';

const pages = [
  { label: 'testapp', url: 'file://' + path.resolve(import.meta.dirname, '../pages/testapp.html') },
  { label: 'article', url: 'file://' + path.resolve(import.meta.dirname, '../pages/article.html') },
];

const { browser, page, cdp } = await launch();
const results = [];
for (const p of pages) {
  try {
    await page.goto(p.url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(500);
    const { result } = await capturePage(page, cdp, p.label);
    results.push(result);
    console.log(JSON.stringify(result, null, 2));
  } catch (e) {
    console.error(`SKIP ${p.label}: ${e.message}`);
  }
}
fs.writeFileSync(path.resolve(import.meta.dirname, '../results/representations.json'), JSON.stringify(results, null, 2));
await browser.close();
