# Linux findings (reference cell, run by Claude in a headless sandbox)

Ran as the worked example for the Windows/macOS agents. Environment: Ubuntu 24.04,
GTK 4.14, Qt 5.15, LibreOffice, Chromium — **headless** (broadway, no login seat).
Six cells produced; see `results/*.json` and the aggregated `MATRIX.md`.

## What worked, and the shape of it

- **LibreOffice via UNO (object model)** — the strongest positive. Reading the
  document is 21 tokens vs ~1366 for a page screenshot (~65×), text is real strings
  with accents intact, no glyph decoding. This is the Linux twin of Word-via-COM:
  when an app exposes its document model, you don't need the render tree at all.
- **GTK4 render-tree tap** on the real GNOME Text Editor — the known file content
  came back exactly ("The quick brown fox 12345", "RENDER-TAP-SENTINEL-XYZ") by
  decoding GSK text-node glyph IDs, and the intercepted tree re-renders to the exact
  window (artifact PNG). Completeness proven, not asserted. Caveat carried over: text
  is glyph IDs (one reverse-cmap table per font); ligatures/complex scripts would be
  lossy.
- **Chromium/CDP** — the highest-*coverage* channel because the same method covers
  the entire Chromium/Electron slice of the desktop across all three OSes. Numbers
  from phase 1 (308 vs 1366 tok, 4.4×; 14× on a living screen; evals 4/4 and 3/3).

## What did NOT work — and why that's the point

- **AT-SPI (accessibility API)**: `blocked` here — `org.a11y.Bus` isn't activatable
  without a real session; headless/CI can't get it. Not a property of AT-SPI (it's
  the standard channel on a real desktop), but a genuine *routing* datum: an agent
  running headless can't rely on it. The macOS/Linux desktop agents will exercise it
  properly.
- **Qt render tap**: `unavailable` by architecture — Qt has no public
  `gsk_render_node_serialize()` analog; QWidget paints to a backing store, QML's
  scene graph is GPU-internal. The only structured channel for Qt is AT-SPI. This is
  the central caveat of the whole thesis in miniature: **the render-tap is
  toolkit-dependent, not universal.**
- **All-canvas "game"**: `unavailable` but **explicit** — the view emits exactly
  `[pixels] canvas 0,0,1280,800` and nothing else. The perimeter law and the safety
  property at once: where structure yields nothing, it *says so*, and a router can
  detect "0% structural coverage" before acting and switch to vision.

## The headline for the paper's safety argument

Across six very different stacks: **zero silent divergences**, and **every** channel
was predictable from a stack signature (loaded `.so`, open debug port, UNO socket,
canvas-only DOM) *before* extraction. Failures were either explicit (declared opaque
region / honest empty tree) or environmental blocks. That is exactly the property a
production router needs: not "structure always works" (it doesn't — Qt and games
don't), but "you can always know in advance whether it will, and it never lies to
you when it won't." The job for the Windows and macOS runs is to try hard to break
that — to find a *silent* cell, especially in custom-drawn native apps (UIA on
Windows, thin SwiftUI AX trees on macOS are the prime suspects).
