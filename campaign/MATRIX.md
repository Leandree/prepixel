# Coverage matrix & predictability (aggregated)

12 result cells. Legend: ✅ works · 🟡 partial · ⬜ unavailable (structure yields nothing) · ⛔ blocked (OS/env).

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

## Predictability & safety (H5)

The production-safety question: could a router know the channel in advance, and does failure stay explicit (never silent)?

| Stack signature | Channel | Coverage verdict | Failure mode |
|-----------------|---------|------------------|--------------|
| --remote-debugging-port responds on the target process (Electron apps expose the same) | cdp | ✅ works | explicit |
| CDP responds | cdp | 🟡 partial | blocked |
| n/a | cdp | ✅ works | — |
| single CANVAS element covering the viewport; DOM has no text/interactive nodes inside it | pixels-baseline | ⬜ unavailable | explicit |
| libgtk-4.so; text nodes name their font per run | render-tree-tap | ✅ works | explicit |
| org.a11y.Bus not activatable in headless sandbox; app does not register | accessibility-api | ⛔ blocked | blocked |
| libgtk-4.so.1 mapped; renderer submits via gsk_renderer_render() | render-tree-tap | ✅ works | — |
| libgtk-4.so; gsk_renderer_render per frame | render-tree-tap | ✅ works | — |
| soffice.bin running; UNO endpoint 'socket,port=2002;urp' accepts a connection | object-model | ✅ works | — |
| libgtk-4.so | libQt5*.so | soffice | chromium binary — one per window | render-tree-tap | ✅ works | explicit |
| libQt5Gui.so / libQt5Widgets.so mapped (or Qt6 equivalents) | render-tree-tap | ⬜ unavailable | explicit |

## Safety verdict

- Cells where structure **works**: 8/12.
- **Silent divergences** (disqualifying): 0/12 ✅ none found
- Cells **not** predictable in advance: 0/12 ✅ none

Reading: every failure so far is either **explicit** (opaque rect / honest empty tree) or **blocked** (OS/env), and every channel was detectable from a stack signature before use. That is the pattern a production router needs. The open risk to hunt on the other OSes is any **silent** cell — a channel that returns a view disagreeing with the screen without declaring it.
