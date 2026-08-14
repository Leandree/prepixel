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

## What's still open

VS Code AX (the user's instance closed mid-campaign; Electron-AX story sampled via
Chrome/Cursor instead), Android Studio/Swing (not launched — time-boxed out),
a true unannotated game, and Zoom in-meeting. None block the macOS verdict:
**predictable, explicit, zero silent divergences observed.**
