// Precision-vs-pixels duel harness.
// For N randomized app pages, capture BOTH conditions:
//   - pixels: a real screenshot (exact dims -> official image token formula)
//   - structured: the hardened distilled view (exact bytes; text token estimate)
// Emits per-page cost (bytes + tokens) and a tasks+truth file for the accuracy run.
import { launch } from './capture.mjs';
import { distillHardened } from './distill-hardened.mjs';
import fs from 'node:fs';
import path from 'node:path';

const OUT = path.resolve(import.meta.dirname, '../results/duel');
fs.mkdirSync(OUT, { recursive: true });
fs.mkdirSync(path.join(OUT, 'shots'), { recursive: true });

// deterministic PRNG (seed varies per page index; no Math.random for reproducibility)
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
  // tasks + truth (unknowable in advance from the model's side; harness holds truth)
  const byStatus=s=>orders.filter(o=>o.status===s).length;
  const maxCust=orders.reduce((a,b)=>+a.total>+b.total?a:b).customer;
  const target=orders[Math.floor(rnd()*orders.length)];
  return {html,orders,truth:{
    nRows:n,
    countPending:byStatus('Pending'),
    maxCustomer:maxCust,
    shipTargetId:target.id, shipTargetCustomer:target.customer,
  }};
}

// official image token formulas (public, exact)
const imgTokensAnthropic=(w,h)=>Math.ceil((w*h)/750);
const textTokEst=s=>Math.ceil(s.length/4);

const N=20;
const { browser, page, cdp } = await launch();
const rows=[];
for(let i=0;i<N;i++){
  const {html,orders,truth}=genPage(i);
  const p=path.join(OUT,`page-${i}.html`);
  fs.writeFileSync(p,html);
  await page.goto('file://'+p,{waitUntil:'networkidle'});
  await page.waitForTimeout(150);
  const png=await page.screenshot();
  const shot=path.join(OUT,'shots',`page-${i}.png`);
  fs.writeFileSync(shot,png);
  const vp=page.viewportSize();
  const view=await distillHardened(page);
  fs.writeFileSync(path.join(OUT,`page-${i}.view.txt`),view);
  rows.push({
    i, viewport:vp,
    pixels:{ png_bytes:png.length, img_tokens:imgTokensAnthropic(vp.width,vp.height) },
    structured:{ view_bytes:Buffer.byteLength(view), view_chars:view.length, view_tokens_est:textTokEst(view) },
    truth,
  });
}
await browser.close();
fs.writeFileSync(path.join(OUT,'duel-cost.json'),JSON.stringify(rows,null,2));
// summary
const sX=rows.reduce((a,r)=>a+r.structured.view_tokens_est,0)/N;
const sP=rows.reduce((a,r)=>a+r.pixels.img_tokens,0)/N;
const bX=rows.reduce((a,r)=>a+r.structured.view_bytes,0)/N;
console.log(`N=${N} pages`);
console.log(`avg structured: ${bX.toFixed(0)} bytes, ${sX.toFixed(0)} tok (est)`);
console.log(`avg pixels: ${(rows.reduce((a,r)=>a+r.pixels.png_bytes,0)/N).toFixed(0)} png bytes, ${sP.toFixed(0)} img tok (exact formula)`);
console.log(`token ratio pixels/structured: ${(sP/sX).toFixed(1)}x`);
