// Precision-vs-pixels duel — macOS port of src/duel.mjs.
// Same deterministic page generator (mulberry32, same seeds) => byte-identical pages
// to the Linux cell, so the two OS cells are directly comparable page-by-page.
// Differences vs Linux: connects to a real macOS Chrome over CDP and pins the
// viewport to 1280x800 @ deviceScaleFactor=1 via Emulation.setDeviceMetricsOverride
// so the screenshot token count matches the Linux condition exactly (Retina would
// otherwise quadruple it — reported separately in the cell notes).
import { chromium } from 'playwright-core';
import { distillHardened } from '/Users/leandre/dev/prepixel/src/distill-hardened.mjs';
import fs from 'node:fs';
import path from 'node:path';

const OUT = '/Users/leandre/dev/prepixel/results/duel-macos';
fs.mkdirSync(path.join(OUT, 'shots'), { recursive: true });

function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
const SYL=['ba','re','mo','lu','ti','ka','ve','so','ni','du','fa','ro','pi','sa','mi'];
const SUF=['SARL','SA','& Co','SAS','GmbH','Ltd'];
const STAT=['Paid','Pending','Overdue','Draft'];

function genPage(i){
  const rnd=mulberry32(1000+i*97);
  const pick=a=>a[Math.floor(rnd()*a.length)];
  const cap=s=>s[0].toUpperCase()+s.slice(1);
  const n=5+Math.floor(rnd()*6);
  const orders=Array.from({length:n},(_,k)=>({
    id:3000+i*100+k,
    customer:cap(pick(SYL)+pick(SYL)+pick(SYL))+' '+pick(SUF),
    total:(rnd()*5000+20).toFixed(2),
    status:pick(STAT),
  }));
  const rows=orders.map(o=>`<tr><td>#${o.id}</td><td>${o.customer}</td><td>€${o.total}</td><td><span class="badge">${o.status}</span></td><td><button data-id="${o.id}" class="ship">Ship</button></td></tr>`).join('');
  const html=`<!doctype html><html><head><meta charset="utf-8"><title>Orders ${i}</title>
  <style>body{font-family:system-ui,sans-serif;margin:0}main{padding:20px}table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:6px 10px;border-bottom:1px solid #e2e8f0}.badge{padding:2px 8px;border-radius:10px;background:#eef}button{padding:6px 10px}</style></head>
  <body><main><h1>Orders</h1><p>${n} open orders</p><table><thead><tr><th>Order</th><th>Customer</th><th>Total</th><th>Status</th><th></th></tr></thead><tbody>${rows}</tbody></table>
  <form><input id="cust" placeholder="Customer" aria-label="Customer"><button id="add" type="button">Add order</button></form></main></body></html>`;
  const byStatus=s=>orders.filter(o=>o.status===s).length;
  const maxCust=orders.reduce((a,b)=>+a.total>+b.total?a:b).customer;
  const target=orders[Math.floor(rnd()*orders.length)];
  return {html,orders,truth:{
    nRows:n, countPending:byStatus('Pending'), maxCustomer:maxCust,
    shipTargetId:target.id, shipTargetCustomer:target.customer,
  }};
}

const imgTokensAnthropic=(w,h)=>Math.ceil((w*h)/750);
const textTokEst=s=>Math.ceil(s.length/4);

const N=20, VW=1280, VH=800;
const browser = await chromium.connectOverCDP('http://127.0.0.1:9223');
const ctx = browser.contexts()[0];
const page = ctx.pages()[0] ?? await ctx.newPage();
const cdp = await ctx.newCDPSession(page);
// pin CSS viewport AND device scale so the pixel condition equals the Linux one
await cdp.send('Emulation.setDeviceMetricsOverride', { width: VW, height: VH, deviceScaleFactor: 1, mobile: false });

const rows=[];
for(let i=0;i<N;i++){
  const {html,truth}=genPage(i);
  const p=path.join(OUT,`page-${i}.html`);
  fs.writeFileSync(p,html);
  await page.goto('file://'+p);
  await page.waitForTimeout(120);
  const shotB64 = (await cdp.send('Page.captureScreenshot',{format:'png'})).data;
  const png = Buffer.from(shotB64,'base64');
  fs.writeFileSync(path.join(OUT,'shots',`page-${i}.png`),png);
  const view = await distillHardened(page);
  fs.writeFileSync(path.join(OUT,`page-${i}.view.txt`),view);
  rows.push({
    i, viewport:{width:VW,height:VH},
    pixels:{ png_bytes:png.length, img_tokens:imgTokensAnthropic(VW,VH),
             img_tokens_retina:imgTokensAnthropic(VW*2,VH*2) },
    structured:{ view_bytes:Buffer.byteLength(view), view_tokens_est:textTokEst(view) },
    truth,
  });
}
await cdp.send('Emulation.clearDeviceMetricsOverride');
fs.writeFileSync(path.join(OUT,'duel-cost.json'),JSON.stringify(rows,null,2));

const avg=f=>rows.reduce((a,r)=>a+f(r),0)/N;
const sX=avg(r=>r.structured.view_tokens_est), sP=avg(r=>r.pixels.img_tokens);
const bX=avg(r=>r.structured.view_bytes), bP=avg(r=>r.pixels.png_bytes);
const summary={
  n:N, viewport:{width:VW,height:VH},
  structured:{avg_bytes:+bX.toFixed(0), avg_tokens_est:+sX.toFixed(0)},
  pixels:{avg_png_bytes:+bP.toFixed(0), img_tokens:sP, img_tokens_retina:avg(r=>r.pixels.img_tokens_retina)},
  ratio_tokens:+(sP/sX).toFixed(2), ratio_bytes:+(bP/bX).toFixed(1),
  ratio_tokens_retina:+(avg(r=>r.pixels.img_tokens_retina)/sX).toFixed(2),
};
fs.writeFileSync(path.join(OUT,'duel-summary.json'),JSON.stringify(summary,null,2));
console.log(JSON.stringify(summary,null,1));
