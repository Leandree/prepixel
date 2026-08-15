// Hardened distiller: runs IN-PAGE so it can hit-test. Prevents the two
// silent-divergence classes found on the occlusion probe:
//  (1) occlusion — an element listed as present while another element covers it
//      (a blind click would miss). We mark [occluded] via elementFromPoint.
//  (2) off-viewport leak — content the screen doesn't show. We drop or mark it.
//  (3) undeclared blind spot — pictorial content (canvas/img/video) the structure
//      cannot read. Emitting nothing for it makes an all-canvas screen look EMPTY
//      instead of opaque, so a router never learns it must fall back to pixels.
//      We declare each such region with its rect (found by the macOS campaign).
// Every emitted line reflects what is ACTUALLY visible & hittable, or is tagged.
export async function distillHardened(page) {
  return await page.evaluate(() => {
    const vw = innerWidth, vh = innerHeight;
    const out = [];
    const INTERACTIVE = new Set(['A','BUTTON','INPUT','SELECT','TEXTAREA','SUMMARY','LABEL']);
    const OPAQUE = new Set(['IMG','CANVAS','VIDEO','SVG','PICTURE','EMBED','OBJECT']);
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT);
    const seen = new Set();
    function visible(el){
      const s = getComputedStyle(el);
      if (s.visibility==='hidden'||s.display==='none'||parseFloat(s.opacity)===0) return false;
      return true;
    }
    function rectOf(node){
      if (node.nodeType===3){ const r=document.createRange(); r.selectNode(node); return r.getBoundingClientRect(); }
      return node.getBoundingClientRect();
    }
    let n;
    while ((n = walker.nextNode())) {
      if (n.nodeType===3){
        const t=n.textContent.trim(); if(!t) continue;
        const p=n.parentElement; if(!p||!visible(p)) continue;
        const r=rectOf(n); if(r.width===0||r.height===0) continue;
        const off = r.right<0||r.bottom<0||r.left>vw||r.top>vh;
        if (off) continue; // drop off-viewport text (was the OFFSCREEN leak)
        // occlusion: is the text's own parent the topmost at its center?
        const cx=Math.min(Math.max(r.left+r.width/2,0),vw-1), cy=Math.min(Math.max(r.top+r.height/2,0),vh-1);
        const top=document.elementFromPoint(cx,cy);
        const occ = top && !p.contains(top) && top!==p && !top.contains(p);
        out.push(`text ${Math.round(r.left)},${Math.round(r.top)},${Math.round(r.width)},${Math.round(r.height)} "${t}"${occ?' [occluded]':''}`);
      } else if (INTERACTIVE.has(n.tagName)) {
        if(!visible(n)) continue;
        const r=n.getBoundingClientRect(); if(r.width===0||r.height===0) continue;
        const off = r.right<0||r.bottom<0||r.left>vw||r.top>vh;
        if (off) continue;
        const cx=Math.min(Math.max(r.left+r.width/2,0),vw-1), cy=Math.min(Math.max(r.top+r.height/2,0),vh-1);
        const top=document.elementFromPoint(cx,cy);
        const hittable = top && (n===top || n.contains(top));
        const val = (n.value!==undefined && n.value!=='')?` value="${n.value}"`:'';
        out.push(`${n.tagName.toLowerCase()} ${Math.round(r.left)},${Math.round(r.top)},${Math.round(r.width)},${Math.round(r.height)}${n.id?' id='+n.id:''}${val}${hittable?'':' [occluded]'}`);
      } else if (OPAQUE.has(n.tagName.toUpperCase())) {
        if(!visible(n)) continue;
        const r=n.getBoundingClientRect(); if(r.width===0||r.height===0) continue;
        if (r.right<0||r.bottom<0||r.left>vw||r.top>vh) continue;
        const cx=Math.min(Math.max(r.left+r.width/2,0),vw-1), cy=Math.min(Math.max(r.top+r.height/2,0),vh-1);
        const top=document.elementFromPoint(cx,cy);
        const occ = top && n!==top && !n.contains(top);
        const label = n.getAttribute('alt') || n.getAttribute('aria-label') || '';
        out.push(`[pixels] ${n.tagName.toLowerCase()} ${Math.round(r.left)},${Math.round(r.top)},${Math.round(r.width)},${Math.round(r.height)}${label?' alt='+label:''}${occ?' [occluded]':''}`);
      }
    }
    return out.join('\n');
  });
}
