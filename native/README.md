
## Native probe (GTK4) — beyond the browser

`native/` taps a real GTK4 app (`gtk4-widget-factory`) at the exact moment it submits its scene to the rendering pipeline: `gsk_renderer_render()`. Findings, mirroring the browser results on a native toolkit:

- **Interception friction is real**: Ubuntu builds libgtk with `-Bsymbolic`, so the LD_PRELOAD shim (`gsktap.c`) cannot interpose intra-library calls — the capture uses a gdb-based tap (`tap.gdb`) instead. Production would use a toolkit hook or patched lib; the 1990s off-screen-model fragility story, replayed in miniature.
- **The captured tree is the whole screen, by construction**: `gtk4-rendernode-tool render` re-renders the intercepted tree into the exact on-screen frame (`native/samples/rerendered-frame.png`) — text, widgets, and even photos (texture nodes embed their bitmaps).
- **Text survives as glyph IDs** (`glyphs: 70 7, 82 8, ...`, post-shaping): recoverable with a one-time reverse-cmap per font (`decode_glyphs.py` decodes the samples to `"comboboxentry"`, `"Click icon to change mode"`). Ligatures/complex scripts would be lossy — the predicted "glyph problem", confirmed and mostly solvable.
- **Sizes** (widget-factory, 1332×751): 339 KB/frame serialized, of which 198 KB is embedded texture payloads (sendable once — stable identity) and 142 KB verbose structure (pre-distillation). **Inter-frame diffs: ~1–2 KB** while an animation runs — the same event-shaped economics as the browser probe.
