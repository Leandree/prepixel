// Generates a randomized orders page (data unknowable in advance), captures the
// distilled structured view, and prints TASKS. The model answers from the view
// ALONE (no screenshot); verify-eval.mjs then checks answers mechanically.
import { launch, capturePage } from './capture.mjs';
import fs from 'node:fs';
import path from 'node:path';

const HERE = import.meta.dirname;
const R = (arr) => arr[Math.floor(Math.random() * arr.length)];
const syll = ['ba','re','mo','lu','ti','ka','ve','so','ni','du','fa','ro'];
const name = () => (R(syll) + R(syll) + R(syll)).replace(/^./, c => c.toUpperCase()) + ' ' + R(['SARL', 'SA', '& Co', 'SAS', 'GmbH']);
const nOrders = 5 + Math.floor(Math.random() * 4);
const orders = Array.from({ length: nOrders }, (_, i) => ({
  id: 2000 + i,
  customer: name(),
  total: (Math.random() * 4000 + 50).toFixed(2),
  status: R(['Paid', 'Pending', 'Overdue']),
}));

const rows = orders.map(o =>
  `<tr><td>#${o.id}</td><td>${o.customer}</td><td>€${o.total}</td><td><span class="badge">${o.status}</span></td><td><button data-id="${o.id}" class="ship">Ship</button></td></tr>`).join('\n');

const html = fs.readFileSync(path.join(HERE, '../pages/testapp.html'), 'utf8')
  .replace(/<tbody id="rows">[\s\S]*?<\/tbody>/, `<tbody id="rows">\n${rows}\n</tbody>`)
  .replace('3 open orders', `${nOrders} open orders`);
fs.writeFileSync(path.join(HERE, '../pages/eval.html'), html);

// pick task targets AFTER generation
const shipTarget = R(orders.filter(o => o.status !== 'Paid'));
const sumStatus = 'Pending';
const truth = {
  orders, shipTarget: shipTarget.id, shipTargetCustomer: shipTarget.customer,
  nPending: orders.filter(o => o.status === sumStatus).length,
  maxCustomer: orders.reduce((a, b) => +a.total > +b.total ? a : b).customer,
};
fs.writeFileSync(path.join(HERE, '../results/eval-truth.json'), JSON.stringify(truth, null, 2));

const { browser, page, cdp } = await launch();
await page.goto('file://' + path.join(HERE, '../pages/eval.html'), { waitUntil: 'networkidle' });
await page.waitForTimeout(300);
const { domDistilled } = await capturePage(page, cdp, 'eval');
await browser.close();

console.log('================= STRUCTURED VIEW (the ONLY thing the model sees) =================');
console.log(domDistilled);
console.log('================= TASKS =================');
console.log(`T1. How many orders have status "${sumStatus}"? (answer: integer)`);
console.log(`T2. Which customer has the LARGEST order total? (answer: exact customer string)`);
console.log(`T3. CLICK the "Ship" button of the order belonging to "${shipTarget.customer}". (answer: x,y coordinates)`);
console.log(`T4. Type "Nova Corp" in the customer field and submit the form. (answer: two clicks x,y + where to type)`);
console.log('Write answers to results/eval-answers.json as:');
console.log('{"t1": n, "t2": "customer", "t3": {"x":..,"y":..}, "t4": {"clickInput":{"x":..,"y":..},"text":"Nova Corp","clickSubmit":{"x":..,"y":..}}}');
