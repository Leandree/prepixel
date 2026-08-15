# -*- coding: utf-8 -*-
"""Cell: windows-obs-qt-uia. OBS Studio (Qt Widgets) — READ-ONLY.

Tier F question: does Qt's Windows accessibility bridge (QAccessible->UIA)
expose an honest tree, and is the video-preview canvas declared or silent?
No clicks at all — the user's real OBS config is behind this UI.
"""
import ctypes, json, os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from uia_probe import (auto, distill, rect_of, screenshot, text_tokens,
                       image_tokens, save_artifact, probe_with_latch, walk)

out = {"cell": "windows-obs-qt-uia"}
OBS_DIR = r"C:\Program Files\obs-studio\bin\64bit"
proc = subprocess.Popen([os.path.join(OBS_DIR, "obs64.exe"), "--disable-updater"],
                        cwd=OBS_DIR)
time.sleep(10.0)

win = auto.WindowControl(searchDepth=1, RegexName="OBS .*")
if not win.Exists(15):
    print(json.dumps({"error": "obs window not found"})); sys.exit(1)
wrect = rect_of(win)
out["window_rect"] = wrect
out["window_title"] = win.Name

# stack signature: Qt DLLs in the process
try:
    import psutil  # optional
except ImportError:
    psutil = None
sig = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     f"(Get-Process obs64).Modules | Where-Object {{$_.ModuleName -match 'Qt'}} | Select-Object -First 4 -ExpandProperty ModuleName"],
    capture_output=True, text=True).stdout.strip().splitlines()
out["qt_modules"] = sig

view, stats, attempts = probe_with_latch(lambda: win, settle=1.0, retries=4)
out["latch_attempts"] = attempts
out["view_stats"] = {"nodes": stats["nodes"], "cap_hit": stats["cap_hit"]}
out["view_bytes"] = len(view.encode("utf-8"))
out["view_tokens"] = text_tokens(view)
out["screenshot_tokens_window"] = image_tokens(wrect[2], wrect[3])
save_artifact("obs-uia-view.txt", view)

t0 = time.perf_counter(); distill(win)
out["capture_latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)

# what does the tree say about the video preview area? look for big unnamed
# regions vs declared ones in the raw walk
big_nodes = []
for c, d in walk(win, max_depth=40, max_nodes=20000):
    if c is None: break
    try:
        r = c.BoundingRectangle
        w, h = r.right - r.left, r.bottom - r.top
        if w * h > 200000:  # big regions only
            big_nodes.append({"type": c.ControlTypeName, "name": (c.Name or "")[:60],
                              "class": (c.ClassName or "")[:40],
                              "rect": [r.left, r.top, w, h], "depth": d})
    except Exception:
        continue
out["big_regions"] = big_nodes[:15]

# key UI landmarks expected on screen: dock titles
landmarks = ["Scènes", "Scenes", "Sources", "Mélangeur", "Audio Mixer",
             "Commandes", "Controls", "Démarrer le streaming", "Start Streaming"]
out["landmarks_seen"] = [l for l in landmarks if l in view]

if ctypes.windll.user32.GetForegroundWindow() == win.NativeWindowHandle:
    screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                   "artifacts", "windows", "obs-uia-shot.png"))
else:
    screenshot(wrect, os.path.join(os.path.dirname(__file__), "..", "results",
                                   "artifacts", "windows", "obs-uia-shot.png"))

# idle cost
import difflib
v1, _ = distill(win); time.sleep(1.5); v2, _ = distill(win)
idiff = "\n".join(difflib.unified_diff(v1.splitlines(), v2.splitlines(), lineterm=""))
out["idle_diff_bytes"] = len(idiff.encode("utf-8"))

# close politely via window close (OBS asks nothing on plain close when not streaming)
win.GetPattern(auto.PatternId.WindowPattern).Close()
time.sleep(2.0)
# confirm exit dialog if OBS shows one — click "Oui/Yes" would be needed; check
conf = auto.WindowControl(searchDepth=1, RegexName=".*[Qq]uitter.*|.*[Ee]xit.*")
if conf.Exists(2):
    out["exit_dialog"] = conf.Name
print(json.dumps(out, ensure_ascii=False, indent=1))
