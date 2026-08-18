// P1 — the web channel of the per-window router (DEV-PHASE-PLAN §2).
//
// Emits the SAME records as the AT-SPI channel (`distill-osworld.py`): the
// same {kind, role, rect, label, value, states, line} shape and the same
// role vocabulary (`push-button`, `entry`, `check-box`, `page-tab`, …).
// That is the whole point of the router — a composed view must speak ONE
// grammar, or the model is reading two dialects and the comparison measures
// our formatting, not the channel. So HTML is mapped INTO the platform
// vocabulary here rather than a second vocabulary being introduced.
//
// What this channel gives that AT-SPI's OSWorld payload cannot:
//   - the value of a text field (the payload carries entry text in 0 of 1951
//     nodes — measured by probe_entry_text.py),
//   - content below the fold, with real page coordinates, so `scroll_to`
//     becomes implementable instead of a guess,
//   - toggle/checkbox state read from the DOM rather than inferred,
//   - lazily-rendered rows, which appear as soon as they exist in the DOM.
//
// The hardening is inherited from src/distill-hardened.mjs (occlusion via
// elementFromPoint, shadow DOM recursion, same-origin iframe recursion with
// cross-origin ones DECLARED as [pixels], background-image blind spots).
// Off-viewport nodes are NOT dropped here as they are there: for an agent
// that can scroll, "exists below the fold" is information, and it is marked
// [offscreen] so it can never be mistaken for something clickable now.
//
// Coordinates: on-screen records are translated by --offset into SCREEN
// coordinates so they compose with AT-SPI's frame. Offscreen records stay in
// PAGE coordinates — they have no screen position, and pretending otherwise
// is exactly the silent divergence the campaign exists to catch.
//
// Usage:
//   node cdp_view.mjs --endpoint http://localhost:9222 [--offset X,Y]
//                     [--url-needle S] [--max-offscreen N]
// Prints one JSON object on stdout: {ok, page:{…}, records:[…], pages:[…]}.
import { chromium } from 'playwright-core';

const argv = process.argv.slice(2);
const arg = (k, d) => {
  const i = argv.indexOf(k);
  return i >= 0 && i + 1 < argv.length ? argv[i + 1] : d;
};

const ENDPOINT = arg('--endpoint', 'http://localhost:9222');
const [OFFX, OFFY] = arg('--offset', '0,0').split(',').map(Number);
const URL_NEEDLE = arg('--url-needle', '');
// Title of the tab AT-SPI reports as selected. This is the authority on
// which page is on screen; visibilityState is not (see pickPage).
const TITLE_NEEDLE = arg('--title-needle', '');
const MAX_OFFSCREEN = Number(arg('--max-offscreen', '60'));
const CONNECT_TIMEOUT = Number(arg('--timeout-ms', '8000'));

// The in-page pass. Everything below runs inside the tab; it returns records,
// not text, so the Python side splices them into the AT-SPI record list and
// every downstream stage (ids, diff, act-guard, resolution ladder) is
// untouched by the channel swap.
function inPage(maxOffscreen) {
  const vw = innerWidth, vh = innerHeight;
  const recs = [];
  // Handles for the action side. Parking the elements on the page means
  // cdp_act.mjs acts on the very node the view described, instead of
  // re-finding it by a selector that may match something else by the time
  // the model answers. The array is rebuilt every step, which matches the
  // existing contract exactly: eN ids are valid for THIS step only. If the
  // page navigated in between, the global is gone and the action falls
  // honestly to the next rung rather than hitting the wrong element.
  const els = [];
  window.__prepixel = els;

  // HTML -> the AT-SPI role vocabulary. Kept deliberately small: a mapping
  // is generic, a per-site special case is not.
  const BY_TAG = {
    A: 'link', BUTTON: 'push-button', SELECT: 'combo-box',
    TEXTAREA: 'entry', SUMMARY: 'push-button', OPTION: 'list-item',
    H1: 'heading', H2: 'heading', H3: 'heading', H4: 'heading',
    H5: 'heading', H6: 'heading', LI: 'list-item', TD: 'table-cell',
    TH: 'table-cell', TR: 'table-row', IMG: 'image', CANVAS: 'canvas',
    VIDEO: 'video', SVG: 'image', PICTURE: 'image', EMBED: 'image',
    OBJECT: 'image', P: 'paragraph', LABEL: 'label',
  };
  const BY_INPUT_TYPE = {
    checkbox: 'check-box', radio: 'radio-button', submit: 'push-button',
    button: 'push-button', reset: 'push-button', image: 'push-button',
    range: 'slider', number: 'spin-button', search: 'entry',
    password: 'password-text', file: 'push-button',
  };
  // ARIA role -> platform role, for the roles a page actually declares.
  const BY_ARIA = {
    button: 'push-button', link: 'link', checkbox: 'check-box',
    radio: 'radio-button', textbox: 'entry', searchbox: 'entry',
    combobox: 'combo-box', listbox: 'list', option: 'list-item',
    tab: 'page-tab', tablist: 'page-tab-list', menuitem: 'menu-item',
    menuitemcheckbox: 'check-menu-item', menuitemradio: 'radio-menu-item',
    switch: 'toggle-button', slider: 'slider', spinbutton: 'spin-button',
    heading: 'heading', img: 'image', treeitem: 'tree-item',
    row: 'table-row', cell: 'table-cell', gridcell: 'table-cell',
    dialog: 'dialog', alert: 'alert', menu: 'menu', list: 'list',
  };
  const OPAQUE = new Set(['image', 'canvas', 'video']);
  // Elements whose accessible name WAS their own text. The text node is then
  // the same information a second time; the AT-SPI channel suppresses that
  // with its `consumed` set and the two channels must agree, or the composed
  // view is denser on the web half for no added meaning.
  const namedByText = new WeakSet();

  const roleOf = (el) => {
    const explicit = (el.getAttribute('role') || '').trim().toLowerCase();
    if (explicit && BY_ARIA[explicit]) return BY_ARIA[explicit];
    if (explicit) return explicit;                 // pass through, honestly
    const tag = el.tagName.toUpperCase();
    if (tag === 'INPUT') {
      const t = (el.getAttribute('type') || 'text').toLowerCase();
      return BY_INPUT_TYPE[t] || 'entry';
    }
    return BY_TAG[tag] || '';
  };

  const visible = (el) => {
    const s = getComputedStyle(el);
    return !(s.visibility === 'hidden' || s.display === 'none' ||
             parseFloat(s.opacity) === 0);
  };

  // Accessible name, in the order the platform would resolve it. Text
  // content is the LAST resort and only for roles whose name is their text.
  const NAME_FROM_TEXT = new Set(['link', 'push-button', 'heading',
                                  'list-item', 'table-cell', 'page-tab',
                                  'menu-item', 'label', 'paragraph']);
  function nameOf(el, role) {
    const al = el.getAttribute('aria-label');
    if (al && al.trim()) return al.trim();
    const lb = el.getAttribute('aria-labelledby');
    if (lb) {
      const t = lb.split(/\s+/).map((id) => {
        const n = document.getElementById(id);
        return n ? n.textContent.trim() : '';
      }).filter(Boolean).join(' ');
      if (t) return t;
    }
    if (el.labels && el.labels.length) {
      const t = [...el.labels].map((l) => l.textContent.trim())
        .filter(Boolean).join(' ');
      if (t) return t;
    }
    for (const a of ['alt', 'title', 'placeholder', 'name']) {
      const v = el.getAttribute(a);
      if (v && v.trim()) return v.trim();
    }
    if (NAME_FROM_TEXT.has(role)) {
      const t = (el.textContent || '').trim().replace(/\s+/g, ' ');
      if (t && t.length <= 200) { namedByText.add(el); return t; }
    }
    return '';
  }

  // The gap this channel exists to close: the value a field actually holds.
  function valueOf(el, role) {
    if (el.tagName === 'SELECT') {
      const o = el.selectedOptions && el.selectedOptions[0];
      return o ? (o.textContent || '').trim() : '';
    }
    if (el.isContentEditable) {
      return (el.textContent || '').trim().slice(0, 300);
    }
    if (typeof el.value === 'string' &&
        !['check-box', 'radio-button', 'push-button'].includes(role)) {
      return el.value;
    }
    const av = el.getAttribute('aria-valuenow');
    return av ? String(av) : '';
  }

  function statesOf(el, role) {
    const st = {};
    const ac = el.getAttribute('aria-checked');
    if (ac === 'true' || ac === 'false') st.checked = ac === 'true';
    else if (typeof el.checked === 'boolean' &&
             ['check-box', 'radio-button'].includes(role)) {
      st.checked = el.checked;
    }
    const ap = el.getAttribute('aria-pressed');
    if (ap === 'true') st.pressed = true;
    const ae = el.getAttribute('aria-expanded');
    if (ae === 'true') st.expanded = true;
    const as = el.getAttribute('aria-selected');
    if (as === 'true' || el.selected === true) st.selected = true;
    if (el === document.activeElement) st.focused = true;
    return st;
  }

  // Mirrors _state_str in distill-osworld.py exactly — same order, same
  // "checked:true/false" spelling — because the two channels render into one
  // view and a diff across a channel switch must not show phantom changes.
  function stateStr(st) {
    const parts = [];
    if ('checked' in st) parts.push('checked:' + (st.checked ? 'true' : 'false'));
    for (const k of ['pressed', 'selected', 'expanded', 'focused']) {
      if (st[k]) parts.push(k);
    }
    return parts.join(',');
  }
  const q = (s) => '"' + String(s).replace(/"/g, '""') + '"';

  const MAIN = { doc: document, dx: 0, dy: 0 };
  const rectOf = (n) => {
    if (n.nodeType === 3) {
      const r = document.createRange();
      r.selectNode(n);
      return r.getBoundingClientRect();
    }
    return n.getBoundingClientRect();
  };
  const onScreen = (r, ctx) => {
    const L = r.left + ctx.dx, T = r.top + ctx.dy;
    return r.width > 0 && r.height > 0 &&
           !(L + r.width < 0 || T + r.height < 0 || L > vw || T > vh);
  };
  const occluded = (n, r, ctx) => {
    const cx = Math.max(r.left + r.width / 2, 0);
    const cy = Math.max(r.top + r.height / 2, 0);
    const top = ctx.doc.elementFromPoint(cx, cy);
    if (!top) return false;
    const root = n.getRootNode();
    const host = root instanceof ShadowRoot ? root.host : null;
    return !(n === top || n.contains(top) || top.contains(n) ||
             (host && host.contains(top)));
  };

  let nOff = 0, nSkipped = 0;
  function push(n, role, ctx, kindHint) {
    const r = rectOf(n);
    if (r.width <= 0 || r.height <= 0) return;
    const on = onScreen(r, ctx);
    if (!on && nOff >= maxOffscreen) { nSkipped += 1; return; }
    // On-screen: viewport frame, translated later into screen coords.
    // Off-screen: PAGE coordinates — a scroll target, not a click target.
    const box = on
      ? [r.left + ctx.dx, r.top + ctx.dy, r.width, r.height]
      : [r.left + ctx.dx + scrollX, r.top + ctx.dy + scrollY,
         r.width, r.height];
    const rect = box.map(Math.round);
    const bs = rect.join(',');

    if (kindHint === 'text') {
      const t = (n.textContent || '').trim().replace(/\s+/g, ' ');
      if (!t) return;
      if (!on) nOff += 1;
      // The handle is the PARENT element: a text node cannot be scrolled to,
      // and text below the fold is exactly what a scroll target looks like.
      recs.push({ kind: on ? 'text' : 'offscreen', role: 'static', rect,
                  label: t, value: '', states: {}, src: 'cdp',
                  h: els.push(n.parentElement) - 1,
                  line: `${on ? '' : '[offscreen] '}text ${bs} ${q(t)}` });
      return;
    }
    const label = nameOf(n, role);
    if (OPAQUE.has(role)) {
      if (!on) return;         // a blind spot off-screen is not croppable
      recs.push({ kind: 'pixels', role, rect, label, value: '', states: {},
                  src: 'cdp', h: els.push(n) - 1,
                  line: `[pixels] ${role} ${bs}` +
                        (label ? ` alt=${label}` : '') });
      return;
    }
    const value = valueOf(n, role);
    const st = statesOf(n, role);
    const ss = stateStr(st);
    if (!label && !value && !ss && (rect[2] < 4 || rect[3] < 4)) return;
    if (!on) nOff += 1;
    const occ = on && occluded(n, r, ctx) ? ' [occluded]' : '';
    recs.push({
      kind: on ? 'element' : 'offscreen', role, rect, label, value,
      src: 'cdp', h: els.push(n) - 1,
      states: st,
      line: `${on ? '' : '[offscreen] '}${role} ${bs}` +
            (label ? ` ${q(label)}` : '') +
            (value ? ` value=${q(value)}` : '') +
            (ss ? ` state=${ss}` : '') + occ,
    });
  }

  const INLINE_TEXT_PARENT = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT',
                                      'TEMPLATE', 'TITLE']);
  function walk(root, ctx) {
    const w = ctx.doc.createTreeWalker(
      root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      if (n.nodeType === 3) {
        const p = n.parentElement;
        if (!p || INLINE_TEXT_PARENT.has(p.tagName) || !visible(p)) continue;
        // An ancestor that already took this exact text as its accessible
        // name carries the information; emitting it again is duplication.
        // Matching the AT-SPI rule literally — the text must EQUAL the
        // ancestor's name, so extra prose inside a big container survives.
        const t = (n.textContent || '').trim().replace(/\s+/g, ' ');
        let owned = false;
        for (let a = p; a && !owned; a = a.parentElement) {
          owned = namedByText.has(a) &&
            (a.textContent || '').trim().replace(/\s+/g, ' ') === t;
        }
        if (owned) continue;
        push(n, 'static', ctx, 'text');
        continue;
      }
      if (n.shadowRoot) walk(n.shadowRoot, ctx);
      const tag = n.tagName.toUpperCase();
      if (tag === 'IFRAME' || tag === 'FRAME') {
        if (!visible(n)) continue;
        let idoc = null;
        try { idoc = n.contentDocument; } catch (e) { /* cross-origin */ }
        const fr = n.getBoundingClientRect();
        if (idoc && idoc.body) {
          walk(idoc.body, { doc: idoc, dx: ctx.dx + fr.left,
                            dy: ctx.dy + fr.top });
        } else {
          push(n, 'image', ctx);       // declared, never silently dropped
        }
        continue;
      }
      if (!visible(n)) continue;
      const role = roleOf(n);
      if (!role) {
        // Background-image content with no text: a declared blind spot.
        const s = getComputedStyle(n);
        if (s.backgroundImage && s.backgroundImage !== 'none' &&
            !(n.textContent || '').trim()) {
          const r = n.getBoundingClientRect();
          if (r.width >= 24 && r.height >= 16) push(n, 'image', ctx);
        }
        continue;
      }
      push(n, role, ctx);
    }
  }

  walk(document.body, MAIN);
  return {
    records: recs,
    meta: { url: location.href, title: document.title,
            viewport: [vw, vh], scroll: [scrollX, scrollY],
            scrollHeight: document.documentElement.scrollHeight,
            visibility: document.visibilityState,
            focused: document.hasFocus(), offscreen_emitted: nOff,
            offscreen_skipped: nSkipped },
  };
}

async function main() {
  let browser;
  try {
    browser = await chromium.connectOverCDP(ENDPOINT,
                                            { timeout: CONNECT_TIMEOUT });
  } catch (e) {
    console.log(JSON.stringify({ ok: false, error: 'connect: ' + e.message }));
    return;
  }
  try {
    const pages = [];
    for (const ctx of browser.contexts()) for (const p of ctx.pages()) pages.push(p);
    if (!pages.length) {
      console.log(JSON.stringify({ ok: false, error: 'no pages' }));
      return;
    }
    // Which tab is on screen is a property of the tab, not a guess: exactly
    // one has visibilityState 'visible'. The needle is a fallback for the
    // case where several report visible (detached windows).
    const cands = [];
    for (const p of pages) {
      let vis = 'unknown', title = '', url = '';
      try {
        url = p.url();
        title = await p.title();
        vis = await p.evaluate(() => document.visibilityState);
      } catch (e) { /* target gone mid-enumeration */ }
      cands.push({ page: p, url, title, visible: vis === 'visible' });
    }
    // Page selection, most authoritative first. visibilityState alone was
    // WRONG: in dev iteration 2 two pages reported 'visible' at once and
    // this picked the stale one for ten straight steps while the model kept
    // saying the view did not match the tab it had opened. The AT-SPI tab
    // title is the ground truth for what is on screen, so it leads.
    const norm = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
    const needle = norm(TITLE_NEEDLE);
    let pick = null, how = '';
    if (needle) {
      pick = cands.find((c) => norm(c.title) === needle);
      how = pick ? 'title-exact' : '';
      if (!pick) {
        // Chrome decorates tab titles (" - Memory usage - 127 MB", audio
        // markers), so containment either way is the honest comparison.
        pick = cands.find((c) => {
          const t = norm(c.title);
          return t && (needle.includes(t) || t.includes(needle));
        });
        how = pick ? 'title-partial' : '';
      }
    }
    if (!pick && URL_NEEDLE) {
      pick = cands.find((c) => c.url.includes(URL_NEEDLE));
      how = pick ? 'url-needle' : '';
    }
    if (!pick) {
      pick = cands.find((c) => c.visible);
      how = pick ? 'visible' : '';
    }
    if (!pick) { pick = cands[0]; how = 'first'; }

    const { records, meta } = await pick.page.evaluate(inPage, MAX_OFFSCREEN);
    for (const r of records) {
      if (r.kind === 'offscreen') continue;      // page coords, not screen
      r.rect[0] += OFFX;
      r.rect[1] += OFFY;
      const bs = r.rect.join(',');
      r.line = r.line.replace(/^(\[pixels\] \S+|\S+) \S+/, (m, head) =>
        `${head} ${bs}`);
    }
    meta.picked_by = how;
    meta.tab_needle = TITLE_NEEDLE;
    // A partial or fallback match is not an error, but it must be visible:
    // silently reading the wrong tab is exactly the failure this replaced.
    meta.picked_title = pick.title;
    console.log(JSON.stringify({
      ok: true, meta, records,
      pages: cands.map((c) => ({ url: c.url, title: c.title,
                                 visible: c.visible })),
    }));
  } catch (e) {
    console.log(JSON.stringify({ ok: false, error: e.message }));
  } finally {
    try { await browser.close(); } catch (e) { /* detach only */ }
  }
}

main();
