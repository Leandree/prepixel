# macOS — independent replication pass

**Date:** 2026-08-17 · **Host:** leandre-macbook, macOS 26.5.2 (25F84), arm64, live user session
**Agent:** claude-code (Opus 5), separate session from the one that produced the cells.

## What this is

A blind re-measurement of three load-bearing macOS cells, run to answer one question:
*could a carrying cell have gone quietly wrong?* For each cell the measurement was
re-made from zero — app relaunched, script re-run — and the original cell was read
**only afterwards**. Nothing in `campaign/results/*.json` or
`campaign/results/artifacts/` was modified: the probe scripts were run from
byte-identical copies in a session scratchpad so their hard-coded output paths
resolve outside the repository (verified with `diff -q` before each run).

**One honest caveat on blindness.** For the router cell the task statement itself
quoted the original figures (`≈838 tokens vs ≈1980`), so my blindness there was
broken before I started. The measurement was still made independently; the reader
should discount the router token comparison accordingly. Cells 1 and 3 were fully
blind.

**Environment deltas from the original runs** (all deliberate, none load-bearing —
each is called out again in the cell it affects):

| | original | this replication |
|---|---|---|
| PyObjC | present | **absent from every Python on the machine**; installed into a throwaway venv in the scratchpad, not into any system or user Python |
| JVM | JetBrains Runtime OpenJDK 21.0.10 (bundled with Android Studio) | Temurin 17.0.19 |
| desktop state | 37 windows, a Chrome with `--remote-debugging-port`, Safari and TextEdit open | 39 windows, no CDP-enabled browser, no Safari |

---

## Cell 1 — `macos-swing-accessibility-api`, act-guard axis

Re-run of `SwingProbe2.java` (recompiled, relaunched) plus `act_guard.py`, targeting
`IncrementPlain` — the `JButton` whose accessibility was never touched.

| measurement | original cell | this replication | verdict |
|---|---|---|---|
| `AXUIElementCopyActionNames` on the untouched button | `[]` | `[]` | **match** |
| `AXUIElementPerformAction(btn,'AXPress')` | returns `0` (success) | returns `0` | **match** |
| target-region state after the press | unchanged | unchanged (`countPlain=0` before and after) | **match** |
| act-guard verdict | `UNVERIFIED` | `UNVERIFIED` | **match** |
| same, on the *named* button | `UNVERIFIED` | `UNVERIFIED` | **match** |
| structured re-read cost | 38 tokens | 38 tokens | **match** |
| guarded round-trip | 507–517 ms | 506.2 / 507.6 ms | **match** |
| untouched components expose their painted text | yes | yes — `SENTINEL-PLAIN bravo`, `countPlain=0`, `IncrementPlain` all exact | **match** |
| components with `setAccessibleName` report the name instead | yes | yes — `sentinel-label`, `counter-label`, `increment-button` | **match** |

**Verdict: the act-side finding replicates exactly, on a different JVM.** The
original ran on JetBrains Runtime 21; this ran on Temurin 17 and produced identical
numbers, so the lie is a property of the AWT→NSAccessibility bridge, not of one
vendor's JVM. That is a small strengthening the original could not claim.

### Two strengthenings

**A stricter positive control.** The original's control was a *different app* (a
native AppKit Calculator button: declares `AXPress`, state changed, `CONFIRMED`).
That leaves open the objection "maybe the Swing button is simply dead." I clicked
**the same button** with a synthetic `CGEvent` at the coordinates the AX channel
itself reported (`128.5, 267.5`): `countPlain` went `0 → 1`. So the button is alive
and correctly located by the channel; only the *action* call lies.

**The return code carries no information at all.** The cell says
`kAXErrorActionUnsupported (-25206)` "exists precisely for this and is not used". It
is weaker than that. On the same window:

| call | returns |
|---|---|
| `AXPress` on the button | `0` |
| `AXIncrement` on the button | `0` |
| `AXBogusActionThatCannotExist` on the button | `0` |
| `AXPress` on an `AXStaticText` | `0` |
| `AXBogusActionThatCannotExist` on an `AXStaticText` | `0` |
| `AXConfirm` on the button | `-25200` |

The call does not validate the action name, and does not validate that the element
can act at all — an invented action on a static label returns success. It is not
"`AXPress` fails silently"; it is "`PerformAction` returns 0 for essentially
anything you name it." (`AXConfirm` returning `-25200` shows the path *can* produce
an error, so this is not a blanket stub.) This makes the cell's a-priori
recommendation — *never call perform on an element that declares no actions* —
the only usable signal, since the return value is not one.

### ÉCART — two of the cell's six test rows do not come from the run it documents

The cell states it is the controlled re-run built on `SwingProbe2.java`, and its
`t1`/`t4`/`t5` rows are consistent with that probe. But:

- `t2_enumerate`: *"10 nodes, correct roles (AXStaticText / AXButton / **AXTextField**), … 32.5 ms"*
- `t3_live_value`: *"A **JTextField**'s live contents are exposed: AXValue = 'initial'"*

`SwingProbe2.java` contains **no `JTextField`**. I walked both probes' trees:

| probe | total AX nodes | `AXTextField` present? |
|---|---|---|
| `SwingProbe2.java` — the probe the cell names | **12** | **no** |
| `SwingProbe.java` — the first, retracted probe | **10** | **yes**, `AXValue='initial'` |

So `t2` and `t3` are the **first run's** figures, carried unchanged into the cell
that explicitly retracts and replaces that run. `10` and the text field are exactly
`SwingProbe.java`'s tree. By association the `measurements` block —
`capture_latency_ms 32.5`, `view_bytes 388`, `view_tokens_est 97` — is also more
likely to describe the first probe than the second; the cell gives no separate
figure for `SwingProbe2`, whose 12-node tree cannot produce a 10-node walk.

**How much this matters, stated fairly.** The claims themselves are *true* — I
re-verified that a Swing `JTextField`'s live value is exposed as `AXValue='initial'`,
on `SwingProbe.java`. Nothing in the cell is false about Swing. What is wrong is
provenance: a cell that presents itself as "the controlled re-run after the first
version's confound was caught" carries two evidence rows from the confounded run.
The headline act-side result is untouched by this — I reproduced it from zero on
`SwingProbe2` — but a reader reconstructing the cell from `raw_artifacts` would run
`SwingProbe2.java`, count 12 nodes, find no text field, and be unable to reproduce
`t2` or `t3`.

---

## Cell 2 — `macos-desktop-router`

`router_mac.py` re-run on the live desktop, twice back-to-back after removing my own
probe window, plus one earlier run with it present.

| measurement | original cell | this replication | verdict |
|---|---|---|---|
| on-screen windows | 37 | 39 (both clean runs) | different desktop, see below |
| merged map | 838 tokens / 3351 bytes | **913 tokens / 3649 bytes** (identical across both runs) | **match, order of magnitude** |
| tokens per window | 22.6 | 23.4 | **match** |
| full-desktop screenshot | 1980 tokens | **1980 tokens** | **exact match** |
| same at Retina 2× | 4784 | **4784** | **exact match** |
| shot ÷ map ratio | 2.36× | 2.17× | **match** |
| map latency | 31.9 ms | 32.3 / 40.8 ms | **match** |
| channel bound before any content read | true for all | **39/39** | **match** |

**Verdict on the headline: match.** The merged-map cost is linear in window count
(23.4 tokens/window here, 22.6 there); my 913 against their 838 is two extra windows
on a busier desktop, not a different measurement. The screenshot side is identical
to the token, since the display is the same.

### Channel-per-window binding

| channel | original (37 win) | replication (39 win) |
|---|---|---|
| `accessibility-api` | 16 | 20 |
| `accessibility-api+object-model` | 6 | 5 (TextEdit ×1, Finder ×4) |
| `pixels-baseline` | 14 | 14 (Control Center ×13, Window Server ×1) |
| `cdp` | 1 | 0 |

**Match in structure.** The `pixels-baseline` count is identical (14) and breaks down
the same way the cell describes — menu-bar items that answer AX but expose zero
windows, plus Window Server surfaces where AX refuses. The `cdp` row is 0 simply
because no browser was running with `--remote-debugging-port` this time; Chrome was
open and was correctly bound to `accessibility-api` instead, which is the router
behaving as specified. `accessibility-api+object-model` is 5 rather than 6 because
Safari was not open. None of these are router discrepancies; they are desktop-state
differences, and the router classified each one from a signature before reading.

### ÉCART — the occlusion result: the class replicates, the clean layer split does not

| measurement | original cell | this replication |
|---|---|---|
| global z-order accuracy | 33/40 = **82.5 %** | 37/40 = **92.5 %** (identical in both clean runs) |
| on ordinary windows (`layer == 0`) | 33/33 = **100 % exact** | **32/33** |
| on the overlay layer (`layer == 1000`) | 0/7 = **0 %, wrong every single time** | **5/7 correct** |

The overlay the cell blames is the *same window*: it describes "an overlay window
declared a 748x264 rect while painting only a small opaque band inside it", and I
measure a `layer=1000`, `alpha=1.0` window with rect `[382, 0, 748, 264]`. Two of my
probe points fall inside that rect, are attributed to the overlay by z-order
reconstruction, and are attributed to VS Code by the window server. **The
false-occlusion class replicates and is real.**

What does not replicate is the cell's strongest sentence — *"the split by window
LAYER is total"* — and neither half of it survives:

**1. `layer 1000` is not 0/7.** Five of my seven overlay-layer points agreed. This
follows directly from the cell's own mechanism: if the overlay declares a large rect
and paints only a band inside it, then whether a probe point is mis-attributed
depends on **where that point lands** — on the painted band or on the transparent
remainder. The probe points are the centres of pairwise window overlaps, so they
move with the desktop. `0/7` and `2/7` are two samples of the same phenomenon; the
rate is not a property of the layer, and stating it as one ("every single time")
generalises a single sample.

**2. `layer 0` is not 100 %.** I have one ordinary-window miss, and it is a
different, narrower mechanism that the "100 % exact" claim excludes by construction.
Point `(756, 507)` sits exactly on the shared edge between a `layer=0` window
occupying `x ∈ [0, 756)` and VS Code behind it at full width. Sweeping across the
edge:

| x | rect reconstruction (half-open) | window server |
|---|---|---|
| 750, 754, 755 | left window | left window ✓ |
| **756, 757** | **VS Code** | **left window ✗** |
| 760, 800 | VS Code | VS Code ✓ |

A **2-pixel band** in which the AX hittable frame extends past the window's declared
`CGWindowBounds`. I ruled out the two cheap explanations: it is not map staleness
(re-mapped immediately before each hit test, 4× per point, stable every time), and
it is not `int()` truncation in the router (the raw bounds are exact integers —
`X=0.0 Y=33.0 W=756.0 H=949.0`).

**Honest read.** The cell's *finding* — reconstruction routers suffer a false-occlusion
class that macOS can close with one compositor call, and `layer > 0` is a free
a-priori warning — replicates and stands. The cell's *presentation* of it as a total,
clean dichotomy (100 % / 0 %) is a single-desktop artifact. A second disagreement
class exists on layer 0 at shared window edges; it is far less consequential (2 px
against a 748×264 region) but it means the split is not total, and a paper claiming
"100 % exact on ordinary windows" would be overstating what one sample supports.

---

## Cell 3 — `macos-games-pixels-baseline` (DiRT 4 arm)

Steam and DiRT 4 launched from cold, in one process, and probed at every state.
`probe_game.py` re-run unmodified.

| measurement | original cell | this replication | verdict |
|---|---|---|---|
| **Feral launcher** — AX nodes | 31 | **31** | **exact** |
| launcher — nodes carrying text | 24 | **24** | **exact** |
| launcher — buttons | 11 | **11** | **exact** |
| launcher — `AXWebArea` present | yes | **yes** | **exact** |
| launcher — checkbox + popup | 1 + 1 | **1 `AXCheckBox` + 1 `AXPopUpButton`** | **exact** |
| `AXPress` on the launcher's *Jouer* button | `err 0`, game started | **`err 0`, game started** | **exact** |
| **in game** — AX tree | 1 node, `AXWindow`, 0 children, depth 0 | **1 node, `AXWindow`, 0 children, depth 0** | **exact** |
| in game — client area | 1512×982 | **1512×982** | **exact** |
| in game — screenshot cost | 1980 tokens | **1980 tokens** | **exact** |
| same pid across both states | yes | **yes, pid 69480 throughout** | **exact** |
| sampling | 5× over 2 min | **7× across 4 distinct game states** | match, extended |

**Verdict: exact match on every published figure, and the boundary the cell carries
— "annotation, not category" — holds.** The launcher's 31-node, 24-text,
11-button, fully addressable UI collapses to a single node in the *same process*
seconds later.

Additional measurements are also in
`campaign/results/verification/artifacts-macos/`: launcher and pause-menu AX probes,
the four in-race AX samples, and two screenshots.

### Extension: the collapse is not about 3D

Léandre asked mid-run to get past the menus and actually into the game, so I drove.
Every state below returned **one node, `title=DiRT 4`, zero children, zero
geometry**:

| game state | what is legibly on screen | AX nodes |
|---|---|---|
| title screen | "DiRT 4", "APPUYEZ SUR START OU ENTRÉE" | 1 |
| event briefing | ~20 strings: event name, "ÉPREUVE 2/3 · DEMI-FINALE", circuit, "0,60 km", surface, weather | 1 |
| **in race** (throttle held, 4 samples 1.6 s apart) | lap 1/4, race clock 00:33.065, position "3E", a 6-name live leaderboard, "127 KM/H", gear 4 | 1 each |
| **the engine's own PAUSE menu** | 6 focusable entries: CONTINUER / RECOMMENCER / OPTIONS / ABANDON COURSE / ABANDONNER L'ÉPREUVE / QUITTER | 1 |

The last row is the one the original did not measure and is the strongest form of
the cell's claim. It is easy to read "a game is pixels territory" as "3D content is
opaque". It is not: a conventional, keyboard-navigable **menu**, with focus and a
highlighted selection, drawn by the same engine, is equally invisible. The predictor
is neither rendering technology nor app category nor even widget-ness — it is
whether the surface on screen is an annotated AppKit/Web view or an engine-drawn
drawable. Probing that costs 0.7–0.8 ms warm, precisely because there is nothing
there to walk.

The failure stays **explicit** throughout: `AXWindows` returns `err 0` with one
window and an empty child list. The channel never returned anything that was not on
screen — it returned almost nothing, and said so.

### Minor unexplained difference

The cell records `view_bytes 24 / view_tokens_est 6` for the in-game view. The
single node serialises here as `title=DiRT 4` — 12 bytes, 3 tokens. An accounting
difference in how a 1-node view is rendered to text, not a divergence in the
finding; both are "the view is a rounding error against 1980 image tokens".

### Scope not covered

The original cell has a second arm, **Cuphead (Unity)**, which I did not re-run —
the task asked for the single-process state contrast, which is the DiRT 4 arm.
Cuphead's numbers in that cell are **not** replicated by this pass.

---

## Summary

| cell | headline claim | verdict |
|---|---|---|
| `macos-swing-accessibility-api` (act side) | `AXPress` returns 0 on an untouched Swing button, nothing happens, act-guard says `UNVERIFIED` | **match** — exact, on a different JVM; strengthened by a same-button positive control and by the finding that the return code validates neither the action name nor the element |
| `macos-swing-accessibility-api` (t2/t3 rows) | 10 nodes incl. `AXTextField`, live value `'initial'` | **écart** — those are the retracted first probe's numbers; `SwingProbe2.java` has 12 nodes and no text field. Claims true, provenance wrong |
| `macos-desktop-router` (cost) | ≈838 map tokens vs 1980 for a full-screen shot; channel bound per window before reading | **match** — 913 vs 1980 on a 39-window desktop, 23.4 tokens/window vs 22.6, binding predicted 39/39 |
| `macos-desktop-router` (occlusion) | layer 0 → 100 % exact, layer 1000 → 0 %, "the split by layer is total" | **écart** — class replicates (same overlay, same mechanism), rates do not: 32/33 and 5/7. Plus a second class the dichotomy excludes: a 2-px hit-test/`CGWindowBounds` mismatch at shared window edges |
| `macos-games-pixels-baseline` (DiRT 4) | launcher 31 nodes → 1 node in-game, same pid; "annotation, not category" | **match** — every published figure exact; extended in-race and to the engine's own menu, which is equally invisible |

**Net:** no carrying cell was silently wrong in its headline. Two cells overstate,
in different ways: the Swing cell attributes two evidence rows to a probe that cannot
have produced them, and the router cell promotes one desktop's occlusion sample to a
categorical law that a second desktop does not support. Both are fixable by
rewording rather than by re-measuring, and neither touches the result each cell is
carried for.

---

## Disclosures

- **I entered Léandre's DiRT 4 career save.** Pressing Enter at the title screen
  auto-resumed an in-progress event (Coupe RX Super 1600, épreuve 2/3, demi-finale);
  `ESC` was inoperative at the briefing screen, which offers only CONTINUER, so I
  raced roughly 35 s of it to take the in-race measurement. I left via Pause →
  QUITTER → OUI, whose own confirmation reads *"toute progression non sauvegardée
  sera perdue"*, so the career should be exactly as found. **I did not verify the
  save file** — worth a glance next time the game is opened.
- **Steam is still running.** The game launch started it (it was not running
  before); a scripted quit was refused (AppleScript `-128`). Harmless, but it is a
  residue of this pass, not the machine's prior state.
- **PyObjC was installed** into a throwaway venv under the session scratchpad, since
  no Python on the machine had it. No system or user Python was modified. Any future
  macOS cell will hit the same wall — worth a line in `agent-brief-macos.md`.
- **Actions taken beyond reading:** compiling and running two throwaway Swing
  windows; one synthetic click and several `AXPress` calls on those windows;
  launching, driving and quitting DiRT 4; keystrokes to DiRT 4 only. No user file was
  opened, modified or sent.
- **Privacy:** the router maps the whole live desktop. Only aggregates were kept —
  `router-replication-aggregate.json` holds counts, token totals and the occlusion
  disagreements (app names only). No window titles and no per-window rows of
  Léandre's desktop were written to the repository.
