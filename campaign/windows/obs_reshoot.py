# -*- coding: utf-8 -*-
"""Clean ground-truth screenshot for the OBS cell (round 1 shot captured the
Clock app that had covered OBS — kept as the occlusion lesson)."""
import ctypes, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, text_tokens,
                       image_tokens, save_artifact)

out = {}
# close the self-launched Clock app if present (it appeared after its update)
clk = auto.WindowControl(searchDepth=1, RegexName="Horloge|Clock")
if clk.Exists(2):
    try:
        clk.GetPattern(auto.PatternId.WindowPattern).Close()
        out["clock_closed"] = True
        time.sleep(1.0)
    except Exception as e:
        out["clock_close_error"] = str(e)[:120]

OBS_DIR = r"C:\Program Files\obs-studio\bin\64bit"
proc = subprocess.Popen([os.path.join(OBS_DIR, "obs64.exe"), "--disable-updater"], cwd=OBS_DIR)
time.sleep(10.0)
win = auto.WindowControl(searchDepth=1, RegexName="OBS .*")
if not win.Exists(15):
    print(json.dumps({"error": "obs not found", **out})); sys.exit(1)

hwnd = win.NativeWindowHandle
for attempt in range(5):
    ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
    try: win.SetActive()
    except Exception: pass
    ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
    time.sleep(0.5)
    if ctypes.windll.user32.GetForegroundWindow() == hwnd:
        out["foreground_ok"] = attempt + 1; break
time.sleep(1.0)
wrect = rect_of(win)
view, stats = distill(win)
out["landmarks"] = [l for l in ("Scènes", "Sources", "Mélangeur", "Commandes") if l in view]
out["nodes"] = stats["nodes"]
if ctypes.windll.user32.GetForegroundWindow() == hwnd:
    screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                   "artifacts", "windows", "obs-uia-shot.png"))
    out["shot"] = "ok, foreground verified"
save_artifact("obs-uia-view.txt", view)
win.GetPattern(auto.PatternId.WindowPattern).Close()
print(json.dumps(out, ensure_ascii=False, indent=1))
