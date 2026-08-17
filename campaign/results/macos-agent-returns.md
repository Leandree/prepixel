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

## 2026-08-15 — DECISION NEEDED — which app for the unannotated GL/Metal game cell

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
