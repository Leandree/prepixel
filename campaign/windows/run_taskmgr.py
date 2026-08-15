# -*- coding: utf-8 -*-
"""Cell: windows-taskmgr-uia. Task Manager (WinUI, custom-drawn perf graphs).

T4 living screen: poll the distilled view at ~1 Hz, measure per-tick diff cost.
Silent-divergence hunt: what does UIA declare for the custom-drawn CPU graph
region on the Performance page — a node, or an undeclared hole?
Allowlisted click: the 'Performances' nav item only. Elevation note: taskmgr
auto-elevates for admin users; if UIPI blocks our non-elevated UIA client,
that block IS the result.
"""
import ctypes, json, os, subprocess, sys, time, difflib
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, blind_click,
                       text_tokens, image_tokens, save_artifact, probe_with_latch)

out = {"cell": "windows-taskmgr-uia"}
subprocess.Popen(["taskmgr.exe"])
time.sleep(4.0)

win = auto.WindowControl(searchDepth=1, RegexName="Gestionnaire des tâches|Task Manager")
if not win.Exists(10):
    out["error"] = "window not found — possibly elevated beyond UIA reach (UIPI)"
    print(json.dumps(out, ensure_ascii=False)); sys.exit(1)

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
save_artifact("taskmgr-uia-view-processes.txt", view)
out["screenshot_tokens_highres"] = image_tokens(wrect[2], wrect[3])

# --- T4 living screen: 6 polls at ~1 Hz on the processes page ----------------
ticks = []
prev = view
for i in range(6):
    time.sleep(1.0)
    t0 = time.perf_counter()
    cur, _ = distill(win)
    lat = (time.perf_counter() - t0) * 1000
    d = "\n".join(difflib.unified_diff(prev.splitlines(), cur.splitlines(), lineterm=""))
    changed = sum(1 for l in d.splitlines() if l.startswith("+") and not l.startswith("+++"))
    ticks.append({"tick": i + 1, "diff_bytes": len(d.encode("utf-8")),
                  "changed_lines": changed, "capture_ms": round(lat, 1)})
    prev = cur
out["t4_ticks"] = ticks
save_artifact("taskmgr-uia-tick-diff-sample.txt", d)

# --- navigate to Performance page (allowlisted blind click) ------------------
target = None
for l in prev.splitlines():
    if '"Performances"' in l or '"Performance"' in l:
        target = l; break
perf = {"nav_line": target}
if target:
    x, y, w, h = map(int, target.split(" ")[1].split(","))
    cx, cy = x + w // 2, y + h // 2
    el = auto.ControlFromPoint(cx, cy)
    top = el.GetTopLevelControl() if el else None
    if top and top.NativeWindowHandle == win.NativeWindowHandle:
        blind_click(cx, cy)
        time.sleep(2.0)
        pview, pstats = distill(win)
        perf["view_nodes"] = pstats["nodes"]
        perf["view_tokens"] = text_tokens(pview)
        save_artifact("taskmgr-uia-view-performance.txt", pview)
        if ctypes.windll.user32.GetForegroundWindow() == win.NativeWindowHandle:
            screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                           "artifacts", "windows", "taskmgr-performance-shot.png"))
        # --- graph-region audit: which nodes cover the graph area? ----------
        # find CPU % text and the biggest un-named area; list nodes overlapping
        # the right half of the window (where the graph lives)
        gx0 = wrect[0] + wrect[2] // 3
        overl = []
        for line in pview.splitlines():
            try:
                bx, by, bw, bh = map(int, line.split(" ")[1].split(","))
            except Exception:
                continue
            if bx + bw > gx0 and bw * bh > 10000:
                overl.append(line)
        perf["big_nodes_in_graph_half"] = overl[:20]
        # coverage accounting: fraction of window area covered by leaf text/named nodes
        perf["note"] = "see artifacts for the full view; graph honesty judged from node list vs screenshot"
else:
    perf["error"] = "Performances nav not found in view"
out["performance_page"] = perf

# living screen on the perf page too (graph animates every second)
pticks = []
prev2, _ = distill(win)
for i in range(4):
    time.sleep(1.0)
    cur2, _ = distill(win)
    d2 = "\n".join(difflib.unified_diff(prev2.splitlines(), cur2.splitlines(), lineterm=""))
    pticks.append({"tick": i + 1, "diff_bytes": len(d2.encode("utf-8"))})
    prev2 = cur2
out["t4_perf_page_ticks"] = pticks

win.GetPattern(auto.PatternId.WindowPattern).Close()
print(json.dumps(out, ensure_ascii=False, indent=1))
