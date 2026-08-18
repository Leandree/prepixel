// P1 — the action side of the web channel. Rung 1 for an element the CDP
// channel described, exactly as `PLATFORM_SCRIPT` is rung 1 for an element
// AT-SPI described: the platform's own action, not a synthesised pointer.
//
// The element is addressed by the handle `cdp_view.mjs` parked on the page
// (`window.__prepixel[h]`), so the action lands on the very node the view
// described. If the page navigated since the view was rendered, the global
// is gone and this reports `stale-handle` — the driver then falls to rung 2
// (pointer at the rect centre) rather than acting on a re-found element that
// might not be the same one. Guessing is the failure mode this whole ladder
// exists to avoid.
//
// Every op is dispatched as a real user event where the DOM allows it
// (element.click(), input events for value changes), because a page that
// listens for `input`/`change` must see them or the channel would "succeed"
// while the application learns nothing.
//
// Usage:
//   node cdp_act.mjs --endpoint http://localhost:9222 --handle 12
//                    --op click|set_value|toggle|scroll_to|focus
//                    [--value "132"] [--to true|false]
// Prints one JSON object: {ok, method, ...} or {ok:false, err}.
import { chromium } from 'playwright-core';

const argv = process.argv.slice(2);
const arg = (k, d) => {
  const i = argv.indexOf(k);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : d;
};

const ENDPOINT = arg('--endpoint', 'http://localhost:9222');
const HANDLE = Number(arg('--handle', '-1'));
const OP = arg('--op', 'click');
const VALUE = arg('--value', '');
const TO = arg('--to', '');
const URL_NEEDLE = arg('--url-needle', '');

function inPage([h, op, value, to]) {
  const els = window.__prepixel;
  if (!els) return { ok: false, err: 'stale-handle: no view on this page' };
  const el = els[h];
  if (!el) return { ok: false, err: `stale-handle: no element at ${h}` };
  if (!el.isConnected) {
    return { ok: false, err: 'stale-handle: element left the document' };
  }
  const fire = (name) => el.dispatchEvent(
    new Event(name, { bubbles: true, composed: true }));

  if (op === 'scroll_to') {
    el.scrollIntoView({ block: 'center', inline: 'nearest' });
    const r = el.getBoundingClientRect();
    return { ok: true, method: 'Element.scrollIntoView',
             rect: [Math.round(r.left), Math.round(r.top),
                    Math.round(r.width), Math.round(r.height)],
             scroll: [Math.round(scrollX), Math.round(scrollY)] };
  }
  if (op === 'focus') {
    el.focus();
    if (typeof el.setSelectionRange === 'function' &&
        typeof el.value === 'string') {
      try { el.setSelectionRange(el.value.length, el.value.length); }
      catch (e) { /* not a text-ish input */ }
    }
    return { ok: true, method: 'Element.focus',
             focused: document.activeElement === el };
  }
  if (op === 'set_value') {
    // A framework-backed field ignores a plain assignment: React and friends
    // install a value setter on the instance. Going through the prototype
    // setter is what makes the change visible to the page's own state.
    const proto = Object.getPrototypeOf(el);
    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
    el.focus();
    if (el.tagName === 'SELECT') {
      const want = String(value).toLowerCase();
      const opt = [...el.options].find(
        (o) => (o.textContent || '').trim().toLowerCase() === want ||
               String(o.value).toLowerCase() === want);
      if (!opt) return { ok: false, err: `no option matching "${value}"` };
      el.value = opt.value;
      fire('input'); fire('change');
      return { ok: true, method: 'Select.value', value: el.value };
    }
    if (el.isContentEditable) {
      el.textContent = value;
      fire('input');
      return { ok: true, method: 'contentEditable.textContent' };
    }
    if (desc && desc.set) desc.set.call(el, value);
    else el.value = value;
    fire('input'); fire('change');
    return { ok: true, method: 'HTMLInputElement.value setter',
             value: el.value };
  }
  if (op === 'toggle') {
    const want = to === 'true';
    const now = el.getAttribute('aria-checked') === 'true' ||
                el.checked === true;
    if (now === want) {
      return { ok: true, method: 'noop (already in the asked state)',
               noop: true };
    }
    el.click();
    const after = el.getAttribute('aria-checked') === 'true' ||
                  el.checked === true;
    return { ok: true, method: 'Element.click', reached: after };
  }
  // click
  el.click();
  return { ok: true, method: 'Element.click' };
}

async function main() {
  let browser;
  try {
    browser = await chromium.connectOverCDP(ENDPOINT, { timeout: 8000 });
  } catch (e) {
    console.log(JSON.stringify({ ok: false, err: 'connect: ' + e.message }));
    return;
  }
  try {
    const pages = [];
    for (const c of browser.contexts()) for (const p of c.pages()) pages.push(p);
    // Find the page the VIEW ran on, by asking which one is holding the
    // handle. The handles are self-identifying, so this needs no needle and
    // cannot drift from the view the way a second selection heuristic would.
    //
    // The earlier version picked by document.visibilityState, the same
    // mistake the view side made: in dev iteration 2 two pages reported
    // 'visible' and the stale one won. Here it would have been safe but
    // useless — the wrong page has no __prepixel, so the action would have
    // reported stale-handle and fallen to the pointer on every web click.
    let target = null;
    for (const p of pages) {
      try {
        const has = await p.evaluate(
          (h) => !!(window.__prepixel && window.__prepixel[h]), HANDLE);
        if (has) { target = p; break; }
      } catch (e) { /* target gone mid-enumeration */ }
    }
    if (!target) {
      for (const p of pages) {
        try {
          if (URL_NEEDLE && !p.url().includes(URL_NEEDLE)) continue;
          const vis = await p.evaluate(() => document.visibilityState);
          if (vis === 'visible') { target = p; break; }
        } catch (e) { /* target gone */ }
      }
    }
    if (!target) target = pages[0];
    if (!target) {
      console.log(JSON.stringify({ ok: false, err: 'no pages' }));
      return;
    }
    const res = await target.evaluate(inPage, [HANDLE, OP, VALUE, TO]);
    console.log(JSON.stringify(res));
  } catch (e) {
    console.log(JSON.stringify({ ok: false, err: e.message }));
  } finally {
    try { await browser.close(); } catch (e) { /* detach only */ }
  }
}

main();
