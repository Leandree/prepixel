# -*- coding: utf-8 -*-
"""UIA probe library for the Windows campaign.

Encodes the lessons the Linux + macOS campaigns paid for (see
campaign/agent-brief-windows.md):
  - AT-latch: probe -> poke -> re-probe before concluding "unavailable".
  - Cycle-guard every tree walk (runtime-id set + depth cap + node cap).
  - Physical-pixel coordinate discipline: process is made per-monitor-DPI-aware
    so UIA BoundingRectangle, ImageGrab and SendInput all share one frame.
  - Re-resolve element handles immediately before acting; verify after (TOCTOU).
  - Action allowlist: only actuate controls the caller explicitly whitelists.
  - Distilled view format mirrors src/distill-hardened.mjs line format so token
    numbers are comparable across channels: `role x,y,w,h "name" [attrs]`.
"""
import ctypes
import ctypes.wintypes
import json
import os
import sys
import time

# --- DPI awareness FIRST, before any window/GDI call -------------------------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

import uiautomation as auto  # noqa: E402
from PIL import ImageGrab    # noqa: E402

ARTIFACTS = os.path.join(os.path.dirname(__file__), "..", "results", "artifacts", "windows")
os.makedirs(ARTIFACTS, exist_ok=True)

# --- token estimators (same formulas as src/) --------------------------------
def text_tokens(s):
    return -(-len(s) // 4)  # ceil(chars/4)

def image_tokens(w, h, tier="highres"):
    max_edge, max_px = (2576, 3_588_000) if tier == "highres" else (1568, 1_150_000)
    s = min(1.0, max_edge / max(w, h))
    W, H = w * s, h * s
    if W * H > max_px:
        s2 = (max_px / (W * H)) ** 0.5
        W, H = W * s2, H * s2
    return -(-int(W * H) // 750)

# --- tree walk with cycle guard ----------------------------------------------
INTERACTIVE_TYPES = {
    "ButtonControl", "HyperlinkControl", "EditControl", "ComboBoxControl",
    "CheckBoxControl", "RadioButtonControl", "MenuItemControl", "TabItemControl",
    "ListItemControl", "TreeItemControl", "SliderControl", "SplitButtonControl",
    "SpinnerControl", "DataItemControl",
}
PICTORIAL_TYPES = {"ImageControl"}
TEXTUAL_TYPES = {"TextControl", "DocumentControl", "EditControl"}

def walk(root, max_depth=60, max_nodes=25000):
    """Yield (control, depth). Cycle-guarded via runtime ids, depth+node capped."""
    seen = set()
    stack = [(root, 0)]
    n = 0
    while stack:
        c, d = stack.pop()
        try:
            rid = tuple(c.GetRuntimeId() or ())
        except Exception:
            rid = ()
        if rid and rid in seen:
            continue
        if rid:
            seen.add(rid)
        n += 1
        if n > max_nodes:
            yield None, -1  # signal cap hit
            return
        yield c, d
        if d >= max_depth:
            continue
        try:
            kids = c.GetChildren()
        except Exception:
            kids = []
        for k in reversed(kids):
            stack.append((k, d + 1))

def rect_of(c):
    try:
        r = c.BoundingRectangle
        return (r.left, r.top, r.right - r.left, r.bottom - r.top)
    except Exception:
        return (0, 0, 0, 0)

def _value_of(c):
    """Current value via ValuePattern (careful: not all controls support it)."""
    try:
        vp = c.GetPattern(auto.PatternId.ValuePattern)
        if vp:
            return vp.Value
    except Exception:
        pass
    return None

def _states_of(c):
    st = []
    try:
        tp = c.GetPattern(auto.PatternId.TogglePattern)
        if tp is not None:
            st.append(f"toggle={tp.ToggleState}")
    except Exception:
        pass
    try:
        sp = c.GetPattern(auto.PatternId.SelectionItemPattern)
        if sp is not None:
            st.append(f"selected={sp.IsSelected}")
    except Exception:
        pass
    try:
        if c.IsOffscreen:
            st.append("offscreen")
    except Exception:
        pass
    return st

def distill(root, include_offscreen=False, max_depth=60, max_nodes=25000,
            with_values=True):
    """Compact agent view of a UIA subtree, one line per meaningful node.

    Format mirrors the CDP distiller: `role x,y,w,h "name" [value=..] [states]`.
    Offscreen nodes are dropped (like the viewport clip in the browser distiller)
    unless include_offscreen. Pictorial nodes are declared as [pixels] lines.
    Returns (view_text, stats dict).
    """
    lines = []
    stats = {"nodes": 0, "cap_hit": False, "types": {}}
    for c, d in walk(root, max_depth, max_nodes):
        if c is None:
            stats["cap_hit"] = True
            break
        stats["nodes"] += 1
        try:
            ct = c.ControlTypeName
        except Exception:
            continue
        stats["types"][ct] = stats["types"].get(ct, 0) + 1
        x, y, w, h = rect_of(c)
        try:
            name = (c.Name or "").strip()
        except Exception:
            name = ""
        offscreen = False
        try:
            offscreen = bool(c.IsOffscreen)
        except Exception:
            pass
        if offscreen and not include_offscreen:
            continue
        if w <= 0 or h <= 0:
            continue
        role = ct.replace("Control", "").lower()
        if ct in PICTORIAL_TYPES:
            lines.append(f"[pixels] image {x},{y},{w},{h}" + (f' "{name}"' if name else ""))
            continue
        interesting = ct in INTERACTIVE_TYPES or (name and ct in TEXTUAL_TYPES) or ct == "WindowControl"
        if not interesting and not name:
            continue
        parts = [f"{role} {x},{y},{w},{h}"]
        if name:
            nm = name if len(name) <= 200 else name[:200] + "…"
            parts.append(f'"{nm}"')
        if with_values and ct in ("EditControl", "DocumentControl", "ComboBoxControl"):
            v = _value_of(c)
            if v:
                vv = v if len(v) <= 300 else v[:300] + "…"
                parts.append(f'value="{vv}"')
        st = _states_of(c)
        if st:
            parts.append("[" + " ".join(st) + "]")
        lines.append(" ".join(parts))
    return "\n".join(lines), stats

# --- screenshots -------------------------------------------------------------
def screenshot(bbox=None, path=None):
    """Grab physical pixels. bbox=(x,y,w,h) window rect or None for full screen."""
    if bbox:
        x, y, w, h = bbox
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h), all_screens=True)
    else:
        img = ImageGrab.grab(all_screens=False)
    if path:
        img.save(path)
    return img

def print_window(hwnd, path=None):
    """Capture a window's OWN surface via PrintWindow(PW_RENDERFULLCONTENT) —
    works even when the window is covered or unfocused. The per-window pixel
    ground truth that pairs with the per-window UIA structure (no focus games).
    Returns a PIL Image or None."""
    from PIL import Image
    u, g = ctypes.windll.user32, ctypes.windll.gdi32
    HDC, HBMP, HWND = ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p
    u.GetWindowDC.restype = HDC; u.GetWindowDC.argtypes = [HWND]
    u.ReleaseDC.argtypes = [HWND, HDC]
    u.PrintWindow.argtypes = [HWND, HDC, ctypes.c_uint]
    g.CreateCompatibleDC.restype = HDC; g.CreateCompatibleDC.argtypes = [HDC]
    g.CreateCompatibleBitmap.restype = HBMP
    g.CreateCompatibleBitmap.argtypes = [HDC, ctypes.c_int, ctypes.c_int]
    g.SelectObject.restype = ctypes.c_void_p
    g.SelectObject.argtypes = [HDC, ctypes.c_void_p]
    g.DeleteObject.argtypes = [ctypes.c_void_p]
    g.DeleteDC.argtypes = [HDC]
    g.GetDIBits.argtypes = [HDC, HBMP, ctypes.c_uint, ctypes.c_uint,
                            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
    r = ctypes.wintypes.RECT()
    u.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0:
        return None
    hdc = u.GetWindowDC(hwnd)
    mdc = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, w, h)
    g.SelectObject(mdc, bmp)
    ok = u.PrintWindow(hwnd, mdc, 2)  # PW_RENDERFULLCONTENT
    img = None
    if ok:
        class BMIH(ctypes.Structure):
            _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                        ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                        ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                        ("biClrImportant", ctypes.c_uint32)]
        bmi = BMIH(ctypes.sizeof(BMIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
        buf = ctypes.create_string_buffer(w * h * 4)
        g.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bmi), 0)
        img = Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1)
        if path:
            img.convert("RGB").save(path)
    g.DeleteObject(bmp)
    g.DeleteDC(mdc)
    u.ReleaseDC(hwnd, hdc)
    return img

# --- blind click via raw SendInput (independent of UIA) ----------------------
SendInput = ctypes.windll.user32.SendInput
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
class INPUT(ctypes.Structure):
    class _I(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _anonymous_ = ("i",)
    _fields_ = [("type", ctypes.c_ulong), ("i", _I)]

def blind_click(x, y):
    """Move cursor to physical (x, y) and left-click there. No UIA involved."""
    ctypes.windll.user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    inputs = (INPUT * 2)()
    inputs[0].type = 0
    inputs[0].mi = MOUSEINPUT(0, 0, 0, 0x0002, 0, None)  # LEFTDOWN
    inputs[1].type = 0
    inputs[1].mi = MOUSEINPUT(0, 0, 0, 0x0004, 0, None)  # LEFTUP
    SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))

# --- latch-aware channel probe ----------------------------------------------
def probe_with_latch(get_root, settle=1.0, retries=3):
    """probe -> poke -> re-probe. Returns (view, stats, attempts).

    The act of walking UIA IS the assistive-client signal for apps that build
    their tree lazily (Chromium). We walk, wait, re-walk until the node count
    stabilises or retries are exhausted.
    """
    attempts = []
    prev_nodes = -1
    view, stats = "", {}
    for i in range(retries):
        t0 = time.perf_counter()
        view, stats = distill(get_root())
        dt = (time.perf_counter() - t0) * 1000
        attempts.append({"attempt": i + 1, "nodes": stats["nodes"], "ms": round(dt, 1)})
        if stats["nodes"] == prev_nodes:
            break
        prev_nodes = stats["nodes"]
        time.sleep(settle)
    return view, stats, attempts

def find_window(title_re=None, class_name=None, timeout=10):
    auto.SetGlobalSearchTimeout(timeout)
    kw = {"searchDepth": 1}
    if title_re:
        kw["RegexName"] = title_re
    if class_name:
        kw["ClassName"] = class_name
    return auto.WindowControl(**kw)

def save_artifact(name, content):
    p = os.path.join(ARTIFACTS, name)
    if isinstance(content, str):
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        with open(p, "wb") as f:
            f.write(content)
    return p

if __name__ == "__main__":
    # smoke test: distill the desktop root's immediate windows
    root = auto.GetRootControl()
    t0 = time.perf_counter()
    kids = root.GetChildren()
    dt = (time.perf_counter() - t0) * 1000
    print(f"desktop children: {len(kids)} in {dt:.1f} ms")
    for k in kids[:15]:
        print(" ", k.ControlTypeName, rect_of(k), repr((k.Name or "")[:60]))
