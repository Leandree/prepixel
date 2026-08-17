# Coverage matrix & predictability (aggregated)

61 result cells. Legend: ✅ works · 🟡 partial · ⬜ unavailable (structure yields nothing) · ⛔ blocked (OS/env).

## Coverage matrix

| OS | App | Stack | Channel | Verdict | Failure | View tok | Shot tok | Predictable a priori? |
|----|-----|-------|---------|---------|---------|---------:|---------:|:---------------------:|
| linux | Chromium / Chrome DevTools Protocol (covers all Electron apps: VS Code, Slack, Discord, Teams) | chromium | cdp | ✅ works | explicit | 308 | 1,366 | ✅ |
| linux | Coordinate-frame trap: calibrate, don't assume (generalizes the macOS Retina miss) | chromium | cdp | ✅ works | explicit |  |  | ✅ |
| linux | MITIGATION: converting silent divergences to explicit (answers Windows FL Studio/OBS/rekordbox) | chromium | cdp | ✅ works | — |  | 1,366 | ✅ |
| linux | Diff-streaming session simulation (the per-session efficiency story) | chromium | cdp | ✅ works | — | 626 | 28,686 | ✅ |
| linux | Hard-text battery via the CDP structured channel (mirror of macOS AX hard-text) | chromium | cdp | ✅ works | — |  | 1,366 | ✅ |
| linux | Adversarial round 2: leak audit of our own hardened distiller (mirror+extension of the macOS self-audit) | chromium | cdp | ✅ works | explicit |  | 1,366 | ✅ |
| linux | Native OS-level blind click driven by structured coordinates | chromium | cdp | 🟡 partial | blocked |  | 1,366 | ✅ |
| linux | Precision-vs-pixels duel (20 randomized order-console pages) | chromium | cdp | ✅ works | — | 391 | 1,366 | ✅ |
| linux | Retina/DPR image-token two-tier replication (mirror of macOS finding) | chromium | cdp | ✅ works | — | 438 | 4,784 | ✅ |
| linux | Adversarial: occlusion & visibility tricks (the safety-claim stress test) | chromium | cdp | ✅ works | explicit |  | 1,366 | ✅ |
| linux | Real-web battery + blind navigation (macOS cells) — Linux replication attempt | chromium | cdp | ⛔ blocked | blocked |  |  | ✅ |
| linux | All-canvas 'game' page (perimeter-law control) | custom-canvas | pixels-baseline | ⬜ unavailable | explicit | 7 | 1,366 | ✅ |
| linux | GNOME Text Editor — hard-text stress (ligatures, accents, RTL Arabic, emoji, CJK) | gtk4 | render-tree-tap | ✅ works | explicit |  | 1,366 | ✅ |
| linux | GNOME Calculator 46.3 | gtk4 | accessibility-api | ⛔ blocked | blocked |  | 1,366 | ✅ |
| linux | GNOME Chess — annotated-game boundary at the RENDER-TREE level (counterpart of macOS Chess via AX) | gtk4 | render-tree-tap | 🟡 partial | explicit |  | 1,366 | ✅ |
| linux | GNOME Text Editor 46.3 | gtk4 | render-tree-tap | ✅ works | — | 3,577 | 1,366 | ✅ |
| linux | GTK4 Widget Factory — animated | gtk4 | render-tree-tap | ✅ works | — |  | 1,366 | ✅ |
| linux | LibreOffice Writer — object-model WRITE path (mirror of macOS Pages read+write) | office-native | object-model | ✅ works | — |  | 1,366 | ✅ |
| linux | LibreOffice Writer | office-native | object-model | ✅ works | — | 21 | 1,366 | ✅ |
| linux | Whole desktop — 4 concurrent windows, 4 toolkits (Chromium, GTK4, Qt, LibreOffice) | other | render-tree-tap | ✅ works | explicit | 30 | 3,110 | ✅ |
| linux | Qt Widgets (examples/widgets/calculator) — representative Qt app | qt | render-tree-tap | ⬜ unavailable | explicit |  | 1,366 | ✅ |
| macos | Finder (system file manager), probe folder with 3 throwaway files | appkit | accessibility-api | ✅ works | — | 4,345 | 1,049 | ✅ |
| macos | TextEdit — hard-text stress (ligatures, combining accents, CJK, RTL Arabic/Hebrew, bidi, ZWJ emoji) | appkit | accessibility-api | ✅ works | — | 35 | 1,477 | ✅ |
| macos | Pages 14.x (iWork word processor) | appkit | object-model | ✅ works | — | 21 | 1,285 | ✅ |
| macos | Safari (system WebKit browser), pages/testapp.html + allcanvas.html | appkit | accessibility-api | ✅ works | explicit | 2,957 | 1,914 | ✅ |
| macos | TextEdit (com.apple.TextEdit) | appkit | accessibility-api | ✅ works | explicit | 1,760 | 1,526 | ✅ |
| macos | Google Chrome 151.0.7922.138 (isolated instance, temp profile) | chromium | accessibility-api | 🟡 partial | explicit | 4,948 | 880 | ✅ |
| macos | Google Chrome 151.0.7922.138 (isolated instance, temp profile) | chromium | cdp | ✅ works | explicit | 315 | 880 | ✅ |
| macos | Precision-vs-pixels duel (20 randomized order-console pages) — macOS replication of the Linux cell | chromium | cdp | ✅ works | — | 391 | 1,366 | ✅ |
| macos | Adversarial: occlusion, visibility tricks & undeclared blind spots (the safety-claim stress test) | chromium | cdp | ✅ works | explicit | 57 | 1,366 | ✅ |
| macos | 16 live public websites in Chrome 151 (6 categories: vitrine, presse, commerce, media, reference, webapp, webapp-canvas) | chromium | cdp | ✅ works | explicit | 1,397 | 1,366 | ✅ |
| macos | Blind navigation on 5 live sites in Chrome 151 (Hacker News, Wikipedia, GitHub, MDN, DuckDuckGo) | chromium | cdp | ✅ works | explicit | 16,826 | 12,294 | ✅ |
| macos | All-canvas 'game' page + mixed opaque page (perimeter-law control) | custom-canvas | pixels-baseline | ⬜ unavailable | explicit | 7 | 1,366 | ✅ |
| macos | Cursor 2.x (VS Code fork, Electron/Chromium 144) — isolated instance, temp profile | electron | cdp | ✅ works | explicit | 647 | 1,366 | ✅ |
| macos | Chess/Échecs (com.apple.Chess) — Apple's 3D-rendered chess game | game | accessibility-api | ✅ works | — | 3,050 | 921 | ✅ |
| macos | Render-tap feasibility on macOS (targets: TextEdit as a system/platform binary, Google Chrome as a hardened third-party app) | other | render-tree-tap | ⛔ blocked | blocked |  | 1,366 | ✅ |
| macos | Zoom Workplace 6.x (us.zoom.xos) — home window, logged in, NOT in a meeting | other | accessibility-api | ✅ works | — | 1,712 | 878 | ✅ |
| macos | Clock/Horloge (com.apple.clock, system SwiftUI app) — world clock + stopwatch | swiftui | accessibility-api | ✅ works | — | 634 | 1,049 | ✅ |
| windows | Google Chrome 151.0.7922.138 (isolated instance, temp profile, repo test pages) | chromium | cdp | ✅ works | explicit | 273 | 1,366 | ✅ |
| windows | Google Chrome 151.0.7922.138 (isolated instance, temp profile) — DUAL channel of windows-chrome-cdp, same page | chromium | accessibility-api | ✅ works | explicit | 969 | 1,560 | ✅ |
| windows | Precision-vs-pixels duel (20 randomized order-console pages) — Windows replication of the Linux/macOS cells, same generator, same seeds | chromium | cdp | ✅ works | — | 391 | 1,366 | ✅ |
| windows | FL Studio 2025 (Producer Edition v25.1.6) — fully custom-drawn UI (Delphi, TFruityLoopsMainForm), READ-ONLY probe, zero input sent | custom-canvas | accessibility-api | 🟡 partial | explicit | 127 | 2,642 | ✅ |
| windows | rekordbox 7.0.9 (Pioneer DJ, JUCE framework — fully custom-drawn like FL Studio), user's real library, READ-ONLY probe | custom-canvas | accessibility-api | 🟡 partial | explicit | 2,003 | 2,584 | ✅ |
| windows | VS Code (Electron/Chromium 148) — isolated instance, temp profile, throwaway workspace | electron | cdp | ✅ works | explicit | 648 | 1,366 | ✅ |
| windows | Unigine Heaven Benchmark 4.0 (Direct3D11, windowed 1280x720) — real-time 3D scene at ~317 fps | game | pixels-baseline | ⬜ unavailable | explicit | 59 | 1,285 | ✅ |
| windows | Microsoft Word via COM (the brief's Tier C 'star case') / LibreOffice via UNO as fallback | office-native | object-model | ⛔ blocked | blocked |  |  | ✅ |
| windows | Microsoft Word 16.0 via COM automation — the brief's Tier C star case: the document itself, above any render tree. Throwaway document, closed without saving | office-native | object-model | ✅ works | — | 18 | 1,446 | ✅ |
| windows | Whole desktop — 10 concurrent visible windows, 6 process families (elevated WinUI, Chromium x2 modes, Electron, WinUI Notepad, Terminal, Win32 dialog, shell) | other | accessibility-api | ✅ works | explicit | 201 | 2,765 | ✅ |
| windows | Distiller dedupe pass (DEEPENING-PLAN P2 cross-cutting): closing the XAML dual-role inflation, measured before/after on 9 real app views | other | accessibility-api | ✅ works | — | 8,637 |  | ✅ |
| windows | Display-scaling / image-token two-tier measurement (Windows counterpart of the macOS Retina and Linux DPR cells) | other | pixels-baseline | ✅ works | — |  | 2,765 | ✅ |
| windows | OBS Studio 31.0.3 (Qt 6 Widgets) — user's real config, READ-ONLY probe | qt | accessibility-api | 🟡 partial | explicit | 1,229 | 1,275 | ✅ |
| windows | Swing probe app — the Java tier (DEEPENING-PLAN P2): UIA shape + coverage-guard + the Java Access Bridge channel end-to-end | swing | java-access-bridge | ✅ works | explicit | 52 | 167 | ✅ |
| windows | File Explorer via Shell.Application COM — the shell's document model (object-model twin of windows-explorer-uia) | win32-gdi | object-model | ✅ works | — | 28 | 974 | ✅ |
| windows | File Explorer (Win11, CabinetWClass shell window: Win32 list view + XAML islands toolbar/breadcrumb) | win32-gdi | accessibility-api | ✅ works | — | 1,470 | 974 | ✅ |
| windows | LIVE coordinate-trap demo at 125% scaling (DEEPENING-PLAN P1): one blind click that MISSES under the naive frame and HITS after self-calibration | win32-gdi | accessibility-api | ✅ works | — |  |  | ✅ |
| windows | Date and Time dialog (timedate.cpl) — legacy Win32/GDI dialog with a custom-drawn analog clock | win32-gdi | accessibility-api | ✅ works | — | 280 | 299 | ✅ |
| windows | Calculator (Microsoft.WindowsCalculator, WinUI/XAML UWP) | winui-xaml | accessibility-api | ✅ works | — | 666 | 243 | ✅ |
| windows | Notepad 11.x (Win11, tabbed, WinUI 3 shell + custom DirectWrite edit control WinUIEdit.dll) | winui-xaml | accessibility-api | ✅ works | — | 502 | 1,756 | ✅ |
| windows | Paint (Win11 WinUI rewrite) — blank throwaway canvas | winui-xaml | accessibility-api | ✅ works | explicit | 1,901 | 1,770 | ✅ |
| windows | Task Manager (Win11 WinUI rewrite, custom-drawn performance graphs) | winui-xaml | accessibility-api | ⛔ blocked | blocked |  | 2,765 | ✅ |
| windows | WPF probe app (PresentationFramework hosted via PowerShell/XamlReader — no SDK needed): TextBox, Button+counter, CheckBox, Canvas subtree | wpf | accessibility-api | ✅ works | — | 130 | 314 | ✅ |

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
| n/a | cdp | ✅ works | explicit |
| CDP responds | cdp | 🟡 partial | blocked |
| AXUIElementCreateApplication(pid) answers, but see notes: content is LAZY — first shallow probe returned 72 nodes of window chrome only (page text absent) | accessibility-api | 🟡 partial | explicit |
| http://127.0.0.1:9223/json/version → Chrome/151.0.7922.138, Protocol 1.3 | cdp | ✅ works | explicit |
| http://127.0.0.1:9231/json/version -> Chrome/151.0.7922.138, Protocol 1.3 | cdp | ✅ works | explicit |
| first UIA walk returns 257 nodes of browser chrome WITHOUT page content (the stub); the walk itself is the assistive-client signal — 328 nodes WITH full page content by the second walk, t+1.4 s. No --force-renderer-accessibility needed | accessibility-api | ✅ works | explicit |
| chromium.launch on the installed chrome.exe; same duel.mjs page generator (mulberry32, seeds 1000+97i) | cdp | ✅ works | — |
| single CANVAS element covering the viewport; DOM has no text/interactive nodes inside it | pixels-baseline | ⬜ unavailable | explicit |
| TFruityLoopsMainForm window class (Delphi/VCL custom); oleacc.dll + uiautomationcore.dll loaded (minimal a11y layer); first UIA walk returns 52 nodes that are ALL PaneControl — zero interactive control types, zero value patterns. That shape IS the router's predictor: 'custom-drawn, region map only' | accessibility-api | 🟡 partial | explicit |
| JUCE_* window class; UIA answers with a RICH 549-node tree (141 named buttons, 17 sliders, radios, combos, 11 table headers) — JUCE >=6.1 ships an accessibility layer and Pioneer wired it. Predictor refined: custom-drawn + JUCE class -> expect annotated chrome, verify list contents separately | accessibility-api | 🟡 partial | explicit |
| http://127.0.0.1:9224/json/version → Chrome/144.0.7559.236; app warns 'remote-debugging-port is not in the list of known options, but still passed to Electron/Chromium' | cdp | ✅ works | explicit |
| :9233/json/version -> Chrome/148.0.7778.97; Electron warns 'remote-debugging-port is not in the list of known options, but still passed to Electron/Chromium' (same banner as the macOS Cursor cell) | cdp | ✅ works | explicit |
| com.apple.Chess; every piece an AXButton on first walk | accessibility-api | ✅ works | — |
| AppWindow class, D3D11 swapchain; UIA tree = 7 nodes, all OS window chrome (title bar, system menu, min/max/close), ZERO content children — the unambiguous zero-coverage signal | pixels-baseline | ⬜ unavailable | explicit |
| libgtk-4.so; text nodes name their font per run | render-tree-tap | ✅ works | explicit |
| org.a11y.Bus not activatable in headless sandbox; app does not register | accessibility-api | ⛔ blocked | blocked |
| libgtk-4.so; gsk_renderer_render | render-tree-tap | 🟡 partial | explicit |
| libgtk-4.so.1 mapped; renderer submits via gsk_renderer_render() | render-tree-tap | ✅ works | — |
| libgtk-4.so; gsk_renderer_render per frame | render-tree-tap | ✅ works | — |
| soffice.bin + socket,port=2003 up | object-model | ✅ works | — |
| soffice.bin running; UNO endpoint 'socket,port=2002;urp' accepts a connection | object-model | ✅ works | — |
| New-Object -ComObject Word.Application -> REGDB_E_CLASSNOTREG 0x80040154 (no Office installed; Excel likewise); no LibreOffice present | object-model | ⛔ blocked | blocked |
| Dispatch('Word.Application') answers in 10 ms (REGDB check is a registry read — free and a-priori) | object-model | ✅ works | — |
| libgtk-4.so | libQt5*.so | soffice | chromium binary — one per window | render-tree-tap | ✅ works | explicit |
| csrutil status = enabled; Chrome CodeDirectory flags=0x12a00 (kill, restrict, library-validation, runtime); TextEdit is a platform binary under /System | render-tree-tap | ⛔ blocked | blocked |
| us.zoom.xos; home window exposes 100+ nodes incl. 3 embedded AXWebArea (hybrid native+web UI) | accessibility-api | ✅ works | — |
| chrome.exe+port9235 -> cdp | chrome.exe/Discord.exe/Spotify.exe no port -> uia-latch | Notepad/Terminal/rundll32 -> uia | TokenElevation=True -> pixels-crop | accessibility-api | ✅ works | explicit |
| n/a | accessibility-api | ✅ works | — |
| LOGPIXELSX=96, HORZRES=DESKTOPHORZRES=1920x1080 (no DPI virtualization); ImageGrab returns exactly 1920x1080 | pixels-baseline | ✅ works | — |
| libQt5Gui.so / libQt5Widgets.so mapped (or Qt6 equivalents) | render-tree-tap | ⬜ unavailable | explicit |
| Qt6Widgets.dll / Qt6Svg.dll / Qt6Network.dll mapped in obs64.exe; UIA answers through Qt's QAccessible->UIA bridge with a 185-node tree on first query | accessibility-api | 🟡 partial | explicit |
| com.apple.clock; window tree 25 nodes with labeled toolbar tabs on first query | accessibility-api | ✅ works | — |
| SunAwtFrame window class (=Java/AWT, a-priori); channel signature: jabswitch enabled + windowsaccessbridge-64.dll present + isJavaWindow(hwnd)=TRUE answers immediately once the JVM runs with the AccessBridge AT loaded | java-access-bridge | ✅ works | explicit |
| CreateObject('Shell.Application') succeeds (always present on Windows); Windows() enumerates open Explorer windows with LocationURL | object-model | ✅ works | — |
| CabinetWClass; UIA responds with a full 188-node tree on first query | accessibility-api | ✅ works | — |
| router process: per-monitor-aware (UIA rects physical); executor process: DPI-unaware (no manifest, no SetProcessDpiAwareness) — its LOGPIXELSX reads 96 while the fresh-aware probe reads 120: the mismatch IS the detectable signature | accessibility-api | ✅ works | — |
| classic #32770 dialog class; UIA answers through the MSAA/Win32 proxy providers with a 25-node tree on first query | accessibility-api | ✅ works | — |
| UWP package Microsoft.WindowsCalculator; UIA answers with a full 92-node tree on first query (no latch). NOTE the frame/content process split: the top-level WindowControl belongs to ApplicationFrameHost.exe, every content element to CalculatorApp.exe | accessibility-api | ✅ works | — |
| Microsoft.UI.Xaml.dll + NotepadXamlUI.dll + WinUIEdit.dll mapped; UIA responds with a 70-node tree on first query (no AT-latch needed) | accessibility-api | ✅ works | — |
| Win11 Paint (Microsoft.Paint store app); UIA answers with a 232-node tree on first query | accessibility-api | ✅ works | explicit |
| OpenProcess + GetTokenInformation(TokenElevation) on taskmgr.exe returns True (auto-elevation for admin accounts, no UAC dialog shown); ControlFromHandle on its HWND returns a 1-node stub (window + empty title bar) | accessibility-api | ⛔ blocked | blocked |
| PresentationCore.ni.dll + PresentationFramework.ni.dll + wpfgfx_v0400.dll mapped; UIA answers with the full 18-node element tree on first query (WPF is UIA's first-class citizen) | accessibility-api | ✅ works | — |

## Safety verdict

- Cells where structure **works**: 46/61.
- **Silent divergences surviving** (disqualifying): 0/61 ✅ none
- Silent divergences **found, then caught-and-declared** by coverage-guard: 3 — FL Studio 2025, OBS Studio 31.0.3, rekordbox 7.0.9 (each cell carries its `mitigation` record)
- Cells **not** predictable in advance: 0/61 ✅ none

Reading: the campaign found 3 silent divergences (**FL Studio 2025** (windows), **OBS Studio 31.0.3** (windows), **rekordbox 7.0.9** (windows)) and **neutralized every one** with the documented coverage-guard (pixel spot-check on structure-empty regions + view self-consistency): each cell re-emits its blind spot as an explicit `[pixels]`/`[inconsistent]` line and records the guard run in a `mitigation` field. Combined with 0 unpredictable cells, the safety claim stands in its honest form: not "structure never lies", but "every blind spot is predictable a priori and convertible to an explicit declaration by a documented, measured router guard."
