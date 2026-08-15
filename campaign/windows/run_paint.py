# -*- coding: utf-8 -*-
"""Cell: windows-paint-uia. Paint (Win11 WinUI). T6 pictorial honesty:
does UIA declare the drawing canvas as a bounded region, or silently omit it?
Throwaway canvas; closed without saving.
"""
import ctypes, json, os, subprocess, sys, time, difflib
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, blind_click,
                       text_tokens, image_tokens, save_artifact, probe_with_latch, walk)

out = {"cell": "windows-paint-uia"}
subprocess.Popen(["mspaint.exe"])
time.sleep(4.0)

win = auto.WindowControl(searchDepth=1, RegexName=".*Paint.*")
if not win.Exists(10):
    print(json.dumps({"error": "paint window not found"})); sys.exit(1)

def force_foreground(w):
    hwnd = w.NativeWindowHandle
    for attempt in range(5):
        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
        try: w.SetActive()
        except Exception: pass
        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.5)
        if ctypes.windll.user32.GetForegroundWindow() == hwnd:
            return attempt + 1
    return -1

out["foreground_attempts"] = force_foreground(win)
wrect = rect_of(win)
out["window_rect"] = wrect

view, stats, attempts = probe_with_latch(lambda: win, settle=0.8, retries=3)
out["latch_attempts"] = attempts
out["view_stats"] = {"nodes": stats["nodes"], "cap_hit": stats["cap_hit"]}
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_highres"] = image_tokens(wrect[2], wrect[3])
save_artifact("paint-uia-view.txt", view)
if ctypes.windll.user32.GetForegroundWindow() == win.NativeWindowHandle:
    screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                   "artifacts", "windows", "paint-uia-shot.png"))

# --- T6: locate the canvas node(s) — walk raw tree for anything canvas-like --
canvas_nodes = []
for c, d in walk(win, max_depth=40, max_nodes=8000):
    if c is None: break
    try:
        ct, nm = c.ControlTypeName, (c.Name or "")
        cls = c.ClassName or ""
    except Exception:
        continue
    if any(k in (nm or "").lower() for k in ("canevas", "canvas", "image", "dessin", "zone de dessin")) \
       or any(k in cls.lower() for k in ("canvas", "surface", "d2d", "swapchain")):
        x, y, w, h = (c.BoundingRectangle.left, c.BoundingRectangle.top,
                      c.BoundingRectangle.right - c.BoundingRectangle.left,
                      c.BoundingRectangle.bottom - c.BoundingRectangle.top)
        canvas_nodes.append({"type": ct, "name": nm[:80], "class": cls, "rect": [x, y, w, h]})
out["t6_canvas_nodes"] = canvas_nodes[:10]

# --- T5: blind click a harmless tool (Pinceaux/Brush) & verify in channel ----
t5 = {"pass": False}
target = None
for l in view.splitlines():
    if any(f'"{n}"' in l for n in ("Pinceaux", "Brushes", "Pinceau")):
        target = l; break
t5["target_line"] = target
if target:
    x, y, w, h = map(int, target.split(" ")[1].split(","))
    cx, cy = x + w // 2, y + h // 2
    el = auto.ControlFromPoint(cx, cy)
    top = el.GetTopLevelControl() if el else None
    if top and top.NativeWindowHandle == win.NativeWindowHandle:
        blind_click(cx, cy)
        time.sleep(1.0)
        nview, _ = distill(win)
        for l in nview.splitlines():
            if any(f'"{n}"' in l for n in ("Pinceaux", "Brushes", "Pinceau")):
                t5["after_line"] = l
                t5["pass"] = "toggle=1" in l or "selected=True" in l
                break
        d = "\n".join(difflib.unified_diff(view.splitlines(), nview.splitlines(), lineterm=""))
        out["diff_bytes_tool_click"] = len(d.encode("utf-8"))
out["t5"] = t5

# idle
v1, _ = distill(win); time.sleep(1.0); v2, _ = distill(win)
idiff = "\n".join(difflib.unified_diff(v1.splitlines(), v2.splitlines(), lineterm=""))
out["idle_diff_bytes"] = len(idiff.encode("utf-8"))

win.GetPattern(auto.PatternId.WindowPattern).Close()
time.sleep(1.5)
# decline save prompt if any
try:
    for wht in auto.GetRootControl().GetChildren():
        if "Paint" in (wht.Name or ""):
            btn = wht.ButtonControl(RegexName="Ne pas enregistrer|Don't save")
            if btn.Exists(2):
                btn.Click(simulateMove=False)
except Exception:
    pass
print(json.dumps(out, ensure_ascii=False, indent=1))
