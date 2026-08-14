# Agent brief — WINDOWS (read agent-brief-COMMON.md first)

Windows is the most permissive OS for this study and the most important to get
right — it has the richest set of structured channels and a decade of commercial
precedent (RPA tools hook GDI to read text). Aim for broad coverage across the
stack tiers below.

## Environment prep

- Run in a normal user session with a real display (structured channels often need a
  live UI, not Session 0). Have admin rights available for tools that need them.
- Install once, as needed: Python 3 (`pip install pywinauto uiautomation comtypes
  pillow`), and Node if you want the CDP path. `uiautomation`/`pywinauto` wrap the
  **UI Automation (UIA)** API — your primary cross-app structured channel.
- Windows Accessibility Insights (optional) is a good manual cross-check for UIA
  trees.

## Channels to probe, by tier

### Tier A — UI Automation (the general channel; try on EVERY app)
UIA exposes a control tree: control type, name, value, bounding rect, patterns
(Invoke, Value, Toggle…). This is the closest Windows analog to "the render/semantic
tree" available cross-app without injection.
- Detection signature (H5): UIA responds for the process → channel available.
- Run full T1–T6 via `uiautomation`/`pywinauto`. For T5, use the UIA bounding rect
  center as your blind-click coordinate and dispatch a raw click there.
- **Silent-divergence hunt**: UIA is notorious for stale/missing nodes in
  custom-drawn apps. Deliberately test an app that draws its own content and check
  whether UIA *admits* it can't see it (empty/generic node = explicit) or reports a
  tree that contradicts the screen (= silent, disqualifying).

### Tier B — Electron / Chromium (VS Code, Chrome, Slack, Discord, Teams)
- Launch with `--remote-debugging-port=9222` (VS Code: `code
  --remote-debugging-port=9222`; Chrome likewise). Detection: port 9222 answers.
- Reuse the browser probe method from the parent repo: `DOMSnapshot.captureSnapshot`
  + `LayerTree`. Run T1–T6; capture token/diff numbers directly comparable to the
  Linux CDP results already in `results/`.
- Note the DUAL channel: these apps ALSO expose a UIA tree — probe both and compare
  coverage and cost.

### Tier C — Microsoft Word (the star case)
Three channels, increasing semantics:
1. **DirectWrite / render level** — text is glyph runs (like GTK). Note whether
   reachable without injection; likely needs a hook — if blocked, say so.
2. **UIA** — document text + controls.
3. **Word object model via COM** — `win32com.client.Dispatch("Word.Application")`
   then `.ActiveDocument.Range().Text`. This is the *document itself* — the ultimate
   structured source, above any render tree. Run T1 (read known text you typed), T3
   (live edits), and measure token cost of the object-model view vs a screenshot of
   the same page. This cell is likely the strongest positive in the whole study —
   quantify it well.

### Tier D — Win32 / GDI legacy (Notepad, Notepad++, 7-Zip)
- UIA usually still works (that's the point of UIA). Where it's thin, note it.
- Optional/advanced: a GDI text hook (the UiPath "Native" approach) — only if easy;
  otherwise record it as "known-possible, not attempted".

### Tier E — WinUI 3 / XAML (Calculator, Settings) and WPF
- UIA is strong here (XAML maps to UIA well). Expect good T1–T6. Detection: XAML/WinUI
  DLLs loaded.

### Tier F — Qt, Flutter, Java (if any installed: qBittorrent, a Flutter app, a JetBrains IDE)
- Qt: UIA/accessibility only if the app enabled Qt accessibility; the Qt scene graph
  has no public serialization — record the *refusal* as data.
- Flutter desktop: VM service / DevTools protocol if a debug build; release builds
  are an opaque canvas to UIA — a key **explicit-failure** example.
- Java: Java Access Bridge if present.

### Tier G — Pixels-only control (a game, a fullscreen video)
- Confirm the perimeter law: UIA sees a single generic surface; the structured
  channel yields nothing useful and *says so*. This is a wanted negative.

## Windows-specific reporting

For each app, the H5 verdict hinges on: was the working channel predictable from a
signature (loaded modules / process name / open port / UIA availability) BEFORE you
extracted anything? Fill `stack_detection.detected_before_use` honestly. The dream
result for the paper is a clean mapping "signature ⇒ channel ⇒ known coverage"; the
dangerous result is any app where the channel *looked* available but returned a
silently wrong view.
