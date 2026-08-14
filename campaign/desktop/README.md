# Semantic compositor / desktop router (PoC)

The insight: **no single channel sees the whole screen *with* semantics.** The
compositor merges all windows but only as pixels; each toolkit (GTK, Qt, Skia, the
LibreOffice model) is semantic but per-window. So an agent must *assemble* the
merged semantic view itself — this PoC does exactly that on a real Linux desktop.

## What it does

1. **Window-manager map** (`router.py`): via EWMH (`wmctrl`, `xprop
   _NET_CLIENT_LIST_STACKING`, `_NET_ACTIVE_WINDOW`) it enumerates every top-level
   window with geometry, stacking order (z), and which one has focus.
2. **Per-window stack detection**: from each window's PID it reads `/proc/PID/maps`
   and cmdline for a signature — `libgtk-4.so`, `libQt5*.so`, `soffice`, the chromium
   binary — so the toolkit is known *before* any content is touched.
3. **Best-channel binding**: chromium→CDP, LibreOffice→UNO object model, GTK→render-
   tree tap, Qt→accessibility/pixels fallback; each with a verdict (works / partial /
   unavailable) and a failure class (explicit / blocked), decided a priori.
4. **Merged view assembly**: for the focused window it extracts the real content
   through the chosen channel (`cdp_extract.mjs` connects to the live Chromium over
   CDP) and stitches it into one desktop tree (`merged-desktop-view.json`).

## Result (live run, 4 concurrent windows, 4 different toolkits)

| z | focus | window | stack (signature) | channel | verdict |
|---|:---:|--------|-------------------|---------|---------|
| 0 | | GNOME Text Editor | gtk4 (`libgtk-4.so`) | render-tree-tap | ✅ works |
| 1 | | featherpad | qt (`libQt5*.so`) | accessibility-api | ⬜ unavailable |
| 2 | | LibreOffice Writer | office-native (`soffice`) | object-model (UNO) | ✅ works |
| 3 | ★ | Orders Console | chromium (chromium binary) | cdp | ✅ works |

- **4/4 windows predictable before use** (each channel known from a signature).
- **Focused window content extracted live** via CDP: `Invoices` / `button id=pay
  Pay 1240` / `Client: Dupont SARL` — 30 tokens.
- **1/4 unavailable, explicitly**: Qt exposes no render tree; the router flags it and
  would fall back to pixels/AT-SPI rather than inventing a view.
- Evidence screenshot: `desktop-evidence.png` (three toolkits visible at once).

## Why this matters

This is the "compositor of semantics" layered over the compositor of pixels. It
turns the per-window/per-toolkit fragmentation (the thing that felt like a weakness)
into a routing problem with a **predictable, explicit** solution: the agent always
knows, per window, whether structure is available and what it covers — and never
gets a silently wrong view. The unavailable cell (Qt) degrades to the pixel path
by design, not by surprise.

## Run

```bash
export DISPLAY=:9         # a running X desktop with an EWMH WM
python3 router.py          # -> merged window map + per-window channel verdicts
node cdp_extract.mjs "<window title>"   # extract focused Chromium content
```
