// Hardened distiller: runs IN-PAGE so it can hit-test. Closes every known
// silent-divergence class found by the Linux + macOS campaigns:
//  (1) occlusion — an element listed as present while another element covers it
//      (a blind click would miss). We mark [occluded] via elementFromPoint.
//  (2) off-viewport leak — content the screen doesn't show. We drop it.
//  (3) undeclared pictorial blind spot — canvas/img/video regions the structure
//      cannot read are DECLARED with their rects (found by the macOS campaign).
//  (4) shadow DOM — text inside web components was invisible to the naive
//      TreeWalker; we now recurse into open shadow roots.
//  (5) iframes — neither walked nor declared before (worst case: invisible AND
//      unsignalled). Same-origin frames are recursed; cross-origin/blocked ones
//      are declared as [pixels] iframe rects.
//  (6) CSS background-image content (logos as backgrounds) — declared as
//      [pixels] bg rects when the element carries an image and no readable text.
//  (7) color-only semantics (status dots) — small colored elements with no text
//      are emitted as `mark x,y,w,h color` so a state carried purely by color
//      is not silently dropped. Style semantics beyond this remain a documented
//      loss (the view does not carry general styling).
// Every emitted line reflects what is ACTUALLY visible & hittable, or is tagged.
export async function distillHardened(page) {
  return await page.evaluate(() => {
    const vw = innerWidth, vh = innerHeight;
    const out = [];
    const INTERACTIVE = new Set(['A','BUTTON','INPUT','SELECT','TEXTAREA','SUMMARY','LABEL']);
    const OPAQUE = new Set(['IMG','CANVAS','VIDEO','SVG','PICTURE','EMBED','OBJECT']);

    function visible(el){
      const s = getComputedStyle(el);
      if (s.visibility==='hidden'||s.display==='none'||parseFloat(s.opacity)===0) return false;
      return true;
    }
    function rectOf(node){
      if (node.nodeType===3){ const r=document.createRange(); r.selectNode(node); return r.getBoundingClientRect(); }
      return node.getBoundingClientRect();
    }
    // ctx carries the coordinate frame: {doc, dx, dy} — iframe content is
    // hit-tested in ITS OWN document and translated into main-page coords.
    const MAIN = { doc: document, dx: 0, dy: 0 };
    function inViewport(r,ctx){ const L=r.left+ctx.dx, T=r.top+ctx.dy; return !(L+r.width<0||T+r.height<0||L>vw||T>vh) && r.width>0 && r.height>0; }
    function topAt(r,ctx){
      const cx=Math.max(r.left+r.width/2,0), cy=Math.max(r.top+r.height/2,0);
      return ctx.doc.elementFromPoint(cx,cy);
    }
    const px = (r,ctx)=>`${Math.round(r.left+ctx.dx)},${Math.round(r.top+ctx.dy)},${Math.round(r.width)},${Math.round(r.height)}`;

    function emitText(n,ctx){
      const t=n.textContent.trim(); if(!t) return;
      const p=n.parentElement; if(!p||!visible(p)) return;
      const r=rectOf(n); if(!inViewport(r,ctx)) return;
      const top=topAt(r,ctx);
      // note: elementFromPoint retargets into shadow hosts; contains() on the host covers it
      const host = p.getRootNode() instanceof ShadowRoot ? p.getRootNode().host : null;
      const occ = top && !p.contains(top) && top!==p && !top.contains(p) && top!==host && !(host&&host.contains(top));
      out.push(`text ${px(r,ctx)} "${t}"${occ?' [occluded]':''}`);
    }
    function emitInteractive(n,ctx){
      if(!visible(n)) return;
      const r=n.getBoundingClientRect(); if(!inViewport(r,ctx)) return;
      const top=topAt(r,ctx);
      const hittable = top && (n===top || n.contains(top) || (n.getRootNode() instanceof ShadowRoot && n.getRootNode().host.contains(top)));
      const val = (n.value!==undefined && n.value!=='')?` value="${n.value}"`:'';
      out.push(`${n.tagName.toLowerCase()} ${px(r,ctx)}${n.id?' id='+n.id:''}${val}${hittable?'':' [occluded]'}`);
    }
    function emitOpaque(n, kind, label, ctx){
      const r=n.getBoundingClientRect(); if(!inViewport(r,ctx)) return;
      const top=topAt(r,ctx);
      const occ = top && n!==top && !n.contains(top);
      out.push(`[pixels] ${kind} ${px(r,ctx)}${label?' alt='+label:''}${occ?' [occluded]':''}`);
    }

    function walk(root, ctx){
      const walker = (ctx.doc).createTreeWalker(root, NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT);
      let n;
      while ((n = walker.nextNode())) {
        if (n.nodeType===3){ emitText(n,ctx); continue; }
        const tag = n.tagName.toUpperCase();
        // (4) recurse into open shadow roots
        if (n.shadowRoot) walk(n.shadowRoot, ctx);
        if (INTERACTIVE.has(tag)) { emitInteractive(n,ctx); continue; }
        if (OPAQUE.has(tag)) { if(visible(n)) emitOpaque(n, n.tagName.toLowerCase(), n.getAttribute('alt')||n.getAttribute('aria-label')||'', ctx); continue; }
        // (5) iframes: recurse same-origin, declare otherwise
        if (tag==='IFRAME'||tag==='FRAME'){
          if(!visible(n)) continue;
          let idoc=null; try{ idoc=n.contentDocument; }catch(e){}
          const fr=n.getBoundingClientRect();
          if (idoc && idoc.body) walk(idoc.body, {doc:idoc, dx:ctx.dx+fr.left, dy:ctx.dy+fr.top}); // same-origin: readable, translated
          else emitOpaque(n,'iframe', n.getAttribute('title')||n.src||'', ctx); // cross-origin: declared
          continue;
        }
        if (!visible(n)) continue;
        const s=getComputedStyle(n);
        // (6) background-image content with no readable text -> declared blind spot
        if (s.backgroundImage && s.backgroundImage!=='none' && n.textContent.trim()===''){
          const r=n.getBoundingClientRect();
          if (inViewport(r,ctx) && r.width>=24 && r.height>=16)
            emitOpaque(n,'bg', n.getAttribute('aria-label')||n.getAttribute('role')||'', ctx);
          continue;
        }
        // (7) color-only semantics: small colored element, no text -> emit the color
        if (n.childElementCount===0 && n.textContent.trim()===''){
          const r=n.getBoundingClientRect();
          if (r.width>0 && r.width<=32 && r.height>0 && r.height<=32 && inViewport(r,ctx)){
            const bg=s.backgroundColor;
            if (bg && bg!=='rgba(0, 0, 0, 0)' && bg!=='transparent')
              out.push(`mark ${px(r,ctx)} ${bg}`);
          }
        }
      }
    }
    walk(document.body, MAIN);
    return out.join('\n');
  });
}
