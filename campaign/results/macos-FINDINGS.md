# macOS — field notes (claude-code, live MacBook Pro, macOS 26.5.2, 2026-08-14/15)

Ran on a **live, in-use machine** (user present part of the time, screen locked part
of the time) — which turned out to be a feature: it surfaced failure modes a clean VM
never would. 10 cells, 0 silent divergences. Every failure we hit was explicit,
predictable in advance, or a bug in our own probe — and each probe bug was itself a
lesson a production router must encode.

## The cross-cutting macOS discovery: the AT-latch

Three unrelated engines — **Chromium** (Chrome), **WebKit** (Safari), and **iWork's
text engine** (Pages) — all gate their accessibility content behind "is an assistive
client present?". First queries return an honest stub (window chrome, no content);
after sustained AX traffic (and/or setting `AXEnhancedUserInterface`, which
*officially errors* -25208/-25205 and works anyway), the full tree appears. System
apps (TextEdit, Finder, Clock, Chess) are populated immediately; Zoom too.
Router rule: **probe → poke → re-probe before concluding "unavailable"**. Never
classify from the first read.

## Session lock changes the physics

With the screen locked (loginwindow frontmost): AX window enumeration DEGRADES —
TextEdit returned zero windows, Pages returned its *menu tree* dressed as a window
(833 nodes of AXMenuItem, no content). Meanwhile the **AppleScript object-model
channel kept reading AND writing the Pages document perfectly** (73–158 ms
round-trips, char-exact incl. emoji). Channels fail differently; a router that can
fall back from AX to object-model survives a locked lid.

## Geometry traps (each cost us one failed action before we learned it)

- **CDP on Retina**: DOMSnapshot boxes are in *device* pixels, `Input.dispatchMouseEvent`
  takes *CSS* pixels (DPR=2 here). Blind click missed until divided by
  `devicePixelRatio`. Invisible on DPR=1 Linux — a macOS-specific trap nothing in the
  API labels.
- **TOCTOU on window moves**: the human moved a window between our frame-read and our
  click; the click landed on another app (and a Cmd+V went with it — undone by the
  paired Cmd+Z). Re-read frames immediately before acting, verify unchanged after.
- **Stale element handles**: a cached AXTextArea handle later pointed at a transient
  1.25-px caret remnant whose AXValue read empty — without erroring. Re-resolve
  handles before every read/act.
- **Startup degenerate trees**: Safari mid-launch exposed a cyclic
  AXApplication-in-AXApplication tree that exploded a naive walker into 13k menu
  nodes / 2.3 MB. Cycle-guard every walk (hash the element refs), re-query after
  settle.
- **Transient windows shuffle indices**: a tooltip (AXHelpTag) appeared as
  `AXWindows[0]`; sheets/alerts are NOT in `AXWindows` at all but ARE reachable via
  `AXFocusedWindow` and as window children. Modality is visible — if you query the
  right attributes. Our "silent divergence candidate" (a format-bar click swallowed
  with AX reporting value=0) dissolved once we found the modal sheet declared right
  there in `AXFocusedWindow`.

## Per-app one-liners

- **TextEdit (AX)**: full T1–T6. Pasted image declared twice over (U+FFFC in the
  text + AXImage child with exact rect → targeted crop possible). AX ranges count
  UTF-16 units; emoji are 2. Blind clicks from AXFrame are pixel-accurate.
- **Chrome (CDP)**: same distiller as the Linux cell, same numbers class (315-token
  view vs 880-token viewport screenshot; 1–2 ms captures; diffs 58–231 B; idle 0).
  Browser-chrome overlays (a Translate popup) are outside the page — CDP reads the
  page, AX reads the window; pair them.
- **Chrome (AX)**: content lazy (see AT-latch); once up, 15× heavier than the
  distilled CDP view of the same screen, but frames are global-points (directly
  clickable) and it sees browser chrome.
- **Cursor/Electron (CDP)**: workbench fully self-labeled via aria-labels (647-token
  view). Bonus trap: the app *silently dies* if `--user-data-dir` exceeds the
  103-char unix-socket limit. Login-gated content stays honestly gated.
- **Safari (AX)**: full page content after latch; canvas-only page = AXWebArea with
  zero children and zero fabricated text — the honest empty tree, exactly as specified.
- **Pages (object-model)**: the macOS answer to COM/UNO. Reads/writes the document in
  73–158 ms, semantic-only (no coordinates — must pair with AX for aiming), and it
  worked through screen lock. AX side needs the latch, then exposes the body in an
  AXTextArea.
- **Finder (AX)**: enumerate + blind-click + in-channel verification (AXSelected
  flipped on exactly the intended file). AppleScript path was consent-blocked; the
  AX fallback (AXPress on AXCloseButton) needed nothing.
- **Clock/SwiftUI (AX)**: living screen at 38 B/tick (~10 tokens) vs a
  full re-screenshot per second — ~100× cheaper. SwiftUI puts labels in
  AXDescription (not AXTitle) and the stopwatch digits in an AXGenericElement's
  *description* (AXValue nearby reads empty — probe both). Incident: our exploratory
  press paused the user's 174-hour stopwatch for ~3 min — semantic channels put
  destructive-adjacent controls one AXPress away; routers need action allowlists.
- **Zoom (AX)**: the prime custom-drawn suspect is… thoroughly annotated (42 labeled
  buttons, tab selection states, 3 embedded WebAreas). Home window only; in-meeting
  surfaces deliberately untested on a live account.
- **Chess (AX)**: the planned "game = pixels-only" negative REFUTED for Apple's own
  3D game: every piece is 'tour blanche, a1'-style AXButtons. The boundary is
  developer annotation, not app category. Unannotated GL/Metal games remain the
  expected pixels territory (untested here).

## Permissions ledger (the macOS thesis in one list)

One global **Accessibility** toggle (user-granted, once) unlocks the entire AX
channel for every app. **Screen Recording** needed only for verification
screenshots. **Apple Events** consent is per (host → target-app) pair with a
blocking dialog each first time — fine for a person, hostile to autonomy. CDP needs
nothing but only exists if you launched the app with the flag. No render-tap
attempted: SIP makes injection a non-starter, by design — on macOS only the OS
can provide this channel, which is the paper's point.

---

# Round 2 — the transversal cells (the ones the Linux reference had and macOS lacked)

Five cell *types* were missing after round 1. All five are now run. One of them
found a real silent divergence — in this repo's own tooling.

## The one that matters: an undeclared blind spot in our own hardened distiller

`distillHardened()` emitted only text and interactive elements. It had no OPAQUE
set, so **pictorial regions were dropped entirely**. On `pages/allcanvas.html` — a
screen that is 100% canvas — the hardened view was **zero bytes**. That view does
not lie about content, but it never declares its own blind spot, so a consumer
reads *"empty screen"* instead of *"opaque region, fall back to pixels"*. That is
exactly the disqualifying failure mode the thesis rules out, sitting in the code
path the duel and every safety claim run through.

Fixed in `src/distill-hardened.mjs`: IMG/CANVAS/VIDEO/SVG/PICTURE/EMBED/OBJECT are
now declared with their rects and hit-tested (so an occluded image is tagged too).
All-canvas now yields `[pixels] canvas 0,0,1280,800`; the mixed page declares
`[pixels] img 8,191,300,120`. **The duel numbers are unaffected** — 0/20 duel pages
contain any opaque element, and the post-fix re-run reproduces 1578 bytes / 391
tokens exactly. Worth stating plainly in the paper: the naive distiller had this
property and the *hardened* one lost it, because the two safety properties
(hit-testing vs blind-spot declaration) were implemented in different code paths.

## Cross-window occlusion: macOS ships the mitigation as an API

TextEdit over Chrome, 25.3% of the back window covered. Per-window structure is
blind to it — Chrome's AX still calls the covered point its own. But
`AXUIElementCopyElementAtPosition` on the system-wide element, probed at that
point, returns an `AXTextArea` owned by pid 65570 = **TextEdit**, the front window.
One system call, no rectangle math, no z-order bookkeeping — where the Linux cell
had to compute overlap-vs-z-order by hand. The same primitive also covers
in-window occlusion for native apps.

## The duel replicates across OSes, and Retina doubles the stakes

Same 20 pages (same generator, same seeds), so this is replication, not
re-measurement: **1578 bytes / 391 tokens vs 1366 image-tokens = 3.49x fewer
tokens, 39.4x fewer bytes** (Linux: 1580 B / 391 tok / 3.5x / 36.4x; the 2-byte
delta is one text wrap moving under macOS system-ui metrics). Accuracy: **18/18
both conditions** — parity, replicated. Methodology tightened over the Linux cell:
two *independent subagents*, one shown only the structured views, the other only
the screenshots, neither able to see the other's evidence.

Retina addendum, macOS-only — and the arithmetic is not the one you would guess.
Image tokens are `w·h/750` **after** the API's own automatic downscale, and that
downscale has two tiers: long edge ≤2576 px and ≤3.588 MP on the high-res models
(Opus 4.7/4.8/5, Sonnet 5, Fable 5), ≤1568 px and ≤1.15 MP on the older ones.
So the *same* 2× capture of this viewport (2560×1600 px) costs **4784 tokens on a
high-res model (12.24x ratio) but only 1534 on a legacy one (3.92x)** — barely
above the 1366 of a CSS-resolution shot, because the API scales it back down
regardless. Two consequences for anyone budgeting a pixel agent: sending Retina
pixels to a legacy-tier model buys resolution the model never receives (the one
case where the pixel side is *not* punished), and on high-res models the same
harness decision quietly quadruples the bill. We got this wrong first — a naive
`w·h/750` on the raw capture reported 5462/13.97x — which is itself the finding:
the pixel cost of a screen depends on a downscale rule that lives in the API, not
in the harness. Helper implementing both tiers: `src/image-tokens.mjs`.

## Hard text: the glyph problem simply does not arise here

10/10 exact against a ground-truth file — presentation-form ligatures, *combining*
accents (preserved, not silently NFC-folded), CJK, Arabic and Hebrew in logical
order, bidi-mixed lines, ZWJ family emoji with skin-tone modifiers. Read latency
0.03 ms. Where the Linux render-tap needed reverse-cmap + NFKC + BiDi reorder and
still had a lossy tail, AX hands over the model string.

The mirror-image limitation is the honest counterpart: **AX reports the text the
app holds, not the glyphs it painted** — a font-fallback failure would be invisible
here, where a render tap would show it.

Geometry is a closed round-trip, verified against a screenshot: `AXBoundsForRange`
puts the RTL lines right-aligned (Arabic x=770 w=86 and Hebrew x=797 w=59, both
ending at 856 against a window edge of 866) and resolves the bidi line into
`Total:`[220,40] `مرحبا`[286,33] `END`[326,20]; the inverse `AXRangeForPosition`
returns the exact character under a pixel — including **ح**, the correct middle
letter of the Arabic word, despite right-to-left glyph order.

Range-arithmetic trap, measured: AX ranges are UTF-16 units, and the family emoji
is **11 UTF-16 units rendered as one 15x18 px cell** — string length is not a proxy
for visual extent in either direction.

## Render-tap: blocked, with a positive control

The Linux cell's strongest guarantee (the render tree cannot lie — it *is* what
will be drawn) is structurally unavailable here. Measured with a no-op probe
library: it **loads** into a locally compiled unsigned binary (control — so the
test is sound), and is **refused** by both TextEdit (platform binary, SIP) and
Chrome (hardened runtime, `library-validation`, flags 0x12a00). Note who chose
what: SIP is Apple's, but library-validation is the *developer's* flag. SIP was
left enabled throughout and nothing was worked around — the refusal is the result.

That is why macOS is the OS where *"only the platform vendor can provide this
channel"* is an observation rather than an argument, and why the AT-latch,
thin-tree risk and annotation quality dominate every other macOS cell.

## The real web deflates the synthetic result, and that is the finding

Sixteen live public sites across six categories (vitrine, presse, commerce, media,
reference, webapp, webapp-canvas), logged out, no lab pages: Amazon.fr, Le Monde,
BBC, YouTube home and watch, GitHub, Wikipedia, MDN, Stripe, Vercel, Apple,
leboncoin, DuckDuckGo, Hacker News, Excalidraw, OpenStreetMap.

Averaged over the sixteen, the structured view costs **1360 tokens against 1366 for
one CSS-resolution viewport screenshot — a ratio of 1.30x, not the 3.49x of the
synthetic duel.** The mechanism is simple and should be stated plainly rather than
buried: a screenshot has a **flat** cost set by the viewport, while a structured
view scales with **information density**. The ratio is therefore a property of the
page, not of the method — and the spread is enormous:

| | ratio | reading |
|---|---|---|
| Vercel (vitrine) | **3.11x** | sparse marketing page, 439 tokens of structure |
| Excalidraw, Stripe, Apple, OpenStreetMap | 1.7–1.8x | visually rich, semantically thin |
| BBC, MDN, YouTube home | 1.3–1.6x | mixed |
| Le Monde, GitHub, Wikipedia | 0.7–0.8x | text-dense: structure *loses* |
| Amazon.fr (commerce) | 0.48x | 2834 tokens of structure |
| Hacker News (webapp) | **0.47x** | pure text; structure costs **twice** a screenshot |

By category: vitrine 2.20x, webapp-canvas 1.75x, presse 1.21x, reference 1.11x,
media 0.97x, commerce 0.82x, webapp 0.80x. Note that this inverts the intuition
that "text is cheap": the pages where structure loses are exactly the text-heavy
ones, because that is where there is the most to say.

Three corrections push back in the structured view's favour, and all three are
real. A viewport screenshot shows **one screen**, and covering a full page took
**7.6 screens on average** (19 on Stripe and on Amazon) — so the honest whole-page
comparison is not one screenshot. At Retina 2x on a high-res model the screenshot
costs 4784 tokens, moving the average to **4.54x** — but only 1534 on a legacy-tier
model (**1.46x**), for the downscale reason above. And the structured view is
**16 ms** to capture against a screenshot round-trip two to three orders of
magnitude slower.

The obstacle that actually bit was not rendering: **6/16 sites raised a consent
banner**, and 7/16 carry canvas or video (all declared as `[pixels]` rects — the
distiller fix earning its keep on production pages). The occlusion counts are a
good density index in themselves: 0 on Hacker News's flat 1990s table, 12 on
Wikipedia, 79 on BBC, 105 on Le Monde, 114 on Amazon, 142 on the YouTube watch
page. A naive DOM reader would publish roughly a hundred clickable targets per
commercial page that are not, in fact, hittable.

## Can you actually browse this way? 8/8 — and the failures were mine, not the channel's

Eight blind steps on five live sites, with the rule that *every* decision comes
from the published view lines alone — no screenshot is read anywhere in the loop.
**6/6 navigations, 1/1 toggle, 1/1 correct refusal.** Hacker News `new` → `/newest`;
Wikipedia's in-article "Rasterisation" → the right anchor among competing
occurrences; GitHub's `Insights` tab on a fully hydrated app shell → `/pulse`;
MDN's sidebar link → `/Canvas_API/Tutorial`; DuckDuckGo's `Images` filter, verified
by eye; and Hacker News `More` → `?p=2`, which sits **below the fold** and forced a
scroll-and-search (2 views for 1 target — a cost both channels pay equally).

Session cost, stated honestly: **16 826 structured tokens across 9 view reads vs
12 294** for the same nine looks as CSS-resolution screenshots. The structured
route was **1.37x more expensive**. It flips to ~3.5x cheaper only against Retina
screenshots on a high-res model.

The first round scored 3/8-equivalent, and **all three failures were the router's,
not the channel's** — which is why they are recorded rather than quietly fixed:

- It matched *text* lines and ignored the *interactive* line whose box contained
  them, so it aimed at MDN's "Tutorial" believing it was a link. The view had
  already published `summary 16,409,224,32` one line above. The click was
  **correct** — screenshot-confirmed, it collapsed the disclosure widget — only the
  expectation was wrong. Joining text to its innermost enclosing control (pure
  coordinate arithmetic on already-published lines) fixed it, and that join is the
  same operation a native router must perform on an `AXStaticText` inside an
  `AXButton`.
- It expected a "Pull requests" tab on `torvalds/linux`, a repo with PRs disabled.
  The view **did not offer one**, and the screenshot confirms the tab does not
  exist. That is the desired failure mode — explicit "not found" instead of a
  plausible-looking click — so it is now a first-class negative control.
- A wrong URL regex.

The generalisation is worth more than the score: **when a semantic router misfires,
the first hypothesis should be that it under-used the view, not that the view
lied.** In all three cases the view was complete.

The toggle step is the strongest single piece of evidence that the channel is
self-sufficient. Its effect is invisible in the URL, but plainly visible *in the
structured view* (+16 lines as the collapsed section let lower sidebar entries into
the viewport), so the router confirmed its own action without ever taking a
picture. One production note: DuckDuckGo raised a promotional overlay **after** the
click — overlays arrive as a consequence of navigation, not only on load, so a
router must re-read occlusion after every action.

## What's still open

The desktop **router / merged view** (the compositor-map cell — all the pieces now
exist: CGWindowList z-order + `AXUIElementCopyElementAtPosition` + per-window
channel), a **third-party SwiftUI** app (the README's prime thin-tree suspect —
only Apple's well-annotated Clock was sampled), **Tier F** non-Cocoa toolkits
(Qt/Java/Flutter), a genuinely unannotated GL/Metal game, and Zoom in-meeting.
None of these block the macOS verdict: **predictable, explicit, and — after the
distiller fix — zero surviving silent divergences.**
