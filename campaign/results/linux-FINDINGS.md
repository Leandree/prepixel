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

## Round 4 — the real-desktop confirmations the sandbox could not run (debian-server, 2026-08-17)

Run on Léandre's headless Debian 13 server: real internet egress, no display —
everything graphical under Xvfb + dbus-run-session, all GUI packages extracted
from .debs into a user prefix without root (one 8-byte binary patch to relocate
Xvfb's hardcoded /usr/bin/xkbcomp). That environment note is itself a datum: the
"AT-SPI is blocked headless" verdict of the first sandbox was a *sandbox*
artifact — under plain dbus-run-session the a11y bus D-Bus-activates on first
client contact, no seat, no WM, no gsettings needed.

- **The web-parity result replicates number-for-number across OSes.** Same 16
  sites, same scripts (paths-only diff), Chrome 148-under-Xvfb vs macOS's Chrome
  151, x86_64 vs Apple Silicon, two days apart: ratio of totals 1.00x (macOS
  0.98x), median per-site 1.15x (identical), structure wins on the same 10/16,
  vitrine 2.20x / commerce 0.83x / media 0.97x identical to the hundredth,
  Hacker News 0.46x identical, 7.6 screens-per-page identical, the same 6
  consent banners. Blind navigation: 8/8 again, same URLs, and the MDN
  disclosure toggle moved the view by the same +16 lines as on macOS. If the
  paper needs one sentence: the cost ratio is a property of the page, and the
  page is the same page everywhere — the OS contributes only latency (mean view
  61 ms here vs 16 ms on the M-series laptop).
- **AT-SPI in session, GTK3 + Qt6, one client, zero adapters.** The same pyatspi
  code drove Mousepad (GTK3) and FeatherPad (Qt6): identical roles, states,
  Text/EditableText, identical text-changed event vocabulary. Editors cost 68
  (GTK) / 331 (Qt) tokens vs 1365 for a screenshot; idle is 0 events; a
  keystroke is a ~21 B pushed delta. The honesty details were the best part:
  with no WM Mousepad renders menubar-less at 48x52 px, and the channel said
  exactly that (SHOWING=false, MININT extents, frame extents matching X's
  geometry byte-for-byte) — present-in-tree vs shown-on-screen is cleanly
  distinguished.
- **Native blind click, closed end-to-end on three stacks.** The old 'blocked'
  cell re-ran first try: CDP box + window.screenX/Y + chromeTop → xdotool →
  IDLE→CLICKED read back via CDP. Plus GTK (context menu → Select All →
  selection [0,92] verified in-channel) and Qt (menubar + tab). 4/4 first-
  attempt. Router note: CDP makes you compose three coordinate frames yourself;
  AT-SPI answers in DESKTOP_COORDS directly.
- **The OBS silent-mimicry class exists on Linux, in a stock Debian app — and
  the shipped guard calibration MISSES it.** qBittorrent's speed graph
  (SpeedPlotView, custom QGraphicsView paint) is on screen a live chart — axes,
  legend, grid, real DHT-traffic curves — and in AT-SPI a nameless
  `filler [154,313,1038,407] kids=0`, indistinguishable from the genuine spacer
  fillers in the same tree, while the chrome around it (combos, labels) is
  fully exposed. Silent-by-mimicry, predicted a priori from "QGraphicsView +
  paintEvent". Then the twist that improves the paper: coverage-guard's
  contentEnergy reads 0.020 — under the 0.03 threshold calibrated on Windows's
  densely-painted panes (0.06–0.07) — so guard A as shipped calls the chart
  "genuinely-empty". False negative. The margins say it's a calibration gap,
  not a detector limit: the genuinely-empty control in the same frame measures
  0.000 on all three metrics (64x64 energy, full-res energy, edge fraction) vs
  the chart's 0.020 / 0.025 / 0.0268 — total separation; threshold 0.01 or an
  edge-density metric catches it with zero false positives on every sample the
  campaign has measured on any OS. Lesson for the safety claim: "catchable at
  runtime" is a property of the guard's *calibration*, and sparse line-art is a
  regime the Windows-derived threshold had never seen. Guard B stayed correctly
  silent (counts say 0, rows say 0 — consistent).

## Round 5 — the per-window capture primitive, and the two missing tiers (debian-server, 2026-08-17)

- **XComposite closes the per-window-capture rule on the third OS.** ~80 lines of
  Xlib (`campaign/linux/grabwin.c`): redirect one window, read its own surface,
  compare with the screen crop at the same rect. With FeatherPad covering 3/4 of
  Mousepad: 14.2% of pixels diverge, and the guard energy of the screen crop
  (0.042) CROSSES the 0.03 threshold while the window's own surface reads 0.021 —
  the verdict flip macOS predicted, reproduced with plain occlusion instead of
  transparency. Two X11 facts worth keeping: stock Xvfb ships Composite 0.4 and a
  client can redirect a single window with no compositor; and the redirected
  surface holds content under occluded regions (the X11 twin of PrintWindow
  PW_RENDERFULLCONTENT), so per-window capture is strictly more informative than
  the screen.
- **Tier F/Java measured** (purpose-built SwingProbe, OpenJDK 21 +
  java-atk-wrapper): the bridge works and is fast (25 ms full walk), text/value/
  blind-click all pass, and the custom-painted JPanel reproduces the OBS shape on
  a third toolkit — nameless kids=0 panel, painted text nowhere in the tree.
  Dialect quirks a router must know: role is 'button' (not 'push button'), the
  frame node reports extents [-1,-1,-1,-1]. Interception accident of the
  -Bsymbolic class: AtkWrapper's static init execs a hardcoded /usr/bin/xprop and
  a11y dies entirely if x11-utils is absent — three signatures needed, not one.
- **Tier F/Flutter measured on a real third-party app** (AppFlowy 0.13.2,
  official .deb): the screen renders a full login UI; the channel exposes 5
  nodes, zero content, one node answering childCount = -1 with stalling property
  reads (17.4 s first walk). ScreenReaderEnabled=true — live AND at launch —
  changes nothing. Classified unavailable/EXPLICIT-by-shape: 0% structural
  coverage is computable in one walk, so the router's pixel fallback is
  deterministic; nothing mimics a valid answer. Flutter joins games in the
  honest-refusal class on this build, with the usual caveat that the boundary is
  build wiring, not technology.
- **The guard spectrum is now five points and it condemns the 0.03 threshold**:
  FL/OBS 0.06–0.07 (caught), Swing waveform-on-dark 0.036 (caught by 0.006),
  AppFlowy full login UI 0.029 (a WHOLE REAL SCREEN under the threshold),
  qBittorrent sparse chart 0.020 (missed), genuinely-empty 0.000 everywhere
  measured, on three OSes. Threshold 0.01 separates every real-content sample
  from every empty sample in the campaign's data; 0.03 sits in the middle of the
  content distribution. Returns-file FYI updated accordingly.
