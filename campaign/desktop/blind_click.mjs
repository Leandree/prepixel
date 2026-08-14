import { chromium } from 'playwright-core';
import { execSync } from 'node:child_process';
const b = await chromium.connectOverCDP('http://127.0.0.1:9223');
const ctx = b.contexts()[0]; const page = ctx.pages().find(p=>p.url().includes('clicktarget')) || ctx.pages()[0];
await page.bringToFront();
// STRUCTURED channel only: element box + this window's on-screen origin + chrome height
const info = await page.evaluate(()=>{
  const r=document.getElementById('b').getBoundingClientRect();
  return { x:r.x, y:r.y, w:r.width, h:r.height,
           screenX:window.screenX, screenY:window.screenY,
           chromeTop: window.outerHeight-window.innerHeight };
});
const sx = Math.round(info.screenX + info.x + info.w/2);
const sy = Math.round(info.screenY + info.chromeTop + info.y + info.h/2);
console.log(`element box(page)=${info.x},${info.y},${info.w},${info.h} screenXY=${info.screenX},${info.screenY} chromeTop=${info.chromeTop} -> screen ${sx},${sy}`);
const before = await page.evaluate(()=>document.getElementById('s').textContent);
execSync(`DISPLAY=:7 xdotool mousemove ${sx} ${sy} click 1`);
await new Promise(r=>setTimeout(r,500));
const after = await page.evaluate(()=>document.getElementById('s').textContent);
console.log(`state before=${before} after=${after}`);
console.log(after==='CLICKED' ? 'PASS: structured coords drove a real OS click onto the target' : 'MISS');
await b.close();
