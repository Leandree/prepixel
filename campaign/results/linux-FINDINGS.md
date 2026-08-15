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

---

## Hardening round (silent-divergence hunt, native blind-click, glyphs, living GTK)

Four adversarial/robustness tests added after the first pass:

- **Silent-divergence hunt — the important one.** We *found* two silent-divergence
  classes in the naive view: (1) an element covered by an overlay was listed as
  present/clickable while a blind click would hit the overlay; (2) off-viewport
  content (`left:-9999px`) leaked in. Both are now closed: a hardened in-page
  distiller (`src/distill-hardened.mjs`) hit-tests each element (`elementFromPoint`)
  and marks covered ones `[occluded]`, and clips off-viewport content. Cross-window
  occlusion is resolved geometrically from the WM z-order (two overlapping windows →
  back window computed ~48% covered). CSS `opacity:0` / `visibility:hidden` were
  already filtered. **Net: naive structure CAN be silently wrong about
  visibility/hittability; a safe channel needs a hit-test pass (in-window) + the
  compositor map (cross-window). With those, no silent case survived.** This is the
  single most important result for the production-safety argument — and the thing
  the Windows/macOS agents must re-run (UIA on custom-drawn apps; thin SwiftUI AX).

- **Glyph decode, hard cases** — stronger than predicted. Using the per-run font the
  tree names, reverse-cmap + Unicode NFKC + BiDi reorder recovered Latin, accents,
  CJK, emoji, and even Arabic exactly (`مرحبا`). Residual lossy tail (discretionary
  ligatures, complex mixed BiDi) is small and *detectable* (a glyph with no cmap
  entry is a known miss) — degrades explicitly.

- **Living GTK** — native mirror of the browser result: ~1 KB semantic inter-frame
  diff on an animating widget set vs a flat 1366 tok/frame screenshot; idle ≈ 0.

- **Native OS-level blind click** — partial. Logic implemented (structured box +
  window origin + chrome offset → screen px → real `xdotool` click → verify);
  browser grounding already 4/4 in phase 1. The end-to-end native run was blocked by
  Chromium DevTools-port flakiness after many headless relaunches (env, not
  approach). Windows/macOS agents complete this natively via UIA+SendInput /
  AXFrame+CGEvent.

---

## Precision-vs-pixels duel (the reviewer's experiment)

Same 20 randomized pages, both conditions, same model, mechanical verification.

- **Accuracy: parity.** 18/18 correct from the structured view AND 18/18 from
  screenshots (n=6 × 3 tasks). On clean legible pages, pixels score 100% too — so on
  *this* set the win is purely cost. The accuracy *advantage* of structure is real
  but lives in the degraded regimes tested separately (occlusion, off-viewport, tiny
  text), not on legible screens. Stated honestly so the paper doesn't overclaim.
- **Cost: 3.5× fewer tokens, 36× fewer bytes**, every page (n=20). Screenshot side
  uses the EXACT public image-token formula; structured side uses chars/4 (no offline
  BPE tokenizer — network-blocked), corroborated by the tokenizer-independent 36×
  byte ratio. Figure: `results/duel/fig_duel.png`.
- **Infra hardening:** added `campaign/validate.py` (schema-checks every result JSON
  before aggregation) and froze the canonical T1–T6 battery in `campaign/README.md`,
  so the Windows/macOS agents produce directly-comparable, aggregatable data.

---

## Round 3 — porting the macOS-added cell types back to Linux (and a deeper leak audit)

- **Leak audit of our own hardened distiller — FOUR more silent classes found and
  closed**: shadow-DOM text (walker didn't descend), iframes (neither walked nor
  declared — the worst case), CSS background-image content, and color-only
  semantics (status dots). Patched: shadow recursion, same-origin iframe recursion
  with coordinate translation + own-document hit-testing (first patch emitted
  frame-local coords — caught), cross-origin `[pixels] iframe`, `[pixels] bg`, and
  `mark x,y,w,h color` lines. Refined claim for the paper: completeness is a
  *coverage accounting* whose guarantee is only as good as the distiller's
  enumeration of content classes — each campaign round found one the previous
  missed — so the durable guarantee is the runtime spot-check, not distiller trust.
- **Retina/DPR two-tier replication**: DPR=2 capture of the same page = 4784 tok
  (high-res tier) / 1534 (legacy) vs 438 structured — exact match with macOS.
  Structured cost is DPR-invariant; pixel cost is an API-side downscale rule.
- **UNO write path**: insertString round-trip exact incl. accents+emoji,
  9–109 ms writes — the Linux mirror of Pages read+write. (Ops: port 2002 wedged
  after many restarts; fresh-port retry is a router lesson.)
- **Hard text via CDP**: 7/7 exact (combining accents, ZWJ family emoji, RTL
  logical order). The glyph problem is a render-level artifact; semantic channels
  don't have it — same mirror-caveat as macOS (text held ≠ glyphs painted).
- **gnome-chess at the render level**: the board is ~10 texture nodes (explicit,
  croppable), chrome text readable — the render-tree counterpart of macOS's
  AX-annotated Chess. Boundary = channel level × developer annotation. Probe
  hygiene: first run silently captured stale widget-factory frames (binary in
  /usr/games, `which` failed); caught only because we re-render every captured
  tree before believing it.
- **Real-web battery/navigation**: `blocked` in this sandbox (egress filter) —
  one confirmation run on the real Linux desktop recommended, scripts exist.
