# -*- coding: utf-8 -*-
"""Cell: windows-wpf-uia (DEEPENING-PLAN P2: the missing WPF tier).
Throwaway WPF app hosted by PresentationFramework (wpf_app.ps1)."""
import ctypes, json, os, subprocess, sys, time, difflib
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, blind_click,
                       text_tokens, image_tokens, save_artifact, probe_with_latch)

out = {"cell": "windows-wpf-uia"}
ps1 = os.path.join(os.path.dirname(__file__), "wpf_app.ps1")
proc = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                         "-File", ps1])
time.sleep(6)
win = auto.WindowControl(searchDepth=1, Name="pipeline-tap WPF probe")
if not win.Exists(15):
    print(json.dumps({"error": "wpf window not found"})); sys.exit(1)

sig = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     f"(Get-Process -Id {proc.pid}).Modules | Where-Object {{$_.ModuleName -match 'wpfgfx|Presentation'}} | Select-Object -First 4 -ExpandProperty ModuleName"],
    capture_output=True, text=True).stdout.strip().splitlines()
out["wpf_modules"] = sig

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
out["foreground"] = force_foreground(win)
wrect = rect_of(win)
out["window_rect"] = wrect

view, stats, attempts = probe_with_latch(lambda: win, settle=0.8, retries=3)
out["latch_attempts"] = attempts
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_window"] = image_tokens(wrect[2], wrect[3])
save_artifact("wpf-uia-view.txt", view)

t0 = time.perf_counter(); distill(win)
out["capture_latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)

out["t1"] = {"sentinel": "WPF-TAP-SENTINEL café naïve 日本語 END" in view,
             "canvas_text_exposed": "painted-in-canvas" in view}
inter = [l for l in view.splitlines() if l.split(" ")[0] in
         ("button", "edit", "checkbox")]
out["t2"] = {"interactive_lines": len(inter), "lines": inter}

# T3: focus the field, type, re-read value
edit = win.EditControl(searchDepth=6, AutomationId="Field")
t3 = {"pass": False}
if edit.Exists(3):
    edit.SetFocus(); time.sleep(0.3)
    auto.SendKeys("{Ctrl}a"); auto.SendKeys("WPF-LIVE-5j1q", interval=0.02)
    time.sleep(0.5)
    v2, _ = distill(win)
    line = next((l for l in v2.splitlines() if "WPF-LIVE-5j1q" in l), None)
    t3 = {"pass": line is not None, "value_line": line}
out["t3"] = t3

# T5: blind click Increment from the view line; verify count in channel
v3, _ = distill(win)
target = next((l for l in v3.splitlines() if '"Increment"' in l), None)
t5 = {"pass": False, "target_line": target}
if target:
    x, y, w, h = map(int, target.split(" ")[1].split(","))
    cx, cy = x + w // 2, y + h // 2
    el = auto.ControlFromPoint(cx, cy)
    top = el.GetTopLevelControl() if el else None
    if top and top.NativeWindowHandle == win.NativeWindowHandle:
        blind_click(cx, cy)
        time.sleep(0.8)
        v4, _ = distill(win)
        cl = next((l for l in v4.splitlines() if "count=" in l), None)
        d = "\n".join(difflib.unified_diff(v3.splitlines(), v4.splitlines(), lineterm=""))
        t5.update({"pass": cl is not None and "count=1" in cl, "counter_line": cl,
                   "diff_bytes": len(d.encode("utf-8"))})
out["t5"] = t5

# idle
a, _ = distill(win); time.sleep(1.0); b, _ = distill(win)
out["idle_identical"] = a == b

if ctypes.windll.user32.GetForegroundWindow() == win.NativeWindowHandle:
    screenshot(rect_of(win), os.path.join(os.path.dirname(__file__), "..", "results",
                                          "artifacts", "windows", "wpf-uia-shot.png"))
win.GetPattern(auto.PatternId.WindowPattern).Close()
time.sleep(1)
proc.terminate()
print(json.dumps(out, ensure_ascii=False, indent=1))
