# macOS agent — returns to the test manager

**What this file is.** A two-way log between the macOS agent and the human test
manager. The agent writes here whenever it needs a decision, hits a blocker, or
finds something that changes another agent's work; the manager replies in the same
file under `MANAGER:`. Every OS agent keeps its own — see
`campaign/agent-brief-COMMON.md` § "Returns to the test manager".

**What this file is NOT.** It is not the scientific record. Measurements, verdicts
and mechanisms go in `macos-FINDINGS.md` and in the result cells; a claim is not
"published" because it appears here. This file is correspondence: open questions,
decisions taken and why, cross-agent warnings, and honest statements of what was not
done. Nothing here should need to be trusted to reproduce a result.

**Convention.** Newest entry at the top. Each entry dated, with a status:
`DECISION NEEDED` / `FYI` / `BLOCKED` / `DONE`. Leave answered entries in place —
the history of what was asked and decided is part of the record.

---

## 2026-08-17 — FYI — the guard has a boundary, and I found where: Java Swing on macOS

The last two macOS tasks are done and one of them broke the clean story, so it needs
flagging rather than filing. **`macos-swing-accessibility-api` is classified `silent`
with NO mitigation record** — the first surviving silent divergence in the matrix
since the Windows round was neutralised. That is deliberate and I want it challenged
if anyone disagrees.

Two failures, neither of which `coverage-guard` can see:

1. **Substitution, not omission.** Where a Swing component carries an
   `accessibleName`, the macOS AWT peer publishes that name as its *value*, and the
   painted text then appears in **no attribute of any node** — I enumerated every
   string attribute of every node and searched; `SENTINEL` and `count=` return zero
   hits. Control isolating the mechanism: the one label without an `accessibleName`
   reports its real text correctly. So a counter whose text advances reads as the
   constant `counter-label` forever. Guard A only fires on regions structure calls
   *empty*; here there is a node with a confident string, so it never looks.
2. **Act-side silence, a class we had not seen.** The button declares **zero**
   actions (`AXUIElementCopyActionNames` → `[]`) and `AXPress` returns **0, success**
   — five times, including with the window raised and the app frontmost — while the
   screen never changed, confirmed on the window's own surface. The API had
   `kAXErrorActionUnsupported` available and did not use it. Every prior silent cell
   was a bad *read*; this is an *act* that reports success and does nothing, which is
   worse, because the agent proceeds believing the world moved.

So the honest form of the safety claim is now: **the guard catches omission, not
substitution, and it does not watch actions.** I specified two cheap extensions in
the cell rather than leaving it as a complaint — an OCR spot-check gated on the
a-priori signature (`AXDescription == AXValue` on a static text in an AWT process is
exactly the misannotated shape), and an act-side guard that re-reads the target
after any action returning 0 and requires *something* to have changed before
reporting success upward, at roughly 20 tokens per action.

For the Windows and Linux agents: your Swing/JAB and AT-SPI cells should check the
same two things. On Windows, JAB may well expose the real label text where macOS AX
does not — if so, that is a clean cross-OS contrast worth having, and it would mean
the substitution is the *macOS peer's* fault specifically, not Swing's.

---

## 2026-08-17 — DONE — Zoom in-meeting, run live at Léandre's request

`macos-zoom-inmeeting-accessibility-api`. The meeting stage's `AXTabGroup` claims
89.6% of the window and contains exactly one 115x22 label, over a live gallery
reading 0.876 energy — silent-by-mimicry, the FL Studio shape, **on a different OS
and a different accessibility API**, which is the part that matters: the pattern is
not a UIA artifact. The same app ships the opposite shape in another window (the
1-node control bar, 0% coverage, explicit and safely cropped), so both failure modes
sit side by side in one process. Router rule that falls out: measure coverage from a
container's *contents*, never its declared rect.

Privacy handling, since it was a real meeting: no meeting image was written to disk
(energy computed in memory from the CGImage, only the scalar kept), and text was
classified rather than copied — verbatim only for the app's own UI vocabulary. The
artifact contains shapes and counts and nothing else; I re-read it to confirm.

---

## 2026-08-17 — FYI — I reviewed the Windows silent→explicit reclassification, and it holds

Merging the Windows round, I saw `silent=3` become `silent=0` in the matrix and went
looking for erasure, because losing the study's headline negative result to a
flattering number is exactly the failure mode we are supposed to guard against. It
is not what happened, and the bookkeeping is better than mine would have been:

- `aggregate.py` now prints **two** numbers — *surviving* (0) and *found, then
  caught-and-declared* (3, each app named) — rather than one that hides the other.
- Each converted cell carries a `mitigation` record whose `found_as` field keeps the
  original verdict verbatim ("silent (2026-08-15): named-but-empty panes over a
  dense painted DAW UI"). The finding is preserved in the data, not just in prose.

One cosmetic snag for whoever next touches those three cells: their
`runtime_verification.agreement` prose still ends with "recorded as the silent
class", which now sits oddly beside `failure_class: explicit`. It is not wrong —
that *is* the class it was recorded as — but a reader skimming will trip on it.

The one substantive question I would still put to the manager, since it affects how
the paper phrases its central claim: `failure_class` is defined in the schema as a
property of **the channel**, and the channel in those three apps is still silent —
what changed is that *our router* now detects it. Both readings are defensible and
the matrix currently states both, so nothing is being misreported. But if the paper
wants a single number, it should be "3 channels silent, 3 neutralised by a
documented guard", never "0 silent". I have written the README that way.

Also confirmed on merge: the real-web battery now exists on all three OSes and the
result is essentially OS-invariant — macOS 0.98x, Windows 0.99x on the ratio of
totals, both with a 1.15x median. Expected, since all three drive the same Chromium,
but it is now measured rather than assumed, which is what the Linux cell asked for.

---

## 2026-08-15 — DONE — the game cell, answered better than any of my three options

Léandre installed **DiRT 4** (Feral port, Metal+OpenGL, 3D) and **Cuphead** (Unity,
OpenGL, 2D), which supersedes the decision below. I ran both rather than picking
one, because two different engines test whether the boundary is "game" or "renderer".
Cell: `macos-games-pixels-baseline`. Result: DiRT 4 while rendering is a **1-node**
tree (AXWindow, zero children) over a 1512x982 surface, stable across five samples
in two minutes; Cuphead is 2 nodes, the second being the window title echoed as a
child — *not* a reading of the painted logo, and I said so explicitly in the cell
because that one is easy to misreport.

The finding I did not expect, and the reason the cell is worth more than a control:
**the contrast is inside a single process.** Before the game starts, the same pid
presents the Feral launcher — 31 AX nodes, an AXWebArea, 11 buttons, which I drove
with a coordinate-free AXPress on "Jouer". Press Play and that same pid becomes a
1-node window. Structure did not degrade because the app is a game; it vanished
because the surface stopped being a web/AppKit view and became a Metal drawable.
**A router must evaluate coverage per window and per state, never per application** —
caching "DiRT 4 is well annotated" from the launcher would be exactly wrong ten
seconds later. Together with the Chess cell this pins the boundary: developer
annotation over a GPU surface, not rendering technology and not app category.

Two checks I ran instead of assuming. A Metal drawable could plausibly hand a stale
frame to a compositor capture, so I hashed two captures ~12 s apart through both
paths; all four differ, so the per-window capture rule from the SwiftUI cell holds on
GPU surfaces too. And `coverage-guard` on the window surface gives energy 0.625 and
0.866 — it correctly converts "structure is empty" into "declared opaque, crop".

Both games were quit at the end and nothing else on the machine was touched. Note
for the record: I downscaled the two evidence captures to 1400 px and dropped the
screen-region duplicates, which for a fullscreen game are byte-equivalent to the
window surface — 19 MB of redundant PNG for no added evidence.

---

## 2026-08-15 — SUPERSEDED — which app for the unannotated GL/Metal game cell

The deepening plan's macOS P1 asks for "a genuinely unannotated GL/Metal game" whose
acceptance is *a cell confirming frame-only/empty tree → explicit `0% coverage →
pixels`*. This is the honest pixels-territory control that balances the Chess cell
(where Apple's annotation refuted "game = pixels only").

There is no game installed on this machine. Léandre offered to install one. Three
options, and I want the manager's call rather than mine because two of them touch
the machine:

1. **PlagueInc** (already in the Steam library). No install, but it launches Steam
   and signs the user in. It is also a Unity 2D title, and Unity commonly exposes an
   empty AX tree *because the engine wires nothing* — we would get the right result
   for a reason that does not exercise what the cell is about (a moving,
   full-screen GPU surface).
2. **Install a native Metal game.** Best scientific fit — a real animated Metal
   surface — at the cost of an install on the user's machine.
3. **UTM's VM display** (already installed; links `Metal.framework` + `MetalKit`).
   An unannotated Metal surface by construction, no install, no Steam login. Less
   spectacular than a game, but equivalent for what the cell must prove: a region
   with 0% structural coverage that the channel declares rather than hides.

**My recommendation: option 3**, on the grounds that it changes nothing on the
machine and tests the same property. I will default to it if no answer comes.

**Caveat I want on the record either way:** whichever we pick, this cell proves that
*an* unannotated GPU surface is handled explicitly. It cannot prove that *all* games
are, because — as Chess and rekordbox both showed — the boundary is developer
annotation, not rendering technology. The cell should be written as a positive
control, not as a claim about games in general.

---

## 2026-08-15 — FYI — a rule the Windows and Linux agents must apply to `coverage-guard`

This one changes other agents' work, so it should reach them before they run their
P0.

`src/coverage-guard.mjs` shipped validated on synthetic pages only. Running it on a
real macOS overlay window (declared rect 680×580, actually painting a narrow band,
transparent elsewhere) gives:

| how the region was captured | energy | guard verdict |
|---|---|---|
| screen-region crop | 0.387 | `SILENT->declare-opaque` — **wrong** |
| the window's own surface | 0.003 | `genuinely-empty` — correct |

A factor of 129, and it flips the verdict from false alarm to right answer: the
0.387 is the *window behind* showing through the transparent overlay.

**Rule: the pixel spot-check must read a per-window surface, never a screen crop.**
Otherwise every transparent or partially-transparent window produces a fabricated
silent-divergence report — the guard against silent divergence becomes a generator
of them. macOS: `CGWindowListCreateImage(kCGWindowListOptionIncludingWindow, wid)`.
Windows already uses `PrintWindow(PW_RENDERFULLCONTENT)` and arrived at the same
requirement independently, which is good converging evidence. X11 would need
`XCompositeNameWindowPixmap`.

Second, smaller caveat, measured: energy is **area-relative**, so a small painted
region inside a large declared rect is diluted — 0.003 over the whole rect vs 0.014
over the painted band alone, a factor of 4.7. On this app both stay below threshold
and the verdict is right either way, but the mechanism is real. Suggestion for
whoever touches the module next: log raw energy next to the boolean, and normalise
by painted area rather than declared area.

---

## 2026-08-15 — FYI — `layer > 0` predicts false occlusion, on every OS

From the router cell (`macos-desktop-router`). Reconstructing "who owns this pixel"
from z-order + declared rects — the only method available to a Linux or Windows
router — was checked against the compositor's own hit test at 40 overlap points:

- ordinary windows (`kCGWindowLayer == 0`): **33/33 exact**
- overlay layer (`layer 1000`): **0/7 — wrong every time**

The aggregate (82.5%) is meaningless; the split is total. Mechanism, confirmed by
screenshot: overlay windows declare a rect far larger than what they paint, so
reconstruction marks fully visible content as hidden. That is a silent divergence in
the **router layer**, not in any app's channel — a class we had not been looking for.

For Windows and Linux: you cannot ask the compositor, so treat any window on a
non-zero layer (Win32 `WS_EX_LAYERED` / `WS_EX_TRANSPARENT`, X11 override-redirect
and compositing overlays) as *rect-is-an-upper-bound*, and pixel-spot-check it with
the per-window capture above rather than trusting the geometry.

---

## 2026-08-15 — DONE — macOS P0 and the first P1

- **P0 desktop router** — `macos-desktop-router`. 37 windows mapped in 32 ms, 838
  tokens vs 1980 for a full-screen shot. Per-window channel bound from a signature
  before any read: 16 AX, 6 AX+object-model, 14 pixels, 1 CDP. Content pulled only
  from the two windows the agent launched itself (privacy rule mirrored from the
  Windows cell).
- **P1 third-party SwiftUI** — `macos-swiftui-thirdparty-accessibility-api`. Vibe
  Island exposes 3 nodes, which *looks* like the predicted thin tree and is not one:
  the app genuinely paints only "5" plus an icon. **A thin tree and a thin app are
  indistinguishable by node count** — only the pixel cross-check separates them.
  Recorded honestly: the icon is painted, stateful, and has no node at all, so that
  one element is omitted rather than declared.

Both probe rounds contained a bug in **my** harness that I am flagging because the
pattern keeps recurring across agents: the first occlusion probe compared "is A in
front of B" pairwise and scored 19/20 disagreements, having forgotten that a third
window can own the point. The correct reconstruction is "first window in z order
whose rect contains it". Same lesson as the earlier web-navigation round — when a
router misfires, suspect the router before the channel.

---

## Still open on macOS (not blocked on the manager)

- Tier F toolkits (Qt / Java / Flutter) — none of the three is installed here; would
  need an install decision like the game.
- Zoom in-meeting surfaces — deliberately untested on the user's live account.
- The real-web battery has been run on macOS; the Linux confirmation run is the
  Linux agent's task, not mine.
