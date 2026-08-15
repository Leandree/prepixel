# Coverage matrix & predictability (aggregated)

27 result cells. Legend: ✅ works · 🟡 partial · ⬜ unavailable (structure yields nothing) · ⛔ blocked (OS/env).

## Coverage matrix

| OS | App | Stack | Channel | Verdict | Failure | View tok | Shot tok | Predictable a priori? |
|----|-----|-------|---------|---------|---------|---------:|---------:|:---------------------:|
| linux | Chromium / Chrome DevTools Protocol (covers all Electron apps: VS Code, Slack, Discord, Teams) | chromium | cdp | ✅ works | explicit | 308 | 1,366 | ✅ |
| linux | Native OS-level blind click driven by structured coordinates | chromium | cdp | 🟡 partial | blocked |  | 1,366 | ✅ |
| linux | Precision-vs-pixels duel (20 randomized order-console pages) | chromium | cdp | ✅ works | — | 391 | 1,366 | ✅ |
| linux | Adversarial: occlusion & visibility tricks (the safety-claim stress test) | chromium | cdp | ✅ works | explicit |  | 1,366 | ✅ |
| linux | All-canvas 'game' page (perimeter-law control) | custom-canvas | pixels-baseline | ⬜ unavailable | explicit | 7 | 1,366 | ✅ |
| linux | GNOME Text Editor — hard-text stress (ligatures, accents, RTL Arabic, emoji, CJK) | gtk4 | render-tree-tap | ✅ works | explicit |  | 1,366 | ✅ |
| linux | GNOME Calculator 46.3 | gtk4 | accessibility-api | ⛔ blocked | blocked |  | 1,366 | ✅ |
| linux | GNOME Text Editor 46.3 | gtk4 | render-tree-tap | ✅ works | — | 3,577 | 1,366 | ✅ |
| linux | GTK4 Widget Factory — animated | gtk4 | render-tree-tap | ✅ works | — |  | 1,366 | ✅ |
| linux | LibreOffice Writer | office-native | object-model | ✅ works | — | 21 | 1,366 | ✅ |
| linux | Whole desktop — 4 concurrent windows, 4 toolkits (Chromium, GTK4, Qt, LibreOffice) | other | render-tree-tap | ✅ works | explicit | 30 | 3,110 | ✅ |
| linux | Qt Widgets (examples/widgets/calculator) — representative Qt app | qt | render-tree-tap | ⬜ unavailable | explicit |  | 1,366 | ✅ |
| macos | Finder (system file manager), probe folder with 3 throwaway files | appkit | accessibility-api | ✅ works | — | 4,345 | 1,049 | ✅ |
| macos | TextEdit — hard-text stress (ligatures, combining accents, CJK, RTL Arabic/Hebrew, bidi, ZWJ emoji) | appkit | accessibility-api | ✅ works | — | 35 | 1,281 | ✅ |
| macos | Pages 14.x (iWork word processor) | appkit | object-model | ✅ works | — | 21 | 1,285 | ✅ |
| macos | Safari (system WebKit browser), pages/testapp.html + allcanvas.html | appkit | accessibility-api | ✅ works | explicit | 2,957 | 1,914 | ✅ |
| macos | TextEdit (com.apple.TextEdit) | appkit | accessibility-api | ✅ works | explicit | 1,760 | 1,526 | ✅ |
| macos | Google Chrome 151.0.7922.138 (isolated instance, temp profile) | chromium | accessibility-api | 🟡 partial | explicit | 4,948 | 880 | ✅ |
| macos | Google Chrome 151.0.7922.138 (isolated instance, temp profile) | chromium | cdp | ✅ works | explicit | 315 | 880 | ✅ |
| macos | Precision-vs-pixels duel (20 randomized order-console pages) — macOS replication of the Linux cell | chromium | cdp | ✅ works | — | 391 | 1,366 | ✅ |
| macos | Adversarial: occlusion, visibility tricks & undeclared blind spots (the safety-claim stress test) | chromium | cdp | ✅ works | explicit | 57 | 1,366 | ✅ |
| macos | All-canvas 'game' page + mixed opaque page (perimeter-law control) | custom-canvas | pixels-baseline | ⬜ unavailable | explicit | 7 | 1,366 | ✅ |
| macos | Cursor 2.x (VS Code fork, Electron/Chromium 144) — isolated instance, temp profile | electron | cdp | ✅ works | explicit | 647 | 1,366 | ✅ |
| macos | Chess/Échecs (com.apple.Chess) — Apple's 3D-rendered chess game | game | accessibility-api | ✅ works | — | 3,050 | 921 | ✅ |
| macos | Render-tap feasibility on macOS (targets: TextEdit as a system/platform binary, Google Chrome as a hardened third-party app) | other | render-tree-tap | ⛔ blocked | blocked |  | 1,366 | ✅ |
| macos | Zoom Workplace 6.x (us.zoom.xos) — home window, logged in, NOT in a meeting | other | accessibility-api | ✅ works | — | 1,712 | 878 | ✅ |
| macos | Clock/Horloge (com.apple.clock, system SwiftUI app) — world clock + stopwatch | swiftui | accessibility-api | ✅ works | — | 634 | 1,049 | ✅ |

## Predictability & safety (H5)

The production-safety question: could a router know the channel in advance, and does failure stay explicit (never silent)?

| Stack signature | Channel | Coverage verdict | Failure mode |
|-----------------|---------|------------------|--------------|
| com.apple.finder; full window tree on first query (no AT-latch) | accessibility-api | ✅ works | — |
| com.apple.TextEdit; AXTextArea advertises AXBoundsForRange / AXRangeForPosition / AXStringForRange | accessibility-api | ✅ works | — |
| tell application "Pages" responds; NSAppleScriptEnabled bundle | object-model | ✅ works | — |
| com.apple.Safari; AXWindows returns a standard window; AXWebArea appears under the tab group only after the AT latch flips | accessibility-api | ✅ works | explicit |
| bundle com.apple.TextEdit; AXUIElementCreateApplication(pid) returns full window tree (45 nodes) in 41 ms | accessibility-api | ✅ works | explicit |
| --remote-debugging-port responds on the target process (Electron apps expose the same) | cdp | ✅ works | explicit |
| CDP responds | cdp | 🟡 partial | blocked |
| n/a | cdp | ✅ works | — |
| AXUIElementCreateApplication(pid) answers, but see notes: content is LAZY — first shallow probe returned 72 nodes of window chrome only (page text absent) | accessibility-api | 🟡 partial | explicit |
| http://127.0.0.1:9223/json/version → Chrome/151.0.7922.138, Protocol 1.3 | cdp | ✅ works | explicit |
| single CANVAS element covering the viewport; DOM has no text/interactive nodes inside it | pixels-baseline | ⬜ unavailable | explicit |
| http://127.0.0.1:9224/json/version → Chrome/144.0.7559.236; app warns 'remote-debugging-port is not in the list of known options, but still passed to Electron/Chromium' | cdp | ✅ works | explicit |
| com.apple.Chess; every piece an AXButton on first walk | accessibility-api | ✅ works | — |
| libgtk-4.so; text nodes name their font per run | render-tree-tap | ✅ works | explicit |
| org.a11y.Bus not activatable in headless sandbox; app does not register | accessibility-api | ⛔ blocked | blocked |
| libgtk-4.so.1 mapped; renderer submits via gsk_renderer_render() | render-tree-tap | ✅ works | — |
| libgtk-4.so; gsk_renderer_render per frame | render-tree-tap | ✅ works | — |
| soffice.bin running; UNO endpoint 'socket,port=2002;urp' accepts a connection | object-model | ✅ works | — |
| libgtk-4.so | libQt5*.so | soffice | chromium binary — one per window | render-tree-tap | ✅ works | explicit |
| csrutil status = enabled; Chrome CodeDirectory flags=0x12a00 (kill, restrict, library-validation, runtime); TextEdit is a platform binary under /System | render-tree-tap | ⛔ blocked | blocked |
| us.zoom.xos; home window exposes 100+ nodes incl. 3 embedded AXWebArea (hybrid native+web UI) | accessibility-api | ✅ works | — |
| libQt5Gui.so / libQt5Widgets.so mapped (or Qt6 equivalents) | render-tree-tap | ⬜ unavailable | explicit |
| com.apple.clock; window tree 25 nodes with labeled toolbar tabs on first query | accessibility-api | ✅ works | — |

## Safety verdict

- Cells where structure **works**: 20/27.
- **Silent divergences** (disqualifying): 0/27 ✅ none found
- Cells **not** predictable in advance: 0/27 ✅ none

Reading: every failure so far is either **explicit** (opaque rect / honest empty tree) or **blocked** (OS/env), and every channel was detectable from a stack signature before use. That is the pattern a production router needs. The open risk to hunt on the other OSes is any **silent** cell — a channel that returns a view disagreeing with the screen without declaring it.
