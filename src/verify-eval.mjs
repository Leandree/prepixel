// Mechanically verifies the model's answers produced from the structured view alone.
// Clicks are dispatched at RAW COORDINATES (like a pixel agent would act) via CDP
// Input events — no selectors — then the resulting DOM state is checked.
import { launch } from './capture.mjs';
import fs from 'node:fs';
import path from 'node:path';

const HERE = import.meta.dirname;
const truth = JSON.parse(fs.readFileSync(path.join(HERE, '../results/eval-truth.json')));
const ans = JSON.parse(fs.readFileSync(path.join(HERE, '../results/eval-answers.json')));

const { browser, page, cdp } = await launch();
await page.goto('file://' + path.join(HERE, '../pages/eval.html'), { waitUntil: 'networkidle' });
await page.waitForTimeout(300);

const click = async ({ x, y }) => {
  for (const type of ['mousePressed', 'mouseReleased'])
    await cdp.send('Input.dispatchMouseEvent', { type, x, y, button: 'left', clickCount: 1 });
  await page.waitForTimeout(150);
};

const res = {};
res.t1 = { got: ans.t1, want: truth.nPending, pass: ans.t1 === truth.nPending };
res.t2 = { got: ans.t2, want: truth.maxCustomer, pass: ans.t2 === truth.maxCustomer };

// T3: click at raw coords, check the RIGHT row got shipped
await click(ans.t3);
const shipped = await page.evaluate(() =>
  [...document.querySelectorAll('#rows tr')].filter(tr => tr.querySelector('.badge').textContent === 'Shipped')
    .map(tr => tr.querySelector('.ship')?.dataset.id ?? tr.cells[0].textContent.replace('#', '')));
res.t3 = { clicked: ans.t3, shippedRows: shipped, want: String(truth.shipTarget), pass: shipped.length === 1 && shipped[0] === String(truth.shipTarget) };

// T4: click input at coords, type, click submit at coords, check new row
await click(ans.t4.clickInput);
await page.keyboard.type(ans.t4.text, { delay: 10 });
await click(ans.t4.clickSubmit);
await page.waitForTimeout(200);
const lastRow = await page.evaluate(() => {
  const tr = document.querySelector('#rows tr:last-child');
  return tr ? { customer: tr.cells[1].textContent, n: document.querySelectorAll('#rows tr').length } : null;
});
res.t4 = { got: lastRow, pass: lastRow?.customer === 'Nova Corp' && lastRow.n === truth.orders.length + 1 };

await browser.close();
res.score = ['t1','t2','t3','t4'].filter(k => res[k].pass).length + '/4';
fs.writeFileSync(path.join(HERE, '../results/eval-report.json'), JSON.stringify(res, null, 2));
console.log(JSON.stringify(res, null, 2));
