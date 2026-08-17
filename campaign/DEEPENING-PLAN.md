# Deepening plan — close every open question before the paper

Status after three OS campaigns + the Linux desktop round: **63 cells, 63/63
schema-valid, 4 silent divergences (3 Windows + 1 Linux/qBittorrent, all
predictable a priori), 0 unpredictable.** The thesis
is no longer "structure is always safe" — Windows disproved that honestly — it is:
**every channel's coverage is predictable in advance from a stack signature, every
failure is either explicit or convertible-to-explicit by a documented router guard,
and the one disqualifying mode (silent divergence) is exactly characterized and
mitigated.** This plan lists what still has to be shown so a reader is left with no
open question. Each task has an **acceptance criterion** — the concrete artifact
that closes it.

Priorities: **P0 = changes the paper's message; P1 = closes a named open question a
reviewer will ask; P2 = completes the matrix / nice-to-have.**

---

## Already done in-sandbox this round (Linux, cross-OS modules)

- **P0 — Silent→explicit mitigation** (`src/coverage-guard.mjs`): pixel spot-check
  (content-energy) + view self-consistency. Verified on native-mimicry shapes:
  FL-Studio-style painted panes (energy 0.07) and OBS-style preview (0.06) flagged,
  genuinely-empty dock (0.00) not flagged, rekordbox "32 Tracks + 0 rows" caught
  view-only. This is the module every OS agent should now RUN against its real
  silent cells (see P0 tasks below).
- **P1 — Coordinate-frame calibration** (`pages/click-dpr.html`): showed the
  box→input scale is platform-dependent (headless Chromium: frames agree; macOS
  Retina: they don't) → the router must self-calibrate, never hardcode `/DPR`.

---

## WINDOWS agent

### P0 — Prove the mitigation ON the real silent apps (the single most important run)
Re-open FL Studio, OBS, and rekordbox (READ-ONLY, allowlisted, user's real config).
For each silent region, run the mitigation: (1) compute structural-coverage % of the
client area; (2) `PrintWindow(PW_RENDERFULLCONTENT)` the region and feed the crop to
`coverage-guard.contentEnergy`; (3) apply `selfConsistency` to the view.
- **Acceptance:** each of the three silent cells re-emitted as **explicit**
  (`[pixels] group … [unverified: pixels show content]` and/or the count/rows flag),
  with the pixel-crop cost and the a-priori signature that triggered the check.
  Update each JSON's `failure_class` to `explicit` with a `mitigation` note; the
  aggregate then reads **0 silent survivors, 3 caught-and-declared**.

### P1 — Demonstrate the coordinate trap live at 125% or 150% scaling
This panel ran at 100%; the UIA physical-px vs DPI-unaware virtualized-px miss is
encoded, not shown.
- **Acceptance:** one blind click that MISSES under a naive frame and HITS after the
  calibration probe, on a scaled display, with both coordinates logged.

### P2 — Fill the two missing tiers
A **WPF** app and a **Java (Access Bridge)** app — install one representative each.
- **Acceptance:** one T1–T6 cell each, or an explicit "channel unavailable/blocked"
  with the signature, so the tier is not simply absent.

---

## macOS agent

### P0 — The desktop router / merged view (Linux ✅ Windows ✅ macOS ✗)
All primitives exist: `CGWindowList` (z-order, geometry) +
`AXUIElementCopyElementAtPosition` (cross-window occlusion in one call) + per-window
channel binding. Build the merged semantic desktop and extract the focused window.
- **Acceptance:** a `macos-desktop-router.json` mirroring the Linux/Windows cells —
  N windows mapped with per-window channel + verdict, focused-window content pulled
  live, cross-window occlusion resolved via ElementAtPosition, token cost of the
  merged map vs a full screenshot.

### P1 — A third-party SwiftUI app (the real thin-tree test)
Only Apple's well-annotated Clock was sampled; the README's prime thin-tree suspect
is an indie SwiftUI app.
- **Acceptance:** one cell; if AX is thin, that is a positive finding — record
  whether it OMITS (explicit) or FABRICATES (silent), and run coverage-guard on it.

### P1 — A genuinely unannotated GL/Metal game
Chess refuted "game = pixels" because Apple annotated it. Test one with no AX.
- **Acceptance:** a cell confirming frame-only/empty tree → explicit `0% coverage →
  pixels`, i.e. the honest pixels-territory control.

---

## LINUX agent — ✅ DONE 2026-08-17 (debian-server, headless + Xvfb, no root)

### P1 — AT-SPI in a real session ✅
The reference cell had it `blocked` (no a11y bus headless). **Result:** the block
was a sandbox artifact — under plain dbus-run-session the a11y bus D-Bus-activates
headlessly. T1–T6 on Mousepad/GTK3 (68 tok, 0-cost idle, 21 B/keystroke events,
blind context-menu click verified in-channel) and FeatherPad/Qt6 (331 tok, same
event vocabulary, zero client-code changes between toolkits). The Qt thin-tree
risk CONFIRMED on qBittorrent: SpeedPlotView = nameless kids=0 filler vs a live
painted chart → `failure_class: silent` (the 4th silent cell, first non-Windows).
Coverage-guard twist: contentEnergy 0.020 < threshold 0.03 → the shipped
calibration MISSES it; empty control = 0.000 on all metrics, so 0.01 or an edge
metric separates perfectly. See linux-qt6-*.json + linux-FINDINGS round 4.

### P1 — Real-web battery + blind navigation on Linux Chrome ✅
**Result:** replicated number-for-number (ratio of totals 1.00x vs 0.98x, median
1.15x identical, same 10/16 wins, three category ratios identical to the
hundredth, 8/8 navigation, MDN toggle = same +16 view lines as macOS). The ratio
is a property of the page, confirmed cross-OS. See linux-web-battery-cdp.json.

### P2 — End-to-end native blind click ✅
**Result:** the old blocked CDP+xdotool run passed first try (IDLE→CLICKED), plus
GTK context-menu and Qt menubar/tab variants — 4/4 first-attempt, all coords from
the channel, all effects verified in the channel. See linux-native-blind-click.json.

---

## Cross-cutting (any agent; some already mine)

- **P1 — One unified "when to use prepixel" figure/table** for the paper: the
  regime map (change / high-DPI / document-model / grounding → structure wins;
  dense static text / games / custom-drawn-unannotated → pixels or guard-then-pixels)
  with the measured ratios per regime across all three OSes. **Acceptance:** a single
  figure generated from `matrix.json`.
- **P1 — Diff-streaming session simulation:** the biggest efficiency lever is
  send-once-then-deltas + prompt-cache reuse. Simulate a 20-step session and report
  cumulative structured-diff tokens vs per-step screenshots. **Acceptance:** one cell
  with the cumulative curve (structure amortizes, screenshots don't).
- **P2 — Distiller dedupe pass** (Windows noted XAML dual-role ~10% inflation):
  implement + measure the token clawback. **Acceptance:** before/after token delta.

---

## Definition of done (what "no open questions" means)

1. **0 silent survivors** in the aggregate: every silent cell carries a `mitigation`
   that re-derives it as explicit via coverage-guard. (P0 Windows.)
2. **The merged-view router exists on all three OSes.** (P0 macOS.)
3. **The coordinate trap is demonstrated, not just encoded**, on a scaled display.
   (P1 Windows — sandbox already showed the two regimes + the calibrate rule.)
4. **Every tier is either measured or explicitly blocked-with-signature** — no tier
   silently absent.
5. **The efficiency story is quantified** (diff-streaming session curve), so the
   real-web ~parity is contextualized as "per-screen parity, per-session win."
6. **One regime table** tells a reader exactly when the method wins and loses.

When 1–6 are green, the safety and cost claims are both closed and the paper has no
dangling "but what about…". Everything below P1 is polish.
