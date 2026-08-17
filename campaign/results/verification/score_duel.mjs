// Independent accuracy scoring of the precision-cost-duel STRUCTURED condition.
// Answers 3 tasks/page purely by parsing the distilled view text, then checks
// against the harness truth (duel-cost.json). No truth leaks into the parser.
import fs from 'node:fs';
import path from 'node:path';

const DIR = 'C:/Users/Léandre/dev/prepixel/campaign/results/verification/duel-windows-replication';
const truthRows = JSON.parse(fs.readFileSync(path.join(DIR, 'duel-cost.json'), 'utf8'));
const STATUS = new Set(['Paid', 'Pending', 'Overdue', 'Draft']);

function answerFromView(view) {
  const lines = view.split('\n');
  const rows = [];
  let cur = null;
  for (const l of lines) {
    const q = l.match(/^text \S+ "([^"]*)"/);
    if (!q) continue;
    const t = q[1];
    if (/^#\d+$/.test(t)) { cur = { id: t, customer: null, total: null, status: null }; rows.push(cur); continue; }
    if (!cur) continue;
    const amt = t.match(/^€([\d.]+)$/);
    if (amt) { cur.total = parseFloat(amt[1]); continue; }
    if (STATUS.has(t)) { cur.status = t; continue; }
    if (t === 'Ship') continue;
    if (cur.customer === null) cur.customer = t;
  }
  const nRows = rows.length;
  const countPending = rows.filter(r => r.status === 'Pending').length;
  const maxCustomer = rows.reduce((a, b) => (b.total > a.total ? b : a)).customer;
  return { nRows, countPending, maxCustomer };
}

let pass = 0, total = 0;
const per = [];
for (const r of truthRows) {
  const view = fs.readFileSync(path.join(DIR, `page-${r.i}.view.txt`), 'utf8');
  const a = answerFromView(view);
  const checks = [
    ['nRows', a.nRows, r.truth.nRows],
    ['countPending', a.countPending, r.truth.countPending],
    ['maxCustomer', a.maxCustomer, r.truth.maxCustomer],
  ];
  const ok = checks.map(([, got, exp]) => (got === exp ? 1 : 0));
  const rowPass = ok.reduce((x, y) => x + y, 0);
  pass += rowPass; total += 3;
  per.push({ page: r.i, rowPass, checks: checks.map(([k, got, exp], j) => ({ k, got, exp, ok: !!ok[j] })) });
}

const first6 = per.slice(0, 6);
const p6pass = first6.reduce((a, r) => a + r.rowPass, 0);
console.log(JSON.stringify({
  first6_pages_score: `${p6pass}/${first6.length * 3}`,
  all20_pages_score: `${pass}/${total}`,
  failures: per.flatMap(p => p.checks.filter(c => !c.ok).map(c => ({ page: p.page, ...c }))),
}, null, 2));
