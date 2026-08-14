# native — GTK4 render-tree tap (beyond the browser)

Taps a real GTK4 app (`gtk4-widget-factory`, GNOME Text Editor, …) at the exact
moment it submits its scene to the rendering pipeline: `gsk_renderer_render()`.
Proves the browser results hold on a native toolkit.

## Files

- `gsktap.c` — an `LD_PRELOAD` shim that intercepts `gsk_renderer_render` and
  serializes the frame's `GskRenderNode` tree with `gsk_render_node_serialize()`.
- `tap.gdb` — a gdb-based tap used instead when the shim can't interpose (Ubuntu
  builds libgtk with `-Bsymbolic`, which defeats `LD_PRELOAD` for intra-library
  calls — itself a finding: the interception point is fragile *by build accident*).
- `decode_glyphs.py` — recovers text from GSK text-node glyph IDs via a reverse cmap
  of the node's named font (+ Unicode NFKC + BiDi reorder for hard scripts).
- `samples/` — a captured render tree (`frame-0000.node`) and its exact re-render
  (`rerendered-frame.png`), i.e. the intercepted tree redrawn pixel-for-pixel.

## Run

```bash
gcc -shared -fPIC -O2 -o gsktap.so gsktap.c -ldl
# preferred (where -Bsymbolic doesn't block it):
GSK_TAP_DIR=/tmp/tap LD_PRELOAD=$PWD/gsktap.so gtk4-widget-factory
# fallback that always works:
GSK_RENDERER=cairo gdb -batch -x tap.gdb --args gtk4-widget-factory
# re-render a captured tree back to pixels (completeness proof):
gtk4-rendernode-tool render /tmp/tap/frame-0001.node out.png
# decode a text node's glyphs:
python3 decode_glyphs.py /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf "70 7, 82 8, 80 13"
```

## Findings

- **Completeness by construction** — the intercepted tree re-renders to the exact
  on-screen frame (text, widgets, and photos: texture nodes embed their bitmaps).
- **Text survives as glyph IDs**, recoverable per-font. With NFKC + BiDi reorder we
  recovered Latin, accents, CJK, emoji, and Arabic (`مرحبا`) exactly. Residual lossy
  tail (discretionary ligatures, complex mixed BiDi) is small and *detectable*.
- **Living screen** — a semantic inter-frame diff of an animating UI is ~1 KB/frame
  vs a flat ~1,366 tok/frame screenshot; idle ≈ 0.
- **Sizes** (widget-factory, 1332×751): ~340 KB/frame serialized, ~57% of it embedded
  texture payloads (stable identity, send once); the diff is what matters and it is
  tiny.
