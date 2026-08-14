# Agent brief — LINUX (read agent-brief-COMMON.md first)

Linux is where the render-tree tap is most open (we already captured GTK4's GSK tree
by hooking `gsk_renderer_render`, and the Chromium/CDP cell is done). Your job is to
fill the remaining stacks and to stress the **predictability** question across the
toolkit zoo, where interception friction is real (recall: Ubuntu's `-Bsymbolic`
build defeated our LD_PRELOAD shim and forced a gdb tap — that kind of build-time
accident is exactly the "unpredictable in advance" risk to characterize).

## Environment prep

- A real session (Wayland or X11 — note which; it matters for what the compositor
  exposes). Python 3 with `pip install pyatspi python-xlib pillow` if available; the
  **AT-SPI2** accessibility bus is your general cross-app channel (`pyatspi` or
  `gi.repository.Atspi`). `Accerciser` is a good manual AT-SPI cross-check.
- Build tools (`gcc`, `gdb`) for the render-tap path; the parent repo's `native/`
  has the GTK4 tap to reuse/extend.

## Channels to probe

### Tier A — AT-SPI2 (the general channel; try on EVERY app)
Role/name/value/extents tree over D-Bus, cross-toolkit. Detection (H5): does the app
register on the a11y bus? GTK/Qt apps usually do *if* accessibility is enabled.
- Run T1–T6 via `pyatspi`/`Atspi`. For T5 use the element extents center as the
  blind-click coordinate.
- Silent-divergence hunt: apps that draw custom canvases (or disable a11y) — does
  AT-SPI omit them (explicit) or misreport (silent)?

### Tier B — GTK4 render-tree tap (extend the existing PoC)
- Reuse `native/tap.gdb` (or `gsktap.so` where LD_PRELOAD works) on more real GTK4
  apps: **gnome-text-editor, Nautilus (Files), GNOME Settings, gnome-calculator**.
- For each: confirm the tree re-renders to the exact frame (`gtk4-rendernode-tool
  render`), decode a text node's glyphs (`native/decode_glyphs.py`), measure
  frame/diff sizes. Note per-app whether the LD_PRELOAD shim worked or the gdb tap
  was needed (predictability of the *interception method* itself).

### Tier C — Qt (Kate, qBittorrent, VLC-Qt, OBS)
- AT-SPI if Qt accessibility is active (`QT_ACCESSIBILITY=1`). The Qt **scene graph**
  has no public serialization — attempting and documenting that *refusal* is the
  point (contrast with GTK's `gsk_render_node_serialize`). Note whether text is
  reachable via AT-SPI even when the scene graph is closed.

### Tier D — LibreOffice (the Office analog)
- Two channels: **AT-SPI** (document text + controls) and the **UNO object model**
  (`officehelper` / `pyuno`; connect via `soffice --accept=...` and read
  `ThisComponent.getText().getString()`). UNO is the document itself — the Linux
  analog of Windows COM Word. Compare UNO vs AT-SPI vs screenshot on the same page.

### Tier E — Electron/Chromium (spot-check for cross-OS consistency)
- The Linux CDP cell exists in the parent repo; re-run one Electron app (e.g. VS
  Code via `--remote-debugging-port=9222`) so the same app can be compared across all
  three OSes.

### Tier F — Flutter (linux desktop build), Java/Swing (a JetBrains IDE)
- Flutter: VM service if a debug build; AT-SPI semantics if enabled. Java:
  AT-SPI/Java bridge. Record refusals as data.

### Tier G — Pixels-only control (a game via Wayland/Xwayland, mpv fullscreen)
- Confirm the perimeter law under Linux: the compositor sees only a client buffer;
  AT-SPI yields nothing; wanted negative. If on Wayland, note that compositor-level
  interception yields only window geometry + damage, no content — a useful data point
  for the "wrong level" argument.

## Linux-specific reporting

Two headline deliverables:
1. Extend the render-tap evidence beyond widget-factory to real daily-use GTK apps,
   with the completeness proof (re-render + glyph decode) per app.
2. Characterize **interception predictability**: for each app/toolkit, was a
   structured channel available, and was the *method* to get it (AT-SPI vs
   LD_PRELOAD vs gdb vs UNO/CDP) predictable from a signature (linked `.so`, a11y-bus
   registration, debug port)? The `-Bsymbolic` story is the cautionary example —
   look for more like it and note them, since unpredictable interception is the
   study's central risk to production use.
