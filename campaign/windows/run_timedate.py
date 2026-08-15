# -*- coding: utf-8 -*-
"""Cell: windows-timedate-uia. Legacy Win32 'Date and Time' dialog (timedate.cpl).

The classic Win32/GDI living screen: an analog clock (custom-drawn) + a digital
clock that ticks every second. Tests the MSAA->UIA proxy path on a pre-XAML
dialog, and whether the custom-drawn analog clock face is declared or silent.
Read-only except closing the dialog we opened.
"""
import ctypes, json, os, subprocess, sys, time, difflib
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, blind_click,
                       text_tokens, image_tokens, save_artifact, probe_with_latch)

out = {"cell": "windows-timedate-uia"}
subprocess.Popen(["control.exe", "timedate.cpl"])
time.sleep(3.0)

win = auto.WindowControl(searchDepth=1, RegexName="Date et heure|Date and Time")
if not win.Exists(10):
    print(json.dumps({"error": "timedate dialog not found"})); sys.exit(1)

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
out["view_stats"] = {"nodes": stats["nodes"], "cap_hit": stats["cap_hit"],
                     "types": stats["types"]}
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_highres"] = image_tokens(wrect[2], wrect[3])
save_artifact("timedate-uia-view.txt", view)
if ctypes.windll.user32.GetForegroundWindow() == win.NativeWindowHandle:
    screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                   "artifacts", "windows", "timedate-uia-shot.png"))

t0 = time.perf_counter(); distill(win)
out["capture_latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)

# --- T4: poll ~1 Hz, the digital clock should tick every second --------------
ticks = []
prev = view
last_diff = ""
for i in range(6):
    time.sleep(1.0)
    t0 = time.perf_counter()
    cur, _ = distill(win)
    lat = (time.perf_counter() - t0) * 1000
    d = "\n".join(difflib.unified_diff(prev.splitlines(), cur.splitlines(), lineterm=""))
    changed = [l for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]
    ticks.append({"tick": i + 1, "diff_bytes": len(d.encode("utf-8")),
                  "changed_line_bytes": sum(len(c.encode('utf-8')) for c in changed),
                  "changed_lines": len(changed), "capture_ms": round(lat, 1),
                  "sample": changed[0][:100] if changed else ""})
    prev = cur
    if d: last_diff = d
out["t4_ticks"] = ticks
save_artifact("timedate-uia-tick-diff.txt", last_diff)

win.GetPattern(auto.PatternId.WindowPattern).Close()
print(json.dumps(out, ensure_ascii=False, indent=1))
