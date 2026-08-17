# pipeline-tap

**Can a computer-use agent read the rendering pipeline's *input* (the structured
scene the machine is about to draw) instead of its *output* (a screenshot)?**

Today's agents (Anthropic computer use, OpenAI CUA, Gemini Computer Use, UI-TARS)
perceive the screen as pixels: one screenshot per step, ~1,000–4,800 vision tokens
each, re-interpreted from scratch every time — even when nothing changed. Yet the
machine *forward-rendered* that screen milliseconds earlier from structured data
that still exists in memory (DOM, layout tree, display list, document model).
Screenshot perception is **inverse graphics on a scene we already have the source
for.** This repo probes whether reading that source is cheaper, safer, and
continuous — and, crucially, whether it works *predictably enough to ship*.

> **The thesis is not "never use pixels."** It's *"stop doing image interpretation
> you don't need."* Structure is the backbone; pixels are a targeted fallback for
> the regions structure can't read (games, video, canvas). The whole point is that
> the boundary between the two is **knowable in advance** — and the campaign showed
> that it is *not* automatically declared. Six applications returned a view that
> disagreed with the screen without saying so; a documented router guard converts
> four of them into explicit declarations, and the other two bound what that guard
> can do — one is too sparsely painted for its calibration, the other substitutes a
> wrong string instead of omitting one. The boundary
> is predictable; making it **explicit is the router's job, not the OS's** — and
> that job is not finished.

---

## TL;DR — what we found (all measured, in this repo)

- **Cost — and the honest caveat, which is the more interesting half.** On synthetic
  app UIs the structured view is **3.5× fewer tokens and 36× fewer bytes** than a
  screenshot (n=20 pages, exact image-token formula). But on **16 live public
  websites it collapses to break-even**: 0.98× on the ratio of totals, 1.15× median
  per page, ranging from **0.46× on Hacker News** (structure costs *twice* a
  screenshot) to **3.11× on Vercel**, ahead on 10/16 sites. The mechanism:
  a screenshot has a **flat** cost set by the viewport, while a structured view
  scales with **information density** — so the ratio is a property of the *page*,
  not of the method, and structure loses on text-dense pages. Where structure wins
  unambiguously is **change and idleness**: perceiving a *change* costs 14–205
  tokens vs a flat 1,366 for a re-screenshot, an idle frame costs **0**, and
  watching a self-updating screen for 6 s is **14× less** than screenshots at 1 fps.
  Retina cuts both ways: image tokens are charged *after* the API's automatic
  downscale, so a 2× capture costs 4,784 tokens on a high-res model (ratio 12.2×)
  but only 1,534 on a legacy-tier one (3.9×).
- **Completeness is nearly free.** Closing four more silent-leak classes (shadow DOM,
  iframes, CSS background-image, colour-only semantics) cost **~2%** on the same 16
  sites — four of which came back byte-identical, as a determinism control. The
  safety machinery is not what makes a structured view expensive; text density is.
- **You can actually browse this way.** **8/8** blind steps on 5 live sites with
  every decision taken from the structured view alone — 6/6 navigations, 1/1
  disclosure toggle confirmed *in the channel* without a screenshot, and 1/1
  correct refusal to click a control that does not exist.
- **Accuracy.** On legible screens, **parity**: 18/18 correct from structure and
  18/18 from pixels. Structure's *accuracy advantage* appears only in degraded
  regimes (occlusion, off-viewport, tiny text) — stated honestly, not overclaimed.
- **It generalizes beyond the browser.** We tapped a real GTK4 app's render tree
  (`gsk_renderer_render`) and re-rendered it to the exact on-screen frame; recovered
  text (incl. Arabic/emoji/CJK) from glyph IDs; read LibreOffice's document model via
  UNO at ~65× less than a screenshot.
- **The wrong level is the literal GPU stream.** By the Vulkan/Skia layer, text is
  already rasterized to glyph atlases — semantics are gone. The **sweet spot is one
  rung up**: the toolkit render tree / display list / document model.
- **Safety (the production question) — the campaign's most important negative
  result, its repair, and the two places the repair does not reach.** Across 71
  cells on three OSes, **100% of channels were predictable in advance** from a stack
  signature. But "never silent" did **not** survive contact with real apps: **6
  silent divergences found, 4 neutralised, 2 still standing.**

  Four share one mechanism, *disagreement by omission* — a container node is
  present, its content is absent, and nothing declares the region opaque: FL Studio/
  Delphi, OBS/Qt6 and rekordbox/JUCE on Windows, plus Zoom's in-meeting stage on
  macOS, where an `AXTabGroup` claims 89.6% of the window and holds one 115×22
  label. That the same shape appears through **two different accessibility APIs on
  two different OSes** is what makes it a finding rather than a UIA quirk. All four
  are **caught and declared** by a documented router guard (`src/coverage-guard.mjs`:
  a pixel spot-check on structure-empty regions, plus a self-consistency check
  needing no pixels that catches "32 tracks declared, 0 rows exposed"), and each
  keeps a `mitigation` record naming what it was found as, so the finding is
  preserved rather than edited away.

  The two survivors matter more than the four repairs, because they bound the
  repair. **qBittorrent's custom-painted speed graph on Linux is the same omission
  class, but the guard misses it on calibration**: sparse line-art reads energy
  0.020 against a 0.03 threshold, where the genuinely-empty control reads 0.000 (a
  0.01 threshold or an edge metric closes it). **Java Swing on macOS is missed on
  kind**: it *substitutes* rather than omits — a label carrying an `accessibleName`
  publishes that name as its value while the painted text appears in **no attribute
  of any node**, so a counter whose text advances reads as a constant. Guard A only
  fires where structure is *empty*, and here there is a node with a confident,
  plausible, wrong string. The same cell found the campaign's first **act-side**
  silent failure: a button declaring zero actions accepts `AXPress` and returns
  **success** while nothing happens.

  So the honest form of the safety claim is not "every blind spot is convertible",
  it is: **the guard catches omission when it is dense enough to see, does not catch
  substitution, and does not watch actions at all.** Both survivors stay classified
  `silent` on purpose, and each cell specifies the concrete extension it needs.
  The taxonomy that forces itself on us is **explicit-by-shape vs silent-by-mimicry**:
  a 3D game exposing a 7-node frame-only tree cannot be mistaken for coverage (a
  router computes 0% structural coverage in one walk), whereas named-but-empty panes
  *look* like a valid answer. Both are predictable a priori and both are catchable at
  runtime (per-window pixel spot-check via `PrintWindow`), but predictable-and-
  catchable is not the same as declared. **The honest claim is therefore: the boundary
  is knowable, and making it explicit is the router's responsibility — no OS
  accessibility layer does it for you.**
- **The merged desktop view.** No single OS channel is both whole-screen and
  semantic (the compositor has all windows but only pixels; each toolkit is semantic
  but per-window). A **router** assembles it: window-manager map (geometry, z-order,
  focus) + best channel per window. Demonstrated live on all three OSes; the macOS
  run mapped 37 real windows in 32 ms for 838 tokens against 1980 for one
  full-screen capture. macOS adds a primitive the others lack — asking the window
  server directly (`AXUIElementCopyElementAtPosition`) instead of reconstructing
  occlusion from z-order, which is **100% exact on ordinary windows but 0% on
  overlay layers**, where a declared rect is an upper bound rather than coverage.

See `campaign/MATRIX.md` for the full coverage matrix.

---

## 🤖 AGENTS: START HERE — what you must do

If you are an AI coding agent running **natively on a Windows, macOS, or Linux
machine**, your job is to **extend the coverage matrix for your OS** by probing real
applications and recording results in a fixed schema. You are *not* trying to prove
the idea works — you are mapping its real boundary, and especially hunting for the
one disqualifying outcome: a **silent divergence** (a structured view that disagrees
with the screen without declaring it).

Do this, in order:

1. **Read `campaign/agent-brief-COMMON.md`** — the core safety question (H5), the
   T1–T6 test battery, the strict output format, and scope discipline. Read it fully.
2. **Read your OS brief:** `campaign/agent-brief-windows.md`,
   `campaign/agent-brief-macos.md`, or `campaign/agent-brief-linux.md`. It lists the
   channels to probe (UIA / AX / AT-SPI / CDP / UNO / render-tap …) and the apps to
   test, tier by tier.
3. **Run the T1–T6 battery on each app.** For every (app × channel), write one JSON
   file `campaign/results/<os>-<app>-<channel>.json` that validates against
   `campaign/results-schema.json`. Keep raw evidence (dumps, screenshots you took to
   verify) under `campaign/results/artifacts/`.
4. **Append a prose note** per OS to `campaign/results/<os>-FINDINGS.md`: what
   surprised you, any silent divergence you found, your honest read on predictability.
5. **Keep `campaign/results/<os>-agent-returns.md`** — your two-way log with the
   human test manager. Write a `DECISION NEEDED` entry for anything you should not
   decide alone (installing software, touching real accounts or files), an `FYI` the
   moment you find something that changes another agent's work, `BLOCKED` for what
   you could not do and why, and a `DONE` close-out that includes any bug in your
   *own* harness. It is correspondence, not evidence — measurements go in cells,
   prose goes in FINDINGS. Full convention in `agent-brief-COMMON.md`;
   `macos-agent-returns.md` is the worked example.
6. **Validate and aggregate before you finish:**
   ```bash
   python3 campaign/validate.py     # every result JSON must pass the schema
   python3 campaign/aggregate.py    # rebuilds MATRIX.md + matrix.json
   ```
7. **The Linux cell is already done as a worked example** — read
   `campaign/results/linux-*.json` and `campaign/results/linux-FINDINGS.md` to see
   exactly the shape and honesty level expected, then mirror it for your OS.

**What "done well" means:** breadth over depth (cover the listed apps at T1–T6 rather
than perfecting one), record `blocked`/`unavailable` cells as first-class results
(a SIP wall or a toolkit with no render tree is *data*, not failure), and if a
channel *looks* available but returns a view that disagrees with the screen, flag it
`failure_class: "silent"` — that is the headline result everyone is looking for.

Prime silent-divergence suspects to attack: **UIA on custom-drawn Windows apps**,
**thin SwiftUI accessibility trees on macOS**, and any app that paints to a canvas.

---

## Repo map

```
README.md                     ← you are here (master orientation)
src/                          ← browser PoC + experiments (Node/Playwright + Python)
  capture.mjs                 ·  CDP capture: screenshot / DOM view / Skia paint ops
  distill-hardened.mjs        ·  hardened in-page distiller (hit-test occlusion, clip off-viewport)
  duel.mjs                    ·  precision-vs-pixels duel (20 randomized pages)
  run-representations.mjs     ·  exp 1: three representations, token cost
  run-diffs.mjs               ·  exp 2: change diffs + living screen
  gen-eval*.mjs / verify-*    ·  grounding + visual grounding evals (randomized, mechanical)
  make-figures.py, make-duel-figure.py
pages/                        ← synthetic test pages
native/                       ← GTK4 render-tree tap (beyond the browser)
  gsktap.c, tap.gdb           ·  LD_PRELOAD shim + gdb tap on gsk_renderer_render
  decode_glyphs.py            ·  glyph-ID → text via reverse cmap
  samples/                    ·  a captured render tree + its exact re-render
campaign/                     ← the multi-OS test campaign (agents: this is your job)
  PROTOCOLE.md                ·  master protocol (FR): hypotheses, matrix, safety criterion
  agent-brief-COMMON.md       ·  READ FIRST — H5, T1–T6, output format
  agent-brief-{windows,macos,linux}.md
  results-schema.json         ·  the JSON schema every result must satisfy
  validate.py                 ·  schema-gate every result
  aggregate.py                ·  build MATRIX.md + matrix.json
  MATRIX.md                   ·  the aggregated coverage + predictability matrix
  results/                    ·  one JSON per (app × channel) + per-OS FINDINGS
  desktop/                    ·  the semantic-compositor router (router.py, cdp_extract.mjs)
results/                      ← figures + measurement outputs from src/ experiments
```

## Run the Linux PoCs

```bash
npm install                        # playwright-core
node src/run-representations.mjs   # three representations, token cost
node src/run-diffs.mjs             # change diffs + living screen
node src/duel.mjs                  # precision-vs-pixels cost duel (n=20)
python3 src/make-figures.py        # regenerate figures
# native GTK4 tap (needs gtk4 + gdb):  see native/README.md
# desktop router (needs an X desktop): python3 campaign/desktop/router.py
```

## The safety criterion, precisely

A channel is usable in production iff it is **(1) predictable** — a router can tell
from a signature (loaded libs, open debug port, UNO socket, accessibility response)
*before acting* whether structure is available and what it covers; **(2) explicit on
failure** — uncovered regions are declared (opaque rect / empty tree), never
silently wrong; **(3) verifiable at runtime** — the view can be cross-checked against
a screenshot. A channel that sometimes works but can't be predicted, or that fails
silently, is a **negative** result — report it as such.

## Why this isn't just "use the accessibility tree"

It's adjacent, and the 1990s already ran this play: screen readers built "off-screen
models" by hooking GDI/QuickDraw draw calls, then the industry replaced them with
accessibility APIs. What's different now: (1) the render tree *cannot be missing or
lie* — it is what's on screen, by construction — whereas a11y trees are unmaintained
exactly where agents need them; (2) the consumer is an LLM, a machine for
interpreting heterogeneous structured noise, not a brittle heuristic engine. The
accessibility API is in fact the OS-provided *merge* of per-app semantic trees — one
valid channel among several the router chooses from.

## Status

**All three OSes are covered: 71 cells, schema-valid, 100% predictable in advance,
6 silent divergences found — 4 neutralised, 2 kept as counter-examples.**
Linux 25, macOS 22, Windows 24.

The four neutralised are custom-drawn or video surfaces (FL Studio, OBS, rekordbox
on Windows; Zoom's in-meeting stage on macOS), each carrying its `mitigation`
record. The two survivors are deliberately left classified `silent`, because each
bounds the guard in a different way and that boundary is the useful result:
**qBittorrent's speed graph** (Linux) is the right class but too sparse for the
shipped calibration — energy 0.020 against a 0.03 threshold, with the genuinely
empty control at 0.000 on every metric — and **Java Swing** (macOS) is the wrong
class entirely, substituting a plausible wrong string for the painted text and
faking action success, which no pixel spot-check on an *empty* region can see. See
`campaign/MATRIX.md`, which reports *surviving* and *found-then-declared* as two
separate numbers, and the recalibration and act-guard proposals in the two
`*-agent-returns.md` files.

The real-web battery has now been run on all three OSes and the result is
essentially OS-invariant (macOS 0.98x, Linux 1.00x, Windows 0.99x on the ratio of
totals) — unsurprising, since all three drive the same Chromium, but worth having
measured rather than assumed. The Linux desktop round also exercised AT-SPI in
session on GTK3 and Qt6 (the old headless `blocked` was a sandbox artifact) and
closed the native blind click end-to-end on three stacks.

Still open: the two guard extensions the survivors call for (a lower/edge-based
energy metric, and an act-side check that re-reads after any action returning
success); Qt and Flutter on macOS (Java is now done); and a live specimen for the
layered-window occlusion rule on Windows, where the rule is encoded but the audited
desktop had no layered window to exercise it.

The write-up is a position paper (arXiv cs.HC/cs.AI) + a blog post; project notes
live in the attached Claude project.

## License

MIT
