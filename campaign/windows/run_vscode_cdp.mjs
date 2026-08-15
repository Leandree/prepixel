// Cell: windows-vscode-cdp. VS Code (Electron) with --remote-debugging-port,
// isolated user-data-dir, throwaway workspace containing a sentinel file.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright-core';
import { distillHardened } from '../../src/distill-hardened.mjs';
import { imageTokens } from '../../src/image-tokens.mjs';

const ROOT = path.resolve(import.meta.dirname, '..', '..');
const ART = path.join(ROOT, 'campaign', 'results', 'artifacts', 'windows');
const textTokens = s => Math.ceil(s.length / 4);
const PORT = 9233;
const CODE = 'C:/Users/Léandre/AppData/Local/Programs/Microsoft VS Code/Code.exe';
const PROFILE = path.join(process.env.TEMP, 'ptap-vscode-prof');
const WS = path.join(process.env.TEMP, 'ptap-vscode-ws');
fs.mkdirSync(WS, { recursive: true });
const SENTINEL = 'ELECTRON-TAP-SENTINEL const answer = 42; // café 日本語';
fs.writeFileSync(path.join(WS, 'probe.js'), SENTINEL + '\n');

const out = { cell: 'windows-vscode-cdp' };
const proc = spawn(CODE, [
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
  '--disable-workspace-trust', '--skip-welcome', '--skip-release-notes',
  path.join(WS, 'probe.js'),
], { stdio: ['ignore', 'pipe', 'pipe'], detached: false });
let stderr = '';
proc.stderr.on('data', d => { stderr += d; });

let version = null;
for (let i = 0; i < 60; i++) {
  try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); version = await r.json(); break; }
  catch { await new Promise(r => setTimeout(r, 500)); }
}
if (!version) { console.log(JSON.stringify({ error: 'CDP never answered', stderr: stderr.slice(0, 300) })); process.exit(1); }
out.stack_signature = `:${PORT}/json/version -> ${version.Browser}`;
out.electron_warning = /remote-debugging-port/.test(stderr) ? stderr.split('\n').find(l => l.includes('remote-debugging-port'))?.slice(0, 160) : null;

const browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`);
await new Promise(r => setTimeout(r, 6000)); // let the workbench render
const pages = browser.contexts().flatMap(c => c.pages());
out.pages = pages.map(p => p.url().slice(0, 80));
const wb = pages.find(p => p.url().includes('workbench.html')) ?? pages[0];
if (!wb) { console.log(JSON.stringify({ error: 'no workbench page', ...out })); process.exit(1); }

let t0 = performance.now();
let view = await distillHardened(wb);
out.capture_latency_ms = +(performance.now() - t0).toFixed(1);
out.view_bytes = Buffer.byteLength(view);
out.view_tokens = textTokens(view);
fs.writeFileSync(path.join(ART, 'vscode-cdp-view.txt'), view);

const vp = wb.viewportSize();
out.viewport = vp;
try {
  const png = await wb.screenshot();
  fs.writeFileSync(path.join(ART, 'vscode-cdp-shot.png'), png);
  out.screenshot_tokens = imageTokens(vp?.width ?? 1280, vp?.height ?? 800);
} catch (e) { out.screenshot_error = String(e).slice(0, 120); }

out.t1 = { sentinel_visible: view.includes('ELECTRON-TAP-SENTINEL'),
           accents_ok: view.includes('café') && view.includes('日本語') };
const inter = view.split('\n').filter(l => /^(a|button|input|select|textarea|label) /.test(l));
out.t2 = { interactive_lines: inter.length,
           aria_labeled_sample: view.split('\n').filter(l => l.includes('Explorer') || l.includes('Search') || l.includes('probe.js')).slice(0, 6) };

// T3: type in the editor via CDP keyboard, re-distill
try {
  await wb.click('.monaco-editor .view-lines', { timeout: 5000 });
  await wb.keyboard.press('End');
  await wb.keyboard.type(' // LIVE-9z', { delay: 20 });
  await new Promise(r => setTimeout(r, 600));
  const v2 = await distillHardened(wb);
  out.t3 = { pass: v2.includes('LIVE-9z') };
} catch (e) { out.t3 = { pass: null, error: String(e).slice(0, 150) }; }

// idle
const a = await distillHardened(wb);
await new Promise(r => setTimeout(r, 1200));
const b = await distillHardened(wb);
out.idle_identical = a === b;

await browser.close();
proc.kill();
await new Promise(r => setTimeout(r, 500));
console.log(JSON.stringify(out, null, 1));
