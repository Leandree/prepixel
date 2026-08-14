# Agent brief — macOS (read agent-brief-COMMON.md first)

macOS is the **most locked-down** OS for this study — and that makes it scientifically
important. System Integrity Protection (SIP) and code-signing/hardened-runtime block
injecting code into third-party processes, so the render-tree-tap approach that
worked on GTK is largely **unavailable** here. The sanctioned cross-app structured
channel is the **Accessibility API (AX / NSAccessibility)**. A central goal on macOS
is to document *what the OS lets you reach* and *what it blocks*, cleanly — the
blocks are results.

## Environment prep

- Grant the agent's host process **Accessibility** permission: System Settings →
  Privacy & Security → Accessibility. Also **Screen Recording** (for the screenshot
  baseline and verification crops).
- **Do NOT disable SIP.** A SIP/permission refusal is a first-class data point, not
  an obstacle to route around. Record exactly what was refused.
- Tools: Python 3 with `pyobjc` (`pip install pyobjc-framework-ApplicationServices
  pyobjc-framework-Quartz pillow`). The `atomacos`/`ApplicationServices` `AX*` calls
  are your main channel. The built-in **Accessibility Inspector** (Xcode tools) is a
  great manual cross-check.

## Channels to probe

### Tier A — Accessibility API (AX) — the general channel; try on EVERY app
AX exposes an element tree: role, title/value, `AXFrame` (bounding rect), actions
(`AXPress`…). This is macOS's structured-view equivalent, OS-sanctioned, no injection.
- Detection signature (H5): does `AXUIElementCopyAttributeValue` return a real tree
  for the app, or just a top-level window with nothing inside? The latter (common for
  custom-drawn apps) is an **explicit** "I can't see this" — record it.
- Run full T1–T6. Native Cocoa apps (TextEdit, Finder, Notes, Mail, Safari) should
  score well. For T5, use `AXFrame` center as the blind-click coordinate.

### Tier B — Native Cocoa: TextEdit, Notes, Finder, Safari, Mail
- Expect strong AX coverage (text, controls, values). Quantify token cost of the AX
  view vs a screenshot. Safari also exposes the DOM via its own remote inspector
  (Develop menu / `webkit` debugging) — probe that as a second channel and compare.

### Tier C — Chromium/Electron: Chrome, VS Code, Slack
- CDP path: launch with `--remote-debugging-port=9222` (VS Code: `code
  --remote-debugging-port=9222`). Detection: port answers. Run T1–T6, get numbers
  comparable to the Linux/Windows CDP cells.
- Electron apps also expose an AX tree (often partial) — probe both, compare.

### Tier D — Microsoft Word / Office on Mac
- No COM object model like Windows. Channels: **AX** (document text + controls) and
  possibly AppleScript (`tell application "Microsoft Word" to get content of ...`) —
  try AppleScript as a semantic "object-model-like" channel and compare its coverage
  and cost to AX and to a screenshot. This contrast with the Windows COM cell is
  itself a finding.

### Tier E — SwiftUI / Catalyst apps
- AX coverage varies; SwiftUI's AX can be thin if the developer didn't annotate.
  Where labels are missing, note whether AX *omits* them (explicit) or *fabricates*
  (silent). Good hunting ground for the silent-divergence question.

### Tier F — Non-Cocoa toolkits if present (Qt, Java, Flutter)
- Qt on macOS: AX only if Qt accessibility is on. Flutter: AX semantics tree if the
  app enabled it, else opaque. Java: AX bridge varies. Record refusals as data.

### Tier G — Pixels-only control (a game, a fullscreen video, a screen-shared window)
- Confirm the perimeter law: AX yields a bare window, structured channel useless and
  says so. Wanted negative.

## macOS-specific reporting

The headline macOS deliverables are:
1. A clean statement of **what SIP/permissions block** (render-tap unavailable;
   AX/Screen-Recording gated behind explicit user consent) — this shapes the paper's
   "who must provide this channel" argument (answer on macOS: only the OS can).
2. Per app, whether AX was **predictable** (did a real tree exist, knowable from the
   app being a Cocoa/AX-annotated app?) and whether any app returned a **silently
   wrong** AX view. Fill `failure_class` carefully: `blocked` for SIP/permission
   walls, `explicit` for honest empty trees, `silent` for divergence.
